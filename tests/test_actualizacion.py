"""Pruebas de la actualización automática (src/actualizar_datos.py).

Todas trabajan sobre una COPIA de data/ en una carpeta temporal y sin internet:
el archivo "descargado" se fabrica con los mismos partidos del proyecto, en el
formato de Football-Data.co.uk (fecha día/mes/año y columnas extra de cuotas).
"""

import json
import math
import shutil
import sys

import pandas as pd
import pytest

from src import actualizar_datos as act
from src import entrenar_modelo
from src.preparar_datos import RAIZ_PROYECTO

CARPETA_DATOS = RAIZ_PROYECTO / "data"


def copia_de_datos(tmp_path):
    """Copia data/ a una carpeta temporal y devuelve (carpeta, código y ruta del CSV en curso)."""
    destino = tmp_path / "data"
    shutil.copytree(CARPETA_DATOS, destino)
    temporada, _ = act.temporada_objetivo(destino / "raw")
    codigo = act.codigo_de(temporada)
    return destino, destino / "raw" / f"season-{codigo}.csv"


def como_football_data(tabla):
    """Convierte una tabla del proyecto al formato del CSV original de Football-Data.co.uk."""
    original = tabla.copy()
    original["Date"] = pd.to_datetime(original["Date"]).dt.strftime("%d/%m/%Y")
    original.insert(0, "Div", "E0")
    original.insert(2, "Time", "15:00")
    original["B365H"] = 2.1                       # columna de cuotas: el proyecto la descarta
    return original.to_csv(index=False).encode("latin-1")


def valores_iguales(a, b, tolerancia=1e-6):
    """Compara dos resultados (diccionarios, listas, textos y números) con tolerancia en los números."""
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(valores_iguales(a[k], b[k], tolerancia) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(valores_iguales(x, y, tolerancia) for x, y in zip(a, b))
    if isinstance(a, float) or isinstance(b, float):
        return math.isclose(a, b, rel_tol=tolerancia, abs_tol=tolerancia)
    return a == b


def contenido_de_carpeta(carpeta):
    """Diccionario ruta relativa -> bytes, para comprobar que nada cambió."""
    return {ruta.relative_to(carpeta).as_posix(): ruta.read_bytes()
            for ruta in sorted(carpeta.rglob("*")) if ruta.is_file()}


def test_sin_resultados_nuevos_no_modifica_nada(tmp_path):
    datos, ruta = copia_de_datos(tmp_path)
    antes = contenido_de_carpeta(datos)
    resultado = act.actualizar(datos, como_football_data(pd.read_csv(ruta)), descargar_archivos=False)
    assert resultado == {"cambios": False, "motivo": "sin novedades"}
    assert contenido_de_carpeta(datos) == antes


def test_fuente_no_disponible_conserva_la_version_actual(tmp_path):
    datos, _ = copia_de_datos(tmp_path)
    antes = contenido_de_carpeta(datos)
    resultado = act.actualizar(datos, None, descargar_archivos=False)
    assert resultado["cambios"] is False and resultado["motivo"] == "fuente no disponible"
    assert contenido_de_carpeta(datos) == antes


def test_partidos_nuevos_actualizan_tablas_modelo_y_registro(tmp_path):
    datos, ruta = copia_de_datos(tmp_path)
    completa = pd.read_csv(ruta)
    completa.iloc[:-5].to_csv(ruta, index=False, lineterminator="\n")       # faltan los 5 últimos
    registro_antes = (datos / "registro_actualizaciones.csv").read_text(encoding="utf-8")

    resultado = act.actualizar(datos, como_football_data(completa), descargar_archivos=False)

    assert resultado["cambios"] is True and resultado["partidos_nuevos"] == 5
    assert len(pd.read_csv(ruta)) == len(completa)
    # Las tablas quedan exactamente igual que las del proyecto (que ya tiene esos 5 partidos).
    # Se ignora la diferencia de saltos de línea (\r\n en Windows, \n en Linux).
    for archivo in ["processed/partidos_limpios.csv", "processed/estadisticas_equipo_temporada.csv"]:
        nuevo = (datos / archivo).read_bytes().replace(b"\r\n", b"\n")
        assert nuevo == (CARPETA_DATOS / archivo).read_bytes().replace(b"\r\n", b"\n"), archivo
    # El modelo, con una tolerancia mínima: otra versión de scikit-learn u otro computador
    # pueden cambiar los últimos decimales (por ejemplo, el decimal 16 del log loss).
    assert valores_iguales(json.loads((datos / "modelo" / "evaluacion.json").read_text(encoding="utf-8")),
                           json.loads((CARPETA_DATOS / "modelo" / "evaluacion.json").read_text(encoding="utf-8")))
    nuevas = pd.read_csv(datos / "modelo" / "predicciones.csv")
    guardadas = pd.read_csv(CARPETA_DATOS / "modelo" / "predicciones.csv")
    columnas = ["P_local", "P_empate", "P_visitante"]
    assert nuevas.drop(columns=columnas).equals(guardadas.drop(columns=columnas))
    assert ((nuevas[columnas] - guardadas[columnas]).abs() <= 0.0002).all().all()
    registro = (datos / "registro_actualizaciones.csv").read_text(encoding="utf-8")
    assert registro.startswith(registro_antes) and registro.count("\n") == registro_antes.count("\n") + 1


@pytest.mark.parametrize("problema", ["faltan_columnas", "no_es_numero", "fecha_mala", "no_es_csv", "goles_negativos"])
def test_rechaza_archivos_invalidos_sin_tocar_los_datos(tmp_path, problema):
    datos, ruta = copia_de_datos(tmp_path)
    tabla = pd.read_csv(ruta)
    tabla = pd.concat([tabla, tabla.iloc[[0]].assign(HomeTeam="Equipo X")])     # habría "un partido nuevo"
    if problema == "faltan_columnas":
        contenido = como_football_data(tabla.drop(columns=["HST"]))
    elif problema == "no_es_numero":
        contenido = como_football_data(tabla.astype({"HS": object}).assign(HS="muchos"))
    elif problema == "fecha_mala":
        contenido = como_football_data(tabla).replace(b"21/08/2026", b"2026-21-08", 1)
    elif problema == "goles_negativos":
        contenido = como_football_data(tabla.assign(HC=-1))
    else:
        contenido = b"<html>Pagina no encontrada</html>\x00\x01"
    antes = contenido_de_carpeta(datos)
    with pytest.raises(act.DatosInvalidos):
        act.actualizar(datos, contenido, descargar_archivos=False)
    assert contenido_de_carpeta(datos) == antes


def test_rechaza_cambios_de_marcador_y_partidos_desaparecidos(tmp_path):
    datos, ruta = copia_de_datos(tmp_path)
    tabla = pd.read_csv(ruta)
    antes = contenido_de_carpeta(datos)
    cambiado = tabla.copy()
    cambiado.loc[0, "FTHG"] = cambiado.loc[0, "FTHG"] + 1
    with pytest.raises(act.DatosInvalidos):
        act.actualizar(datos, como_football_data(cambiado), descargar_archivos=False)
    with pytest.raises(act.DatosInvalidos):
        act.actualizar(datos, como_football_data(tabla.iloc[1:]), descargar_archivos=False)
    assert contenido_de_carpeta(datos) == antes


def test_si_falla_el_modelo_se_conserva_la_ultima_version_valida(tmp_path):
    datos, ruta = copia_de_datos(tmp_path)
    completa = pd.read_csv(ruta)
    completa.iloc[:-3].to_csv(ruta, index=False, lineterminator="\n")
    antes = contenido_de_carpeta(datos)

    guardar_original = entrenar_modelo.guardar

    def guardar_que_falla(*argumentos, **opciones):
        raise RuntimeError("fallo simulado al entrenar")

    entrenar_modelo.guardar = guardar_que_falla
    try:
        with pytest.raises(RuntimeError):
            act.actualizar(datos, como_football_data(completa), descargar_archivos=False)
    finally:
        entrenar_modelo.guardar = guardar_original
    assert contenido_de_carpeta(datos) == antes


def test_partidos_sin_estadisticas_esperan_a_la_proxima_actualizacion(tmp_path):
    datos, ruta = copia_de_datos(tmp_path)
    completa = pd.read_csv(ruta)
    completa.iloc[:-2].to_csv(ruta, index=False, lineterminator="\n")
    descarga = completa.astype({"HS": object})
    descarga.loc[descarga.index[-1], "HS"] = None          # el último aún sin estadísticas
    resultado = act.actualizar(datos, como_football_data(descarga), descargar_archivos=False)
    assert resultado["partidos_nuevos"] == 1
    assert len(pd.read_csv(ruta)) == len(completa) - 1


def test_partidos_pendientes_no_son_resultados():
    tabla = pd.read_csv(CARPETA_DATOS / "raw" / "season-2627.csv")
    pendiente = tabla.iloc[[0]].assign(HomeTeam="Arsenal", AwayTeam="Hull")
    pendiente[["FTHG", "FTAG", "FTR", "HS", "AS"]] = None
    convertida, aplazados = act.convertir_resultados(como_football_data(pd.concat([tabla, pendiente])))
    assert len(convertida) == len(tabla) and aplazados == 0


def test_se_puede_ejecutar_a_mano_con_un_archivo(tmp_path, monkeypatch):
    # main() es lo que corre GitHub Actions (y una persona con: python -m src.actualizar_datos --archivo E0.csv).
    datos, ruta = copia_de_datos(tmp_path)
    archivo = tmp_path / "E0.csv"
    archivo.write_bytes(como_football_data(pd.read_csv(ruta)))
    salida = tmp_path / "salida_github.txt"
    monkeypatch.setenv("GITHUB_OUTPUT", str(salida))
    carpeta_original, argumentos_originales = act.CARPETA_DATOS, sys.argv
    act.CARPETA_DATOS = datos
    sys.argv = ["actualizar_datos", "--archivo", str(archivo)]
    try:
        act.main()
    finally:
        act.CARPETA_DATOS, sys.argv = carpeta_original, argumentos_originales
    assert salida.read_text(encoding="utf-8") == "cambios=false\n"


def test_temporada_objetivo_pasa_a_la_siguiente_cuando_termina(tmp_path):
    carpeta = tmp_path / "raw"
    carpeta.mkdir()
    completa = pd.read_csv(CARPETA_DATOS / "raw" / "season-2526.csv")
    completa.to_csv(carpeta / "season-2526.csv", index=False)
    assert act.temporada_objetivo(carpeta) == ("2026/27", True)
    completa.iloc[:100].to_csv(carpeta / "season-2627.csv", index=False)
    assert act.temporada_objetivo(carpeta) == ("2026/27", False)
    assert act.temporada_siguiente("2026/27") == "2027/28" and act.codigo_de("2027/28") == "2728"
