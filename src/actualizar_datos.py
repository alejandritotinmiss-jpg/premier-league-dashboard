"""Actualiza la temporada en curso con los resultados nuevos de Football-Data.co.uk.

Uso:
    python -m src.actualizar_datos                    descarga y actualiza
    python -m src.actualizar_datos --archivo E0.csv   usa un archivo ya descargado

Lo ejecuta GitHub Actions varias veces al día (.github/workflows/actualizar-datos.yml).
Pasos:
    1. Descarga el CSV de la temporada en curso (y el calendario).
    2. Lo convierte al formato del proyecto y lo valida.
    3. Lo compara con lo que ya había. Si no hay nada nuevo, termina sin tocar nada.
    4. Recalcula las tablas, la evaluación del modelo y las predicciones en una COPIA.
    5. Solo si todo salió bien, pasa los archivos nuevos a data/.
Si algo falla, data/ queda como estaba (se conserva la última versión válida).
"""

import argparse
import io
import json
import os
import shutil
import tempfile
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src import calendario as cal
from src import entrenar_modelo, preparar_datos
from src.limpieza import (COLUMNAS_ESPERADAS, COLUMNAS_NUMERICAS, PARTIDOS_TEMPORADA_COMPLETA,
                          descubrir_temporadas, temporada_es_valida, validar_temporada)

CARPETA_DATOS = preparar_datos.RAIZ_PROYECTO / "data"
URL_RESULTADOS = "https://www.football-data.co.uk/mmz4281/{codigo}/E0.csv"
URL_CALENDARIO = "https://fixturedownload.com/feed/json/epl-{anio}"


class DatosInvalidos(Exception):
    """El archivo descargado no pasa las comprobaciones: no se publica."""


def aviso(texto):
    print(f"[actualizar] {texto}", flush=True)


# ---------------------------------------------------------------------------
# Qué temporada toca actualizar
# ---------------------------------------------------------------------------
def codigo_de(temporada):
    """"2026/27" -> "2627"."""
    return temporada[2:4] + temporada[5:7]


def temporada_siguiente(temporada):
    """"2026/27" -> "2027/28"."""
    inicio = int(temporada[:4]) + 1
    return f"{inicio}/{str(inicio + 1)[2:]}"


def temporada_objetivo(carpeta_raw):
    """Devuelve (temporada a actualizar, True si es una temporada que todavía no está en data/raw/)."""
    temporadas = descubrir_temporadas(carpeta_raw)
    ultima = list(temporadas)[-1]
    filas = len(pd.read_csv(Path(carpeta_raw) / temporadas[ultima]))
    if filas >= PARTIDOS_TEMPORADA_COMPLETA:
        return temporada_siguiente(ultima), True      # la última ya terminó: se busca la siguiente
    return ultima, False


# ---------------------------------------------------------------------------
# Descarga y conversión
# ---------------------------------------------------------------------------
def descargar(url, tiempo_maximo=60):
    """Descarga una URL y devuelve su contenido en bytes (None si la fuente no está disponible)."""
    peticion = urllib.request.Request(url, headers={"User-Agent": "premier-league-dashboard (proyecto academico)"})
    try:
        with urllib.request.urlopen(peticion, timeout=tiempo_maximo) as respuesta:
            return respuesta.read()
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        aviso(f"No se pudo descargar {url}: {error}")
        return None


def convertir_resultados(contenido):
    """Convierte el CSV de Football-Data.co.uk al formato del proyecto.

    Devuelve (tabla, partidos aplazados por falta de estadísticas). El archivo original trae
    más de cien columnas (muchas son cuotas de apuestas): solo se conservan las 22 del proyecto.
    """
    try:
        tabla = pd.read_csv(io.BytesIO(contenido), encoding="latin-1")
    except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError) as error:
        raise DatosInvalidos(f"El archivo no se puede leer como CSV: {error}")
    # La primera columna puede traer caracteres invisibles al inicio (marca BOM).
    tabla.columns = [str(columna).strip().lstrip("ï»¿﻿") for columna in tabla.columns]
    faltan = [columna for columna in COLUMNAS_ESPERADAS if columna not in tabla.columns]
    if faltan:
        raise DatosInvalidos(f"Al archivo le faltan columnas: {faltan}")

    tabla = tabla[COLUMNAS_ESPERADAS].dropna(how="all")
    tabla = tabla.dropna(subset=["HomeTeam", "AwayTeam"])
    # Sin goles todavía = partido pendiente: no es un resultado.
    tabla = tabla.dropna(subset=["FTHG", "FTAG", "FTR"])
    # Con goles pero sin estadísticas: la fuente aún no las cargó. Se espera a la próxima actualización.
    incompletas = tabla[COLUMNAS_NUMERICAS + ["HTR"]].isna().any(axis=1)
    aplazados = int(incompletas.sum())
    tabla = tabla[~incompletas].copy()

    fechas = pd.to_datetime(tabla["Date"], format="%d/%m/%Y", errors="coerce")
    fechas = fechas.fillna(pd.to_datetime(tabla["Date"], format="%d/%m/%y", errors="coerce"))
    if fechas.isna().any():
        raise DatosInvalidos("Hay fechas que no se pueden leer (se esperaba día/mes/año).")
    tabla["Date"] = fechas.dt.strftime("%Y-%m-%d")
    for columna in ["HomeTeam", "AwayTeam", "Referee"]:
        tabla[columna] = tabla[columna].fillna("").astype(str).str.strip()
    try:
        tabla[COLUMNAS_NUMERICAS] = tabla[COLUMNAS_NUMERICAS].astype(float).astype(int)
    except (ValueError, TypeError) as error:
        raise DatosInvalidos(f"Hay estadísticas que no son números: {error}")
    tabla = tabla.sort_values("Date", kind="stable").reset_index(drop=True)
    return tabla, aplazados


def validar_resultados(tabla, temporada):
    """Aplica las mismas comprobaciones que la limpieza del proyecto."""
    revisada = tabla.copy()
    revisada["Date"] = pd.to_datetime(revisada["Date"], format="%Y-%m-%d")
    revisada.insert(0, "Temporada", temporada)
    validacion = validar_temporada(revisada, temporada)
    if (tabla[COLUMNAS_NUMERICAS] < 0).any().any():
        raise DatosInvalidos("Hay estadísticas negativas.")
    if not temporada_es_valida(validacion, puede_estar_en_curso=True):
        raise DatosInvalidos(f"La temporada {temporada} no pasa la validación: {validacion}")


def comparar(anterior, nueva):
    """Compara la versión guardada con la descargada. Devuelve un resumen de los cambios."""
    clave = ["HomeTeam", "AwayTeam"]
    unidas = anterior.merge(nueva, on=clave, how="left", suffixes=("_antes", "_ahora"), indicator=True)
    desaparecidos = unidas[unidas["_merge"] == "left_only"]
    if not desaparecidos.empty:
        partido = desaparecidos.iloc[0]
        raise DatosInvalidos(f"{len(desaparecidos)} partido(s) ya guardados no están en la descarga "
                             f"(por ejemplo {partido['HomeTeam']} - {partido['AwayTeam']}).")
    marcador_cambiado = (unidas["FTHG_antes"] != unidas["FTHG_ahora"]) | (unidas["FTAG_antes"] != unidas["FTAG_ahora"])
    if marcador_cambiado.any():
        partido = unidas[marcador_cambiado].iloc[0]
        raise DatosInvalidos(f"Cambió el marcador de un partido ya guardado ({partido['HomeTeam']} - "
                             f"{partido['AwayTeam']}): hay que revisarlo a mano.")
    otras = [columna for columna in COLUMNAS_ESPERADAS if columna not in clave + ["FTHG", "FTAG"]]
    corregidos = 0
    for columna in otras:
        corregidos += int((unidas[f"{columna}_antes"].astype(str) != unidas[f"{columna}_ahora"].astype(str)).sum())
    return {"partidos_nuevos": len(nueva) - len(anterior), "celdas_corregidas": corregidos}


def convertir_calendario(contenido):
    """Convierte el calendario (JSON de fixturedownload.com) a la tabla del proyecto."""
    try:
        partidos = json.loads(contenido.decode("utf-8-sig"))
        tabla = pd.DataFrame({
            "Jornada": [int(partido["RoundNumber"]) for partido in partidos],
            "FechaUTC": [str(partido["DateUtc"]) for partido in partidos],
            "HomeTeam": [cal.NOMBRES_CALENDARIO.get(partido["HomeTeam"], partido["HomeTeam"]) for partido in partidos],
            "AwayTeam": [cal.NOMBRES_CALENDARIO.get(partido["AwayTeam"], partido["AwayTeam"]) for partido in partidos],
            "Numero": [int(partido["MatchNumber"]) for partido in partidos],
        })
    except (ValueError, KeyError, TypeError) as error:
        raise DatosInvalidos(f"El calendario no tiene el formato esperado: {error}")
    tabla = tabla.sort_values(["FechaUTC", "Numero"], kind="stable").drop(columns="Numero")
    return tabla.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Actualización completa
# ---------------------------------------------------------------------------
def actualizar_calendario(carpeta_datos, temporada, equipos, contenido):
    """Guarda el calendario descargado si es válido y distinto. Devuelve True si cambió."""
    if contenido is None:
        return False
    try:
        nuevo = convertir_calendario(contenido)
    except DatosInvalidos as error:
        aviso(f"Calendario descartado (se conserva el anterior): {error}")
        return False
    revisado = nuevo.assign(FechaUTC=pd.to_datetime(nuevo["FechaUTC"], utc=True, errors="coerce"))
    if not cal.calendario_es_valido(revisado, equipos):
        aviso("Calendario descartado (se conserva el anterior): no tiene 380 partidos válidos de los 20 equipos.")
        return False
    ruta = cal.ruta_calendario(temporada, Path(carpeta_datos) / "calendario")
    texto = nuevo.to_csv(index=False, lineterminator="\n")
    if ruta.exists() and ruta.read_text(encoding="utf-8").replace("\r\n", "\n") == texto:
        return False
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(texto, encoding="utf-8", newline="\n")
    aviso(f"Calendario de {temporada} actualizado.")
    return True


def actualizar(carpeta_datos=None, contenido_resultados=None, contenido_calendario=None,
               descargar_archivos=True):
    """Hace toda la actualización. Devuelve un diccionario con lo que pasó.

    contenido_resultados y contenido_calendario permiten pasar los archivos ya descargados
    (así se prueba sin internet).
    """
    carpeta_datos = Path(carpeta_datos or CARPETA_DATOS)
    temporada, es_nueva = temporada_objetivo(carpeta_datos / "raw")
    codigo = codigo_de(temporada)
    url = URL_RESULTADOS.format(codigo=codigo)
    aviso(f"Temporada a revisar: {temporada} ({'todavía no está en el proyecto' if es_nueva else 'en curso'})")

    if contenido_resultados is None and descargar_archivos:
        contenido_resultados = descargar(url)
    if contenido_resultados is None:
        aviso("Sin datos nuevos: la fuente no respondió. Se conserva la versión actual.")
        return {"cambios": False, "motivo": "fuente no disponible"}

    try:
        nueva, aplazados = convertir_resultados(contenido_resultados)
        validar_resultados(nueva, temporada)
    except DatosInvalidos as error:
        if es_nueva:
            # Al empezar una temporada el archivo puede no existir o tener muy pocos partidos: es normal.
            aviso(f"La temporada {temporada} todavía no se puede incorporar: {error}")
            return {"cambios": False, "motivo": "temporada nueva sin datos suficientes"}
        raise
    if aplazados:
        aviso(f"{aplazados} partido(s) con resultado pero sin estadísticas: se incorporan cuando la fuente las publique.")

    ruta_raw = carpeta_datos / "raw" / f"season-{codigo}.csv"
    resumen = {"partidos_nuevos": len(nueva), "celdas_corregidas": 0}
    if not es_nueva:
        anterior = pd.read_csv(ruta_raw)
        resumen = comparar(anterior, nueva)

    if contenido_calendario is None and descargar_archivos:
        contenido_calendario = descargar(URL_CALENDARIO.format(anio=temporada[:4]))

    hay_resultados = resumen["partidos_nuevos"] > 0 or resumen["celdas_corregidas"] > 0
    # Todo se prepara en una copia: si algo falla, data/ no se toca.
    with tempfile.TemporaryDirectory() as temporal:
        copia = Path(temporal) / "data"
        shutil.copytree(carpeta_datos, copia)
        equipos = sorted(set(nueva["HomeTeam"]))
        cambio_calendario = actualizar_calendario(copia, temporada, equipos, contenido_calendario)
        if not hay_resultados and not cambio_calendario:
            aviso("Sin cambios: no hay resultados nuevos ni cambios en el calendario.")
            return {"cambios": False, "motivo": "sin novedades"}

        if hay_resultados:
            nueva.to_csv(copia / "raw" / f"season-{codigo}.csv", index=False, lineterminator="\n")
            preparar_datos.guardar_tablas(copia / "raw", copia / "processed")
            aviso(f"Tablas recalculadas: {resumen['partidos_nuevos']} partido(s) nuevo(s), "
                  f"{resumen['celdas_corregidas']} celda(s) corregida(s) por la fuente.")
        evaluacion, _ = entrenar_modelo.guardar(copia / "processed", copia / "modelo", copia / "calendario")
        aviso(f"Modelo regenerado: {evaluacion['version']}")

        ahora = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        partidos = pd.read_csv(copia / "processed" / "partidos_limpios.csv")
        registro = {
            "ultima_actualizacion": ahora, "temporada": temporada, "partidos_de_la_temporada": int(len(nueva)),
            "partidos_nuevos": int(resumen["partidos_nuevos"]), "celdas_corregidas": int(resumen["celdas_corregidas"]),
            "fecha_ultimo_partido": str(partidos["Date"].max()), "partidos_totales": int(len(partidos)),
            "fuente_resultados": url, "fuente_calendario": URL_CALENDARIO.format(anio=temporada[:4]),
            "metodo": "automático (GitHub Actions)" if os.environ.get("GITHUB_ACTIONS") else "manual",
        }
        with open(copia / "actualizacion.json", "w", encoding="utf-8", newline="\n") as archivo:
            json.dump(registro, archivo, ensure_ascii=False, indent=2)
        with open(copia / "registro_actualizaciones.csv", "a", encoding="utf-8", newline="\n") as archivo:
            if archivo.tell() == 0:
                archivo.write("fecha_utc,temporada,partidos_nuevos,celdas_corregidas,partidos_de_la_temporada\n")
            archivo.write(f"{ahora},{temporada},{registro['partidos_nuevos']},{registro['celdas_corregidas']},"
                          f"{len(nueva)}\n")

        # Todo salió bien: ahora sí se pasan los archivos a data/.
        shutil.copytree(copia, carpeta_datos, dirs_exist_ok=True)
    aviso("Actualización terminada.")
    return dict(registro, cambios=True)


def main():
    opciones = argparse.ArgumentParser(description="Actualiza los datos de la temporada en curso.")
    opciones.add_argument("--archivo", help="CSV de Football-Data.co.uk ya descargado (no usa internet)")
    argumentos = opciones.parse_args()
    contenido = Path(argumentos.archivo).read_bytes() if argumentos.archivo else None
    try:
        resultado = actualizar(contenido_resultados=contenido, descargar_archivos=argumentos.archivo is None)
    except DatosInvalidos as error:
        aviso(f"ERROR: datos rechazados, no se publica nada. {error}")
        raise SystemExit(1)
    # GitHub Actions lee este archivo para saber si hay algo que publicar.
    salida = os.environ.get("GITHUB_OUTPUT")
    if salida:
        with open(salida, "a", encoding="utf-8") as archivo:
            archivo.write(f"cambios={'true' if resultado['cambios'] else 'false'}\n")


if __name__ == "__main__":
    main()
