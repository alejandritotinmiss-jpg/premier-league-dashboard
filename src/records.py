"""Récords de las cinco temporadas: de una sola temporada, acumulados y de partidos."""

import pandas as pd

from src.curiosidades import describir_partidos, partido_maximo
from src.partidos import fecha_texto, marcador

# Nombre visible -> (columna, True si el récord es el valor más bajo).
METRICAS_RECORD = {
    "Más puntos": ("Puntos", False),
    "Más goles anotados": ("GolesFavor", False),
    "Menos goles recibidos": ("GolesContra", True),
    "Más victorias": ("V", False),
    "Más derrotas": ("D", False),
    "Más empates": ("E", False),
    "Más tiros": ("Tiros", False),
    "Más tiros al arco": ("TirosArco", False),
    "Más córners": ("Corners", False),
    "Más tarjetas amarillas": ("Amarillas", False),
    "Más tarjetas rojas": ("Rojas", False),
}


def poner_posiciones(tabla, columna, menor_es_mejor):
    """Ordena la tabla y agrega la posición; los empatados comparten posición."""
    tabla = tabla.sort_values(columna, ascending=menor_es_mejor, kind="stable").reset_index(drop=True)
    posiciones = tabla[columna].rank(method="min", ascending=menor_es_mejor).astype(int)
    tabla.insert(0, "Pos", posiciones)
    return tabla


def ranking_una_temporada(estadisticas, columna, menor_es_mejor, temporadas=None):
    """Récords de una sola temporada: compara los 100 equipo-temporada (o las temporadas elegidas)."""
    tabla = estadisticas[estadisticas["Condicion"] == "Total"]
    if temporadas is not None:
        tabla = tabla[tabla["Temporada"].isin(temporadas)]
    tabla = tabla[["Temporada", "Equipo", columna]].copy()
    tabla[columna] = tabla[columna].astype(int)
    return poner_posiciones(tabla, columna, menor_es_mejor)


def ranking_acumulado(estadisticas, columna, menor_es_mejor):
    """Suma de las cinco temporadas por equipo.

    Los equipos no jugaron el mismo número de temporadas. Para "menos goles recibidos"
    solo se comparan los que jugaron las cinco; si no, ganaría quien jugó menos.
    """
    tabla = estadisticas[estadisticas["Condicion"] == "Total"]
    resumen = tabla.groupby("Equipo").agg(Temporadas=("Temporada", "count"), Valor=(columna, "sum"))
    resumen = resumen.reset_index().rename(columns={"Valor": columna})
    resumen[columna] = resumen[columna].astype(int)
    if menor_es_mejor:
        resumen = resumen[resumen["Temporadas"] == 5]
    return poner_posiciones(resumen, columna, menor_es_mejor)


def lideres_por_temporada(estadisticas, columna, menor_es_mejor):
    """El mejor valor de cada temporada y quién lo consiguió (puede haber empates)."""
    tabla = estadisticas[estadisticas["Condicion"] == "Total"]
    filas = []
    for temporada, grupo in tabla.groupby("Temporada"):
        mejor = grupo[columna].min() if menor_es_mejor else grupo[columna].max()
        equipos = grupo.loc[grupo[columna] == mejor, "Equipo"].tolist()
        filas.append({"Temporada": temporada, "Valor": int(mejor), "Equipo": " y ".join(equipos)})
    return pd.DataFrame(filas)


def records_de_partidos(partidos):
    """Los cuatro récords de partidos de las cinco temporadas, cada uno con título y texto."""
    records = []

    tabla, goles = partido_maximo(partidos, "FTHG", "FTAG")
    records.append({"titulo": "Partido con más goles", "valor": f"{goles} goles",
                    "texto": describir_partidos(tabla), "partidos": tabla})

    diferencia = (partidos["FTHG"] - partidos["FTAG"]).abs()
    tabla = partidos[diferencia == diferencia.max()]
    records.append({"titulo": "Mayor diferencia de goles", "valor": f"{int(diferencia.max())} goles",
                    "texto": describir_partidos(tabla), "partidos": tabla})

    conteo = {}
    for local, visitante in zip(partidos["FTHG"], partidos["FTAG"]):
        resultado = f"{max(local, visitante)}-{min(local, visitante)}"
        conteo[resultado] = conteo.get(resultado, 0) + 1
    mas_repetido = max(conteo, key=conteo.get)
    total_partidos = f"{len(partidos):,}".replace(",", ".")   # 1900 -> "1.900"
    records.append({"titulo": "Resultado más repetido", "valor": mas_repetido,
                    "texto": f"Se dio en {conteo[mas_repetido]} de los {total_partidos} partidos "
                             "(sin importar quién ganó).", "partidos": None})

    goles_equipo = partidos[["FTHG", "FTAG"]].max(axis=1)
    tabla = partidos[goles_equipo == goles_equipo.max()]
    records.append({"titulo": "Más goles de un equipo en un partido", "valor": f"{int(goles_equipo.max())} goles",
                    "texto": describir_partidos(tabla), "partidos": tabla})
    return records


def resultados_mas_repetidos(partidos, cantidad=8):
    """Los resultados más frecuentes de las cinco temporadas (sin importar quién ganó)."""
    resultados = [f"{max(a, b)}-{min(a, b)}" for a, b in zip(partidos["FTHG"], partidos["FTAG"])]
    conteo = pd.Series(resultados).value_counts().head(cantidad)
    return pd.DataFrame({"Resultado": conteo.index, "Partidos": conteo.values})


def records_de_partidos_por_temporada(partidos):
    """Para cada temporada: el partido con más goles y la mayor diferencia de goles."""
    filas = []
    for temporada, grupo in partidos.groupby("Temporada"):
        tabla, goles = partido_maximo(grupo, "FTHG", "FTAG")
        diferencia = (grupo["FTHG"] - grupo["FTAG"]).abs()
        goleadas = grupo[diferencia == diferencia.max()]
        filas.append({
            "Temporada": temporada,
            "Más goles en un partido": goles,
            "Partido(s) con más goles": "; ".join(f"{marcador(f)} ({fecha_texto(f['Date'])})" for _, f in tabla.iterrows()),
            "Mayor diferencia": int(diferencia.max()),
            "Partido(s) con mayor diferencia": "; ".join(f"{marcador(f)} ({fecha_texto(f['Date'])})"
                                                        for _, f in goleadas.iterrows()),
        })
    return pd.DataFrame(filas)
