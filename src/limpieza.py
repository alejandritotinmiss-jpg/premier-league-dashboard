"""Carga, validación y limpieza de los CSV de cada temporada."""

from pathlib import Path

import pandas as pd

# Una temporada completa de 20 equipos tiene 380 partidos (cada equipo juega 19 de local y 19 de visitante).
PARTIDOS_TEMPORADA_COMPLETA = 380


def descubrir_temporadas(carpeta_raw):
    """Busca los archivos season-AABB.csv y devuelve {"20AA/BB": nombre del archivo}.

    Así no hay una lista fija de temporadas: basta con agregar el CSV de una
    temporada nueva a data/raw/ para que aparezca en toda la aplicación.
    """
    temporadas = {}
    for ruta in sorted(Path(carpeta_raw).glob("season-*.csv")):
        codigo = ruta.stem.replace("season-", "")          # por ejemplo "2526"
        if len(codigo) == 4 and codigo.isdigit():
            temporadas[f"20{codigo[:2]}/{codigo[2:]}"] = ruta.name
    return temporadas

COLUMNAS_ESPERADAS = [
    "Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR",
    "HTHG", "HTAG", "HTR", "Referee", "HS", "AS", "HST", "AST",
    "HF", "AF", "HC", "AC", "HY", "AY", "HR", "AR",
]

COLUMNAS_NUMERICAS = [
    "FTHG", "FTAG", "HTHG", "HTAG", "HS", "AS", "HST", "AST",
    "HF", "AF", "HC", "AC", "HY", "AY", "HR", "AR",
]

COLUMNAS_TIROS = ["HS", "AS", "HST", "AST"]


def cargar_temporada(ruta_csv, temporada):
    """Lee el CSV de una temporada y le agrega la columna Temporada."""
    df = pd.read_csv(ruta_csv)
    # Si una fecha no se puede leer queda vacía y la validación la detecta.
    df["Date"] = pd.to_datetime(df["Date"], format="%Y-%m-%d", errors="coerce")
    df.insert(0, "Temporada", temporada)
    return df


def columnas_coinciden(df):
    """Revisa que el archivo tenga las columnas esperadas en el mismo orden."""
    columnas = list(df.columns.drop("Temporada"))
    return columnas == COLUMNAS_ESPERADAS


def contar_nulos(df):
    """Cuenta las celdas vacías de la tabla."""
    return int(df.isna().sum().sum())


def contar_cruces_repetidos(df):
    """Cuenta los partidos repetidos (la pareja local-visitante no se puede repetir)."""
    return int(df.duplicated(["HomeTeam", "AwayTeam"]).sum())


def contar_fechas_fuera_de_temporada(df, temporada):
    """Cuenta las fechas vacías o que no caen entre agosto y junio de la temporada."""
    anio_inicio = int(temporada[:4])
    inicio = pd.Timestamp(f"{anio_inicio}-08-01")
    fin = pd.Timestamp(f"{anio_inicio + 1}-06-30")
    fuera = df["Date"].isna() | (df["Date"] < inicio) | (df["Date"] > fin)
    return int(fuera.sum())


def equipos_con_calendario_incompleto(df):
    """Lista los equipos que no jugaron 19 partidos de local y 19 de visitante."""
    partidos_local = df["HomeTeam"].value_counts()
    partidos_visitante = df["AwayTeam"].value_counts()
    equipos = sorted(set(df["HomeTeam"]) | set(df["AwayTeam"]))
    incompletos = []
    for equipo in equipos:
        local = int(partidos_local.get(equipo, 0))
        visitante = int(partidos_visitante.get(equipo, 0))
        if local != 19 or visitante != 19:
            incompletos.append(f"{equipo}: {local} local, {visitante} visitante")
    return incompletos


def equipos_con_partidos_de_mas(df):
    """Lista los equipos con más de 19 partidos de local o de visitante (no puede pasar)."""
    partidos_local = df["HomeTeam"].value_counts()
    partidos_visitante = df["AwayTeam"].value_counts()
    de_mas = []
    for equipo in sorted(set(df["HomeTeam"]) | set(df["AwayTeam"])):
        if partidos_local.get(equipo, 0) > 19 or partidos_visitante.get(equipo, 0) > 19:
            de_mas.append(equipo)
    return de_mas


def equipos_sin_local_o_visitante(df):
    """Lista los equipos que todavía no jugaron de local o no jugaron de visitante."""
    locales = set(df["HomeTeam"])
    visitantes = set(df["AwayTeam"])
    return sorted(locales ^ visitantes)      # ^ = los que están en un conjunto y no en el otro


def resultado_esperado(goles_local, goles_visitante):
    """Devuelve el resultado de un marcador: H (gana local), D (empate) o A (gana visitante)."""
    if goles_local > goles_visitante:
        return "H"
    elif goles_local < goles_visitante:
        return "A"
    else:
        return "D"


def contar_resultados_incoherentes(df):
    """Cuenta los partidos cuyo resultado FTR no coincide con los goles."""
    incoherentes = 0
    for goles_local, goles_visitante, resultado in zip(df["FTHG"], df["FTAG"], df["FTR"]):
        if resultado != resultado_esperado(goles_local, goles_visitante):
            incoherentes += 1
    return incoherentes


def buscar_tiros_imposibles(df):
    """Busca equipos con más tiros al arco que tiros en un partido."""
    casos = []
    for indice in df.index:
        fila = df.loc[indice]
        partido = f"{fila['HomeTeam']} {fila['FTHG']}-{fila['FTAG']} {fila['AwayTeam']}"
        if fila["HST"] > fila["HS"]:
            casos.append({"indice": int(indice), "fecha": str(fila["Date"].date()),
                          "partido": partido, "equipo": fila["HomeTeam"],
                          "condicion": "local", "tiros": int(fila["HS"]),
                          "tiros_al_arco": int(fila["HST"])})
        if fila["AST"] > fila["AS"]:
            casos.append({"indice": int(indice), "fecha": str(fila["Date"].date()),
                          "partido": partido, "equipo": fila["AwayTeam"],
                          "condicion": "visitante", "tiros": int(fila["AS"]),
                          "tiros_al_arco": int(fila["AST"])})
    return casos


def validar_temporada(df, temporada):
    """Aplica todas las comprobaciones a una temporada y devuelve un diccionario con los resultados."""
    equipos = set(df["HomeTeam"]) | set(df["AwayTeam"])
    return {
        "filas": len(df),
        "completa": len(df) == PARTIDOS_TEMPORADA_COMPLETA,
        "equipos": len(equipos),
        "columnas_correctas": columnas_coinciden(df),
        "celdas_vacias": contar_nulos(df),
        "partidos_repetidos": contar_cruces_repetidos(df),
        "fechas_fuera": contar_fechas_fuera_de_temporada(df, temporada),
        "calendario_incompleto": len(equipos_con_calendario_incompleto(df)),
        "equipos_con_partidos_de_mas": len(equipos_con_partidos_de_mas(df)),
        "equipos_sin_local_o_visitante": len(equipos_sin_local_o_visitante(df)),
        "resultados_incoherentes": contar_resultados_incoherentes(df),
        "tiros_imposibles": len(buscar_tiros_imposibles(df)),
    }


def temporada_es_valida(validacion, puede_estar_en_curso=False):
    """Indica si una temporada pasa las comprobaciones (los tiros imposibles se corrigen después).

    Una temporada terminada debe tener los 380 partidos. Solo la temporada más reciente
    puede estar en curso (puede_estar_en_curso=True): entonces se aceptan menos partidos,
    pero todos los que haya deben ser correctos y los 20 equipos deben haber jugado ya
    al menos un partido de local y uno de visitante (pasa tras las primeras jornadas).
    """
    sin_errores = (
        validacion["columnas_correctas"]
        and validacion["celdas_vacias"] == 0
        and validacion["partidos_repetidos"] == 0
        and validacion["fechas_fuera"] == 0
        and validacion["resultados_incoherentes"] == 0
        and validacion["equipos_con_partidos_de_mas"] == 0
    )
    if not sin_errores:
        return False
    if validacion["completa"]:
        return validacion["equipos"] == 20 and validacion["calendario_incompleto"] == 0
    return puede_estar_en_curso and 0 < validacion["filas"] < PARTIDOS_TEMPORADA_COMPLETA \
        and validacion["equipos"] == 20 and validacion["equipos_sin_local_o_visitante"] == 0


def limpiar_temporada(df):
    """Quita la columna Referee y vacía los tiros imposibles (decisión A del equipo)."""
    limpio = df.drop(columns=["Referee"])
    # Una columna de enteros no admite celdas vacías, por eso se pasa a decimales.
    limpio[COLUMNAS_TIROS] = limpio[COLUMNAS_TIROS].astype(float)

    cambios = []
    for caso in buscar_tiros_imposibles(df):
        if caso["condicion"] == "local":
            columnas = ["HS", "HST"]
        else:
            columnas = ["AS", "AST"]
        limpio.loc[caso["indice"], columnas] = float("nan")
        caso["columnas_vaciadas"] = columnas
        cambios.append(caso)
    return limpio, cambios
