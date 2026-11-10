"""Estimación sencilla: qué jugadores tienen más opciones de marcar en un partido.

Datos que usa (todos reales, nada inventado):
    - data/jugadores/goleadores.csv: goles y partidos jugados de los máximos goleadores
      de cada temporada (solo aparecen los primeros 10 a 16 de cada temporada).
    - estadisticas_equipo_temporada.csv: goles que recibe cada equipo por partido.

Cálculo, paso a paso:
    1. Goles por partido del jugador: sus goles divididos entre sus partidos jugados,
       sumando la temporada actual y la anterior (así no depende de pocos partidos).
    2. Ajuste por rival: goles que recibe el rival por partido dividido entre el promedio
       de la liga. Un rival que recibe muchos goles sube la cifra; uno que recibe pocos,
       la baja. Para no exagerar con pocos partidos, se mezcla con 10 partidos "promedio".
    3. Goles esperados del jugador = (1) x (2).
    4. Probabilidad de marcar al menos un gol (modelo de Poisson):
           P = 1 - e^(-goles esperados)

Limitaciones: supone que el jugador juega como en sus partidos anteriores; no conoce
alineaciones, lesiones, sanciones ni quién tira los penales; y solo puede nombrar a
jugadores que están en las tablas de goleadores. No se puede validar con partidos pasados
porque no hay datos de goles de cada jugador partido a partido.
"""

import math

import pandas as pd

PARTIDOS_PROMEDIO_RIVAL = 10      # partidos "promedio" que se mezclan con los del rival
NOMBRE_METODO = "Estimación de Poisson con goles por partido y ajuste por rival"


def temporada_anterior(temporada, temporadas):
    """La temporada anterior que existe en los datos (o None)."""
    anteriores = [t for t in sorted(temporadas) if t < temporada]
    return anteriores[-1] if anteriores else None


def goles_por_partido(goleadores, jugador, temporadas_usadas):
    """(goles, partidos) del jugador en las temporadas indicadas, solo las que tienen partidos."""
    filas = goleadores[(goleadores["Jugador"] == jugador) & goleadores["Temporada"].isin(temporadas_usadas)]
    filas = filas.dropna(subset=["Partidos"])
    return int(filas["Goles"].sum()), int(filas["Partidos"].sum())


def factor_rival(estadisticas, temporada, rival):
    """Cuánto más (o menos) goles recibe el rival que un equipo promedio de la liga."""
    total = estadisticas[(estadisticas["Temporada"] == temporada) & (estadisticas["Condicion"] == "Total")]
    media_liga = total["GolesContra"].sum() / total["PJ"].sum()
    fila = total[total["Equipo"] == rival]
    if fila.empty or media_liga == 0:
        return 1.0
    fila = fila.iloc[0]
    # Se suman 10 partidos con la media de la liga: con pocos partidos el factor queda cerca de 1.
    recibe = (fila["GolesContra"] + PARTIDOS_PROMEDIO_RIVAL * media_liga) / (fila["PJ"] + PARTIDOS_PROMEDIO_RIVAL)
    return recibe / media_liga


def probabilidad_de_marcar(goles_esperados):
    """Probabilidad de marcar al menos un gol si los goles siguen una distribución de Poisson."""
    return 1 - math.exp(-goles_esperados)


def candidatos_del_equipo(goleadores, temporada, equipo, temporadas):
    """Jugadores del equipo en la tabla de goleadores de la temporada (o de la anterior si no hay).

    Devuelve (lista de jugadores, temporada de la que salen).
    """
    for opcion in [temporada, temporada_anterior(temporada, temporadas)]:
        if opcion is None:
            continue
        filas = goleadores[(goleadores["Temporada"] == opcion) & (goleadores["EquipoCorto"] == equipo)]
        if not filas.empty:
            return list(filas["Jugador"]), opcion
    return [], None


def estimar(goleadores, estadisticas, temporada, equipo, rival):
    """Tabla con la probabilidad estimada de que marque cada jugador del equipo contra el rival.

    Devuelve (tabla ordenada de mayor a menor, temporada de la que salen los jugadores).
    """
    temporadas = sorted(estadisticas["Temporada"].unique())
    jugadores, origen = candidatos_del_equipo(goleadores, temporada, equipo, temporadas)
    usadas = [t for t in [temporada, temporada_anterior(temporada, temporadas)] if t]
    ajuste = factor_rival(estadisticas, temporada, rival)
    filas = []
    for jugador in jugadores:
        goles, partidos = goles_por_partido(goleadores, jugador, usadas)
        if partidos == 0:
            continue
        tasa = goles / partidos
        esperados = tasa * ajuste
        filas.append({"Jugador": jugador, "Equipo": equipo, "Rival": rival, "Goles": goles, "Partidos": partidos,
                      "Goles por partido": round(tasa, 2), "Ajuste por rival": round(ajuste, 2),
                      "Probabilidad de marcar": probabilidad_de_marcar(esperados)})
    tabla = pd.DataFrame(filas, columns=["Jugador", "Equipo", "Rival", "Goles", "Partidos", "Goles por partido",
                                         "Ajuste por rival", "Probabilidad de marcar"])
    tabla = tabla.sort_values("Probabilidad de marcar", ascending=False, kind="stable").reset_index(drop=True)
    return tabla, origen
