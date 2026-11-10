"""Variables del modelo predictivo: lo que se sabía de cada equipo ANTES de cada partido.

Regla principal (para que no haya "fuga de datos"): las variables de un partido solo
usan partidos de fechas ANTERIORES. Los partidos del mismo día tampoco se usan, porque
los datos no traen una hora fiable y no se sabe cuál se jugó primero.
"""

import pandas as pd

VENTANA_FORMA = 5            # últimos partidos para la forma reciente
VENTANA_NIVEL = 38           # últimos partidos para el nivel del equipo (una temporada)
VENTANA_CONDICION = 10       # últimos partidos en casa (local) o fuera (visitante)
MINIMO_PARTIDOS = 5          # con menos partidos anteriores no se calcula el promedio
ANTIGUEDAD_MAXIMA_DIAS = 365  # no se usan partidos de hace más de un año

# Promedios por partido de cada equipo. Nombre de la variable -> (ventana, dato del partido).
VARIABLES_EQUIPO = {
    "forma_puntos": (VENTANA_FORMA, "puntos"),
    "forma_goles_favor": (VENTANA_FORMA, "goles_favor"),
    "forma_goles_contra": (VENTANA_FORMA, "goles_contra"),
    "nivel_puntos": (VENTANA_NIVEL, "puntos"),
    "nivel_dif_goles": (VENTANA_NIVEL, "dif_goles"),
    "nivel_tiros": (VENTANA_NIVEL, "tiros"),
    "nivel_tiros_arco": (VENTANA_NIVEL, "tiros_arco"),
    "nivel_corners": (VENTANA_NIVEL, "corners"),
    "nivel_faltas": (VENTANA_NIVEL, "faltas"),
    "nivel_tarjetas": (VENTANA_NIVEL, "tarjetas"),
}

# Nombre para mostrar de cada variable de equipo.
NOMBRES_VARIABLES = {
    "forma_puntos": "Puntos por partido (últimos 5)",
    "forma_goles_favor": "Goles a favor por partido (últimos 5)",
    "forma_goles_contra": "Goles en contra por partido (últimos 5)",
    "nivel_puntos": "Puntos por partido (últimos 38)",
    "nivel_dif_goles": "Diferencia de goles por partido (últimos 38)",
    "nivel_tiros": "Tiros por partido (últimos 38)",
    "nivel_tiros_arco": "Tiros al arco por partido (últimos 38)",
    "nivel_corners": "Córners por partido (últimos 38)",
    "nivel_faltas": "Faltas por partido (últimos 38)",
    "nivel_tarjetas": "Tarjetas por partido (últimos 38)",
    "condicion_puntos": "Puntos por partido en su condición (últimos 10 en casa o fuera)",
}

# Variables que recibe el modelo: diferencias (local - visitante) y cuatro variables propias.
VARIABLES_MODELO = [f"dif_{nombre}" for nombre in VARIABLES_EQUIPO] + [
    "local_puntos_en_casa", "visitante_puntos_fuera", "local_sin_historial", "visitante_sin_historial",
]


def registros_de_un_partido(fila):
    """Convierte un partido en dos registros (local y visitante) con los datos de cada equipo."""
    lados = [
        ("Local", "HomeTeam", "FTHG", "FTAG", "HS", "HST", "HC", "HF", "HY", "HR"),
        ("Visitante", "AwayTeam", "FTAG", "FTHG", "AS", "AST", "AC", "AF", "AY", "AR"),
    ]
    registros = []
    for condicion, equipo, favor, contra, tiros, arco, corners, faltas, amarillas, rojas in lados:
        goles_favor, goles_contra = fila[favor], fila[contra]
        if goles_favor > goles_contra:
            puntos = 3
        elif goles_favor == goles_contra:
            puntos = 1
        else:
            puntos = 0
        registros.append({
            "equipo": fila[equipo], "fecha": fila["Date"], "condicion": condicion,
            "puntos": puntos, "goles_favor": goles_favor, "goles_contra": goles_contra,
            "dif_goles": goles_favor - goles_contra, "tiros": fila[tiros], "tiros_arco": fila[arco],
            "corners": fila[corners], "faltas": fila[faltas], "tarjetas": fila[amarillas] + fila[rojas],
        })
    return registros


def construir_historial(partidos):
    """Diccionario equipo -> lista de sus partidos jugados, del más antiguo al más reciente."""
    historial = {}
    for _, fila in partidos.sort_values("Date", kind="stable").iterrows():
        for registro in registros_de_un_partido(fila):
            historial.setdefault(registro["equipo"], []).append(registro)
    return historial


def partidos_anteriores(historial, equipo, fecha, cantidad, condicion=None):
    """Últimos partidos del equipo jugados ANTES de la fecha (nunca el mismo día ni después)."""
    fecha = pd.Timestamp(fecha)
    limite = fecha - pd.Timedelta(days=ANTIGUEDAD_MAXIMA_DIAS)
    anteriores = []
    for registro in historial.get(equipo, []):
        if limite <= registro["fecha"] < fecha and condicion in (None, registro["condicion"]):
            anteriores.append(registro)
    return anteriores[-cantidad:]


def promedio(registros, dato):
    """Promedio de un dato en varios partidos; vacío (NaN) si hay menos de MINIMO_PARTIDOS."""
    valores = [registro[dato] for registro in registros if not pd.isna(registro[dato])]
    if len(valores) < MINIMO_PARTIDOS:
        return float("nan")
    return sum(valores) / len(valores)


def perfil_equipo(historial, equipo, fecha, condicion):
    """Todo lo que se sabía del equipo antes de la fecha: forma, nivel y rendimiento en su condición."""
    perfil = {}
    for nombre, (ventana, dato) in VARIABLES_EQUIPO.items():
        perfil[nombre] = promedio(partidos_anteriores(historial, equipo, fecha, ventana), dato)
    en_su_condicion = partidos_anteriores(historial, equipo, fecha, VENTANA_CONDICION, condicion)
    perfil["condicion_puntos"] = promedio(en_su_condicion, "puntos")

    recientes = partidos_anteriores(historial, equipo, fecha, VENTANA_FORMA)
    letras = {3: "V", 1: "E", 0: "D"}
    perfil["ultimos_resultados"] = "".join(letras[registro["puntos"]] for registro in recientes)
    perfil["partidos_previos"] = len(partidos_anteriores(historial, equipo, fecha, VENTANA_NIVEL))
    # Un equipo recién ascendido no tiene partidos de Premier League del último año.
    perfil["sin_historial"] = 1 if perfil["partidos_previos"] < MINIMO_PARTIDOS else 0
    return perfil


def variables_del_partido(historial, local, visitante, fecha):
    """Variables del modelo para un partido y los perfiles de los dos equipos."""
    perfil_local = perfil_equipo(historial, local, fecha, "Local")
    perfil_visitante = perfil_equipo(historial, visitante, fecha, "Visitante")
    variables = {}
    for nombre in VARIABLES_EQUIPO:
        variables[f"dif_{nombre}"] = perfil_local[nombre] - perfil_visitante[nombre]
    variables["local_puntos_en_casa"] = perfil_local["condicion_puntos"]
    variables["visitante_puntos_fuera"] = perfil_visitante["condicion_puntos"]
    variables["local_sin_historial"] = perfil_local["sin_historial"]
    variables["visitante_sin_historial"] = perfil_visitante["sin_historial"]
    return variables, perfil_local, perfil_visitante


def tabla_del_modelo(partidos, historial=None):
    """Una fila por partido jugado: sus variables previas y el resultado real (H, D o A)."""
    if historial is None:
        historial = construir_historial(partidos)
    filas = []
    for _, fila in partidos.sort_values("Date", kind="stable").iterrows():
        variables, _, _ = variables_del_partido(historial, fila["HomeTeam"], fila["AwayTeam"], fila["Date"])
        variables.update({"Temporada": fila["Temporada"], "Date": fila["Date"], "HomeTeam": fila["HomeTeam"],
                          "AwayTeam": fila["AwayTeam"], "Resultado": fila["FTR"]})
        filas.append(variables)
    columnas = ["Temporada", "Date", "HomeTeam", "AwayTeam", "Resultado"] + VARIABLES_MODELO
    return pd.DataFrame(filas)[columnas].reset_index(drop=True)
