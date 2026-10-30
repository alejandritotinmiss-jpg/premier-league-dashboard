"""Estadísticas descriptivas y correlaciones con NumPy."""

import numpy as np
import pandas as pd

VARIABLES_JUEGO = {
    "TirosPorPartido": "Tiros",
    "TirosArcoPorPartido": "Tiros al arco",
    "CornersPorPartido": "Córners",
    "FaltasPorPartido": "Faltas",
    "AmarillasPorPartido": "Amarillas",
    "RojasPorPartido": "Rojas",
}


def estadisticas_descriptivas(valores):
    """Calcula n, media, mediana, desviación estándar, mínimo y máximo con NumPy."""
    arreglo = np.asarray(valores, dtype=float)
    if np.isnan(arreglo).any():
        raise ValueError("Hay valores faltantes: hay que tratarlos antes de calcular.")
    return {
        "n": len(arreglo),
        "Media": np.mean(arreglo),
        "Mediana": np.median(arreglo),
        "Desv. estándar": np.std(arreglo, ddof=1),
        "Mínimo": np.min(arreglo),
        "Máximo": np.max(arreglo),
    }


def correlacion(x, y):
    """Correlación de Pearson entre dos variables (r entre -1 y 1)."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if len(x) != len(y):
        raise ValueError("Las dos variables deben tener el mismo número de observaciones.")
    if len(x) < 3:
        raise ValueError("Se necesitan al menos 3 observaciones.")
    if np.isnan(x).any() or np.isnan(y).any():
        raise ValueError("Hay valores faltantes.")
    # np.corrcoef devuelve una matriz 2x2; la posición [0, 1] es la correlación entre x e y.
    return float(np.corrcoef(x, y)[0, 1])


def fuerza(r):
    """Clasifica una correlación como débil, moderada o fuerte."""
    if abs(r) < 0.3:
        return "débil"
    elif abs(r) <= 0.7:
        return "moderada"
    else:
        return "fuerte"


def tabla_correlaciones(estadisticas, condiciones=("Local", "Visitante"), temporada=None):
    """Correlación de cada variable de juego con los puntos por partido.

    Con temporada=None usa las cinco temporadas (100 equipo-temporada).
    """
    filas = []
    for condicion in condiciones:
        tabla = estadisticas[estadisticas["Condicion"] == condicion]
        if temporada is not None:
            tabla = tabla[tabla["Temporada"] == temporada]
        for columna, nombre in VARIABLES_JUEGO.items():
            filas.append({
                "Variable": nombre,
                "Condicion": condicion,
                "n": len(tabla),
                "r": correlacion(tabla[columna], tabla["PuntosPorPartido"]),
            })
    return pd.DataFrame(filas)
