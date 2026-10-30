"""Búsqueda de partidos y presentación de sus resultados."""

import pandas as pd

ESTADISTICAS_PARTIDO = {
    "Goles": ("FTHG", "FTAG"),
    "Goles al descanso": ("HTHG", "HTAG"),
    "Tiros": ("HS", "AS"),
    "Tiros al arco": ("HST", "AST"),
    "Córners": ("HC", "AC"),
    "Faltas": ("HF", "AF"),
    "Tarjetas amarillas": ("HY", "AY"),
    "Tarjetas rojas": ("HR", "AR"),
}


def fecha_texto(fecha):
    """Fecha en formato día/mes/año."""
    fecha = pd.Timestamp(fecha)
    return f"{fecha.day:02d}/{fecha.month:02d}/{fecha.year}"


def partidos_de_temporada(partidos, temporada):
    """Partidos de una temporada ordenados por fecha."""
    tabla = partidos[partidos["Temporada"] == temporada]
    return tabla.sort_values("Date").reset_index(drop=True)


def partidos_de_equipo(partidos_temporada, equipo):
    """Partidos de un equipo, de local o de visitante."""
    filtro = (partidos_temporada["HomeTeam"] == equipo) | (partidos_temporada["AwayTeam"] == equipo)
    return partidos_temporada[filtro].reset_index(drop=True)


def enfrentamientos(partidos_temporada, equipo_a, equipo_b):
    """Partidos entre dos equipos, sin importar quién jugó de local."""
    ida = (partidos_temporada["HomeTeam"] == equipo_a) & (partidos_temporada["AwayTeam"] == equipo_b)
    vuelta = (partidos_temporada["HomeTeam"] == equipo_b) & (partidos_temporada["AwayTeam"] == equipo_a)
    return partidos_temporada[ida | vuelta].sort_values("Date").reset_index(drop=True)


def marcador(fila):
    """Texto del resultado, por ejemplo 'Arsenal 2-1 Liverpool'."""
    return f"{fila['HomeTeam']} {int(fila['FTHG'])}-{int(fila['FTAG'])} {fila['AwayTeam']}"


def ganador(fila):
    """Nombre del ganador del partido, o None si fue empate."""
    if fila["FTHG"] > fila["FTAG"]:
        return fila["HomeTeam"]
    elif fila["FTHG"] < fila["FTAG"]:
        return fila["AwayTeam"]
    else:
        return None


def goles_de(fila, equipo):
    """Goles que marcó un equipo en un partido."""
    if fila["HomeTeam"] == equipo:
        return int(fila["FTHG"])
    return int(fila["FTAG"])


def valor_de(fila, equipo, nombre_estadistica):
    """Valor de una estadística para uno de los equipos del partido (None si no hay dato)."""
    columna_local, columna_visitante = ESTADISTICAS_PARTIDO[nombre_estadistica]
    valor = fila[columna_local] if fila["HomeTeam"] == equipo else fila[columna_visitante]
    if pd.isna(valor):
        return None
    return int(valor)


def ficha_partido(fila):
    """Tabla con las estadísticas del local y del visitante de un partido."""
    filas = []
    for nombre, (columna_local, columna_visitante) in ESTADISTICAS_PARTIDO.items():
        local = fila[columna_local]
        visitante = fila[columna_visitante]
        filas.append({
            "Estadística": nombre,
            fila["HomeTeam"]: "sin dato" if pd.isna(local) else int(local),
            fila["AwayTeam"]: "sin dato" if pd.isna(visitante) else int(visitante),
        })
    return pd.DataFrame(filas)


def tabla_resumen(partidos_tabla):
    """Lista de partidos lista para mostrar: fecha, local, resultado, visitante y estadísticas."""
    filas = []
    for _, fila in partidos_tabla.iterrows():
        filas.append({
            "Fecha": fecha_texto(fila["Date"]),
            "Local": fila["HomeTeam"],
            "Resultado": f"{int(fila['FTHG'])} - {int(fila['FTAG'])}",
            "Visitante": fila["AwayTeam"],
            "Tiros": f"{_texto(fila['HS'])} - {_texto(fila['AS'])}",
            "Tiros al arco": f"{_texto(fila['HST'])} - {_texto(fila['AST'])}",
            "Córners": f"{int(fila['HC'])} - {int(fila['AC'])}",
            "Tarjetas": f"{int(fila['HY'] + fila['HR'])} - {int(fila['AY'] + fila['AR'])}",
        })
    return pd.DataFrame(filas)


def _texto(valor):
    return "–" if pd.isna(valor) else str(int(valor))
