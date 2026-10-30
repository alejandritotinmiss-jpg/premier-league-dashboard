"""Goleadores y asistentes de cada temporada (datos de ESPN, Wikipedia y la Premier League)."""

import json

import pandas as pd

from src.equipos import equipo_desde_nombre_completo
from src.preparar_datos import RAIZ_PROYECTO

CARPETA_JUGADORES = RAIZ_PROYECTO / "data" / "jugadores"


def cargar_jugadores():
    """Lee goleadores.csv, asistencias.csv y fuentes.json."""
    goleadores = pd.read_csv(CARPETA_JUGADORES / "goleadores.csv")
    asistencias = pd.read_csv(CARPETA_JUGADORES / "asistencias.csv")
    for tabla in [goleadores, asistencias]:
        # Nombre corto del equipo, el mismo que usan los CSV de partidos.
        tabla["EquipoCorto"] = [equipo_desde_nombre_completo(nombre) for nombre in tabla["Equipo"]]
    with open(CARPETA_JUGADORES / "fuentes.json", encoding="utf-8") as archivo:
        fuentes = json.load(archivo)
    return goleadores, asistencias, fuentes


def ranking(tabla, temporada, columna):
    """Tabla de una temporada ordenada, con posición compartida para los empatados."""
    datos = tabla[tabla["Temporada"] == temporada].copy()
    datos = datos.sort_values(columna, ascending=False, kind="stable")
    posiciones = datos[columna].rank(method="min", ascending=False).astype(int)
    datos.insert(0, "Posicion", posiciones)
    return datos.reset_index(drop=True)


def lideres(tabla_ranking):
    """Jugadores en el primer puesto (puede haber más de uno si empatan)."""
    return tabla_ranking[tabla_ranking["Posicion"] == 1]
