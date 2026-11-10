"""Calendario de la temporada en curso: partidos que todavía no se han jugado.

El calendario viene de una fuente distinta a la de los resultados (fixturedownload.com),
así que sirve para saber qué partidos faltan sin depender del archivo de resultados.
"""

from pathlib import Path

import pandas as pd

RAIZ_PROYECTO = Path(__file__).resolve().parent.parent
CARPETA_CALENDARIO = RAIZ_PROYECTO / "data" / "calendario"
COLUMNAS_CALENDARIO = ["Jornada", "FechaUTC", "HomeTeam", "AwayTeam"]

# El calendario escribe dos equipos distinto a los CSV de resultados.
NOMBRES_CALENDARIO = {"Man Utd": "Man United", "Spurs": "Tottenham"}


def ruta_calendario(temporada, carpeta=CARPETA_CALENDARIO):
    """Ruta del calendario de una temporada: "2026/27" -> calendario-2627.csv."""
    return Path(carpeta) / f"calendario-{temporada[2:4]}{temporada[5:7]}.csv"


def cargar_calendario(temporada, carpeta=CARPETA_CALENDARIO):
    """Lee el calendario de la temporada; devuelve una tabla vacía si no hay archivo."""
    ruta = ruta_calendario(temporada, carpeta)
    if not ruta.exists():
        return pd.DataFrame(columns=COLUMNAS_CALENDARIO + ["Fecha"])
    calendario = pd.read_csv(ruta)
    calendario["FechaUTC"] = pd.to_datetime(calendario["FechaUTC"], utc=True)
    # Fecha sin hora, igual que en los resultados.
    calendario["Fecha"] = calendario["FechaUTC"].dt.tz_localize(None).dt.normalize()
    return calendario


def calendario_es_valido(calendario, equipos):
    """Comprueba el calendario: 380 partidos, 19 en casa por equipo, sin repetidos y con los mismos equipos."""
    if len(calendario) != 380 or calendario["FechaUTC"].isna().any():
        return False
    if calendario.duplicated(["HomeTeam", "AwayTeam"]).any():
        return False
    en_casa = calendario["HomeTeam"].value_counts()
    return set(en_casa.index) == set(equipos) and (en_casa == 19).all()


def partidos_pendientes(calendario, partidos_temporada):
    """Partidos del calendario que todavía no aparecen en los resultados, por orden de fecha."""
    if calendario.empty:
        return calendario
    jugados = set(zip(partidos_temporada["HomeTeam"], partidos_temporada["AwayTeam"]))
    es_pendiente = [(local, visitante) not in jugados
                    for local, visitante in zip(calendario["HomeTeam"], calendario["AwayTeam"])]
    return calendario[es_pendiente].sort_values("FechaUTC", kind="stable").reset_index(drop=True)


def proximos_partidos(pendientes, dias=21):
    """Pendientes de las próximas jornadas: desde el primero hasta `dias` días después."""
    if pendientes.empty:
        return pendientes
    limite = pendientes["Fecha"].min() + pd.Timedelta(days=dias)
    return pendientes[pendientes["Fecha"] <= limite].reset_index(drop=True)


def proximo_partido_de(pendientes, equipo):
    """El siguiente partido pendiente de un equipo (una fila) o None si no hay."""
    filtro = (pendientes["HomeTeam"] == equipo) | (pendientes["AwayTeam"] == equipo)
    if not filtro.any():
        return None
    return pendientes[filtro].iloc[0]


def fecha_y_hora_texto(fecha_utc):
    """Por ejemplo: '21/11/2026 · 12:30 UTC'."""
    fecha = pd.Timestamp(fecha_utc)
    return f"{fecha.day:02d}/{fecha.month:02d}/{fecha.year} · {fecha.hour:02d}:{fecha.minute:02d} UTC"
