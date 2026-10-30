"""Relaciones entre las estadísticas de los equipos: matriz de correlación y explicaciones.

Cada observación es un equipo en una temporada (datos agregados). Todas las variables
son promedios por partido, para no mezclar totales con valores de un solo partido.
"""

import pandas as pd

from src.analisis import correlacion, fuerza

# Nombre visible -> columna (todas por partido).
VARIABLES = {
    "Goles anotados": "GolesFavorPorPartido",
    "Goles recibidos": "GolesContraPorPartido",
    "Puntos": "PuntosPorPartido",
    "Victorias": "VictoriasPorPartido",
    "Derrotas": "DerrotasPorPartido",
    "Tiros": "TirosPorPartido",
    "Tiros al arco": "TirosArcoPorPartido",
    "Córners": "CornersPorPartido",
    "Faltas": "FaltasPorPartido",
    "Tarjetas": "TarjetasPorPartido",
}

# Las siete relaciones que pide estudiar el proyecto: (variable x, variable y).
RELACIONES = [
    ("Tiros", "Goles anotados"),
    ("Tiros al arco", "Goles anotados"),
    ("Córners", "Goles anotados"),
    ("Faltas", "Tarjetas"),
    ("Goles anotados", "Puntos"),
    ("Goles recibidos", "Derrotas"),
    ("Tiros al arco", "Puntos"),
]


def preparar_tabla(estadisticas, condicion="Total", temporada=None):
    """Equipo-temporada de una condición, con las columnas por partido que faltan.

    temporada=None usa las cinco temporadas (100 equipo-temporada).
    """
    tabla = estadisticas[estadisticas["Condicion"] == condicion].copy()
    if temporada is not None:
        tabla = tabla[tabla["Temporada"] == temporada]
    tabla["VictoriasPorPartido"] = tabla["V"] / tabla["PJ"]
    tabla["DerrotasPorPartido"] = tabla["D"] / tabla["PJ"]
    tabla["TarjetasPorPartido"] = tabla["AmarillasPorPartido"] + tabla["RojasPorPartido"]
    return tabla.reset_index(drop=True)


def matriz_correlacion(tabla, nombres):
    """Matriz de correlación de Pearson entre las variables elegidas (con dos ciclos)."""
    matriz = pd.DataFrame(index=nombres, columns=nombres, dtype=float)
    for fila in nombres:
        for columna in nombres:
            matriz.loc[fila, columna] = correlacion(tabla[VARIABLES[fila]], tabla[VARIABLES[columna]])
    return matriz


def matriz_formato_largo(matriz):
    """La matriz en filas (Variable 1, Variable 2, r) para dibujar el mapa de calor."""
    filas = []
    for fila in matriz.index:
        for columna in matriz.columns:
            filas.append({"Variable 1": fila, "Variable 2": columna, "r": round(matriz.loc[fila, columna], 2)})
    return pd.DataFrame(filas)


def datos_dispersion(tabla, nombre_x, nombre_y):
    """Puntos del gráfico de dispersión: un punto por equipo-temporada."""
    datos = tabla[["Equipo", "Temporada"]].copy()
    datos["x"] = tabla[VARIABLES[nombre_x]].round(3)
    datos["y"] = tabla[VARIABLES[nombre_y]].round(3)
    return datos


def explicar(r, nombre_x, nombre_y, n):
    """Explicación sencilla de una correlación, sin hablar de causas."""
    texto_r = f"{r:.2f}".replace(".", ",")
    if abs(r) < 0.1:
        return (f"r = {texto_r} con {n} equipo-temporada: prácticamente no hay relación lineal entre "
                f"{nombre_x.lower()} y {nombre_y.lower()} por partido.")
    if r > 0:
        sentido = f"los equipos con más {nombre_x.lower()} por partido tienden a tener más {nombre_y.lower()}"
    else:
        sentido = f"los equipos con más {nombre_x.lower()} por partido tienden a tener menos {nombre_y.lower()}"
    signo = "positiva" if r > 0 else "negativa"
    porcentaje = round(100 * r ** 2)
    texto_r2 = f"{r ** 2:.2f}".replace(".", ",")
    return (f"r = {texto_r} con {n} equipo-temporada: relación {fuerza(r)} y {signo}. "
            f"En general, {sentido}. La recta explica cerca del {porcentaje} % de la variación "
            f"(r² = {texto_r2}). Es una relación estadística: no demuestra que una cosa cause la otra.")


def tabla_relaciones(tabla):
    """Correlación de cada una de las siete relaciones del proyecto."""
    filas = []
    for nombre_x, nombre_y in RELACIONES:
        r = correlacion(tabla[VARIABLES[nombre_x]], tabla[VARIABLES[nombre_y]])
        filas.append({"Relación": f"{nombre_x} y {nombre_y.lower()}", "r": round(r, 2),
                      "Fuerza": fuerza(r), "Sentido": "positiva" if r > 0 else "negativa"})
    return pd.DataFrame(filas)
