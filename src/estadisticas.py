"""Estadísticas por equipo y temporada, y clasificación calculada."""

import pandas as pd

COLUMNAS_LOCAL = {
    "Equipo": "HomeTeam", "Rival": "AwayTeam",
    "GolesFavor": "FTHG", "GolesContra": "FTAG",
    "Tiros": "HS", "TirosArco": "HST", "Corners": "HC",
    "Faltas": "HF", "Amarillas": "HY", "Rojas": "HR",
}

COLUMNAS_VISITANTE = {
    "Equipo": "AwayTeam", "Rival": "HomeTeam",
    "GolesFavor": "FTAG", "GolesContra": "FTHG",
    "Tiros": "AS", "TirosArco": "AST", "Corners": "AC",
    "Faltas": "AF", "Amarillas": "AY", "Rojas": "AR",
}

COLUMNAS_A_SUMAR = [
    "Victoria", "Empate", "Derrota", "GolesFavor", "GolesContra", "Puntos",
    "Tiros", "TirosArco", "Corners", "Faltas", "Amarillas", "Rojas",
]

CRITERIOS_CLASIFICACION = ["Puntos", "DG", "GolesFavor"]


def puntos_y_resultado(goles_favor, goles_contra):
    """Devuelve (3, "V") si ganó, (1, "E") si empató y (0, "D") si perdió."""
    if goles_favor > goles_contra:
        return 3, "V"
    elif goles_favor == goles_contra:
        return 1, "E"
    else:
        return 0, "D"


def filas_de_un_partido(fila):
    """Convierte un partido en dos registros: uno del local y otro del visitante."""
    registros = []
    for condicion, columnas in [("Local", COLUMNAS_LOCAL), ("Visitante", COLUMNAS_VISITANTE)]:
        registro = {
            "PartidoID": fila["PartidoID"],
            "Temporada": fila["Temporada"],
            "Fecha": fila["Date"],
            "Condicion": condicion,
        }
        for nombre_nuevo, columna_original in columnas.items():
            registro[nombre_nuevo] = fila[columna_original]

        puntos, resultado = puntos_y_resultado(registro["GolesFavor"], registro["GolesContra"])
        registro["Puntos"] = puntos
        registro["Resultado"] = resultado
        registro["Victoria"] = 1 if resultado == "V" else 0
        registro["Empate"] = 1 if resultado == "E" else 0
        registro["Derrota"] = 1 if resultado == "D" else 0
        registros.append(registro)
    return registros


def partidos_a_equipo_partido(tabla_partidos):
    """Aplica filas_de_un_partido a todos los partidos."""
    registros = []
    for _, fila in tabla_partidos.iterrows():
        registros.extend(filas_de_un_partido(fila))
    return pd.DataFrame(registros)


def agregar_numero_partido(equipo_partido):
    """Agrega el número de partido de cada equipo (1 a 38, por fecha) y los puntos acumulados."""
    if equipo_partido.duplicated(["Temporada", "Equipo", "Fecha"]).any():
        raise ValueError("Un equipo tiene dos partidos el mismo día: el orden sería ambiguo.")
    tabla = equipo_partido.sort_values(["Temporada", "Equipo", "Fecha"]).reset_index(drop=True)
    grupos = tabla.groupby(["Temporada", "Equipo"])
    tabla["NumeroPartido"] = grupos.cumcount() + 1
    tabla["PuntosAcumulados"] = grupos["Puntos"].cumsum()
    return tabla


def resumir_equipos(registros):
    """Suma los partidos de cada equipo en cada temporada y calcula promedios por partido."""
    grupos = registros.groupby(["Temporada", "Equipo"])
    resumen = grupos[COLUMNAS_A_SUMAR].sum()
    resumen.insert(0, "PJ", grupos.size())
    # count() no cuenta celdas vacías: así sabemos en cuántos partidos hay dato de tiros.
    resumen["PartidosConTiros"] = grupos["Tiros"].count()
    resumen = resumen.reset_index()

    resumen = resumen.rename(columns={"Victoria": "V", "Empate": "E", "Derrota": "D"})
    resumen["DG"] = resumen["GolesFavor"] - resumen["GolesContra"]

    resumen["PuntosPorPartido"] = resumen["Puntos"] / resumen["PJ"]
    resumen["GolesFavorPorPartido"] = resumen["GolesFavor"] / resumen["PJ"]
    resumen["GolesContraPorPartido"] = resumen["GolesContra"] / resumen["PJ"]
    resumen["TirosPorPartido"] = resumen["Tiros"] / resumen["PartidosConTiros"]
    resumen["TirosArcoPorPartido"] = resumen["TirosArco"] / resumen["PartidosConTiros"]
    resumen["CornersPorPartido"] = resumen["Corners"] / resumen["PJ"]
    resumen["FaltasPorPartido"] = resumen["Faltas"] / resumen["PJ"]
    resumen["AmarillasPorPartido"] = resumen["Amarillas"] / resumen["PJ"]
    resumen["RojasPorPartido"] = resumen["Rojas"] / resumen["PJ"]
    return resumen


def estadisticas_por_condicion(equipo_partido):
    """Calcula las estadísticas por equipo y temporada para Total, Local y Visitante."""
    subconjuntos = {
        "Total": equipo_partido,
        "Local": equipo_partido[equipo_partido["Condicion"] == "Local"],
        "Visitante": equipo_partido[equipo_partido["Condicion"] == "Visitante"],
    }
    tablas = []
    for condicion, registros in subconjuntos.items():
        tabla = resumir_equipos(registros)
        tabla.insert(2, "Condicion", condicion)
        tablas.append(tabla)
    return pd.concat(tablas, ignore_index=True)


def calcular_clasificacion(estadisticas_condicion):
    """Ordena los equipos de cada temporada por puntos, diferencia de goles y goles a favor."""
    tabla = estadisticas_condicion.sort_values(
        ["Temporada"] + CRITERIOS_CLASIFICACION, ascending=[True, False, False, False]
    ).reset_index(drop=True)
    tabla.insert(0, "Posicion", tabla.groupby("Temporada").cumcount() + 1)
    return tabla


def empates_sin_resolver(clasificacion):
    """Devuelve los equipos que siguen empatados después de los tres criterios."""
    repetidos = clasificacion.duplicated(["Temporada"] + CRITERIOS_CLASIFICACION, keep=False)
    return clasificacion[repetidos]
