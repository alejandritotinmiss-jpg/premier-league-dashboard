"""Genera las tablas de data/processed/ a partir de los CSV de data/raw/.

Uso: python -m src.preparar_datos
"""

import json
from pathlib import Path

import pandas as pd

from src.estadisticas import (
    agregar_numero_partido,
    calcular_clasificacion,
    estadisticas_por_condicion,
    partidos_a_equipo_partido,
)
from src.limpieza import (
    TEMPORADAS,
    cargar_temporada,
    limpiar_temporada,
    temporada_es_valida,
    validar_temporada,
)

# Rutas relativas al proyecto, para que funcionen en cualquier computador y en la nube.
RAIZ_PROYECTO = Path(__file__).resolve().parent.parent
CARPETA_RAW = RAIZ_PROYECTO / "data" / "raw"
CARPETA_PROCESADOS = RAIZ_PROYECTO / "data" / "processed"


def limpiar_todas(carpeta_raw=CARPETA_RAW):
    """Carga, valida y limpia las cinco temporadas y las une en una sola tabla."""
    limpias = []
    reporte = {"validacion_por_temporada": {}, "cambios": []}
    for temporada, archivo in TEMPORADAS.items():
        ruta = Path(carpeta_raw) / archivo
        if not ruta.exists():
            raise FileNotFoundError(f"Falta el archivo {archivo} de la temporada {temporada}.")

        df = cargar_temporada(ruta, temporada)
        validacion = validar_temporada(df, temporada)
        reporte["validacion_por_temporada"][temporada] = validacion
        if not temporada_es_valida(validacion):
            raise ValueError(f"La temporada {temporada} no pasa la validación: {validacion}")

        limpio, cambios = limpiar_temporada(df)
        for cambio in cambios:
            cambio["temporada"] = temporada
            reporte["cambios"].append(cambio)
        limpias.append(limpio)

    partidos = pd.concat(limpias, ignore_index=True)
    partidos = partidos.sort_values(["Temporada", "Date"], kind="stable").reset_index(drop=True)
    return partidos, reporte


def generar_tablas(carpeta_raw=CARPETA_RAW):
    """Genera las cuatro tablas del proyecto y el reporte de limpieza."""
    partidos, reporte = limpiar_todas(carpeta_raw)

    con_id = partidos.copy()
    con_id.insert(0, "PartidoID", range(len(con_id)))
    equipo_partido = agregar_numero_partido(partidos_a_equipo_partido(con_id))
    estadisticas = estadisticas_por_condicion(equipo_partido)
    clasificacion = calcular_clasificacion(estadisticas[estadisticas["Condicion"] == "Total"])

    tablas = {
        "partidos_limpios": partidos,
        "equipo_partido": equipo_partido,
        "estadisticas_equipo_temporada": estadisticas,
        "clasificacion": clasificacion,
    }
    return tablas, reporte


def guardar_tablas(carpeta_raw=CARPETA_RAW, carpeta_salida=CARPETA_PROCESADOS):
    """Guarda las tablas en CSV y el reporte en JSON."""
    tablas, reporte = generar_tablas(carpeta_raw)
    carpeta_salida = Path(carpeta_salida)
    carpeta_salida.mkdir(parents=True, exist_ok=True)

    for nombre, tabla in tablas.items():
        tabla.to_csv(carpeta_salida / f"{nombre}.csv", index=False)

    reporte["filas_finales"] = int(len(tablas["partidos_limpios"]))
    with open(carpeta_salida / "reporte_limpieza.json", "w", encoding="utf-8") as archivo:
        json.dump(reporte, archivo, ensure_ascii=False, indent=2)
    return tablas


def main():
    tablas = guardar_tablas()
    for nombre, tabla in tablas.items():
        print(f"{nombre}.csv: {tabla.shape[0]} filas y {tabla.shape[1]} columnas")
    print(f"Archivos guardados en {CARPETA_PROCESADOS}")


if __name__ == "__main__":
    main()
