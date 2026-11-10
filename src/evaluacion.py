"""Evaluación del modelo predictivo con validación cronológica.

Nunca se mezclan los partidos al azar: el modelo siempre se entrena con partidos
anteriores y se evalúa con partidos posteriores, como pasaría en la vida real.
"""

import numpy as np
import pandas as pd
from sklearn.metrics import (accuracy_score, balanced_accuracy_score, confusion_matrix, log_loss,
                             precision_recall_fscore_support)

from src.modelo import CLASES, NOMBRES_CLASES, entrenar, probabilidades


def brier_multiclase(reales, tabla_probabilidades):
    """Brier score: error cuadrático medio de las probabilidades (0 es perfecto, 2 es lo peor)."""
    errores = 0.0
    for clase in CLASES:
        ocurrio = (np.asarray(reales) == clase).astype(float)
        errores += np.mean((tabla_probabilidades[clase].to_numpy() - ocurrio) ** 2)
    return float(errores)


def log_loss_ordenado(reales, tabla_probabilidades):
    """Log loss (0 es perfecto; cuanto más bajo, mejor). Castiga mucho la seguridad equivocada.

    scikit-learn espera las clases en orden alfabético (A, D, H), así que las columnas
    de probabilidades se pasan en ese mismo orden.
    """
    orden = sorted(CLASES)
    return float(log_loss(reales, tabla_probabilidades[orden].to_numpy(), labels=orden))


def calcular_metricas(reales, tabla_probabilidades):
    """Todas las métricas de un conjunto de partidos a partir de sus probabilidades."""
    reales = np.asarray(reales)
    # La predicción es el resultado con la probabilidad más alta.
    predichos = tabla_probabilidades[CLASES].idxmax(axis=1).to_numpy()
    precision, recall, f1, casos = precision_recall_fscore_support(
        reales, predichos, labels=CLASES, zero_division=0)
    por_clase = {}
    for posicion, clase in enumerate(CLASES):
        por_clase[NOMBRES_CLASES[clase]] = {
            "precision": float(precision[posicion]), "recall": float(recall[posicion]),
            "f1": float(f1[posicion]), "partidos_reales": int(casos[posicion]),
            "veces_predicho": int((predichos == clase).sum()),
        }
    return {
        "partidos": int(len(reales)),
        "accuracy": float(accuracy_score(reales, predichos)),
        "balanced_accuracy": float(balanced_accuracy_score(reales, predichos)),
        "f1_macro": float(np.mean(f1)),
        "log_loss": log_loss_ordenado(reales, tabla_probabilidades),
        "brier": brier_multiclase(reales, tabla_probabilidades),
        "por_clase": por_clase,
        # Filas: resultado real. Columnas: resultado predicho. Orden: H, D, A.
        "matriz_confusion": confusion_matrix(reales, predichos, labels=CLASES).tolist(),
    }


def probabilidades_baseline(entrenamiento, cantidad):
    """Baseline histórico: a todos los partidos les da la frecuencia de H, D y A del entrenamiento."""
    frecuencias = entrenamiento["Resultado"].value_counts(normalize=True)
    fila = {clase: float(frecuencias.get(clase, 0.0)) for clase in CLASES}
    return pd.DataFrame([fila] * cantidad)


def evaluar(entrenamiento, prueba, c):
    """Entrena con un periodo y evalúa en otro posterior. Devuelve métricas del modelo y del baseline."""
    if entrenamiento["Date"].max() >= prueba["Date"].min():
        raise ValueError("El periodo de prueba debe ser posterior al de entrenamiento.")
    modelo = entrenar(entrenamiento, c)
    tabla = probabilidades(modelo, prueba)
    return {
        "entrenamiento": resumen_periodo(entrenamiento),
        "prueba": resumen_periodo(prueba),
        "modelo": calcular_metricas(prueba["Resultado"], tabla),
        "baseline": calcular_metricas(prueba["Resultado"], probabilidades_baseline(entrenamiento, len(prueba))),
    }, tabla


def resumen_periodo(tabla):
    return {"desde": str(pd.Timestamp(tabla["Date"].min()).date()),
            "hasta": str(pd.Timestamp(tabla["Date"].max()).date()), "partidos": int(len(tabla))}


def backtesting(tabla, temporadas_de_prueba, c):
    """Para cada temporada: entrena con todas las anteriores y predice esa temporada.

    Es la forma de comprobar cómo le habría ido al modelo en el pasado sin usar el futuro.
    """
    resultados = []
    todas = []
    for temporada in temporadas_de_prueba:
        prueba = tabla[tabla["Temporada"] == temporada]
        entrenamiento = tabla[tabla["Date"] < prueba["Date"].min()]
        resultado, probabilidad = evaluar(entrenamiento, prueba, c)
        resultado["temporada"] = temporada
        resultados.append(resultado)
        todas.append(probabilidad.assign(Resultado=prueba["Resultado"].to_numpy()))
    return resultados, pd.concat(todas, ignore_index=True)


def tabla_calibracion(reales, tabla_probabilidades, tramos=5):
    """Compara lo que el modelo dijo con lo que pasó.

    Junta las probabilidades de los tres resultados en tramos (0-20 %, 20-40 %...). Si el
    modelo está bien calibrado, de las veces que dijo "cerca del 30 %" debió pasar cerca
    del 30 % de las veces.
    """
    predichas, ocurridas = [], []
    for clase in CLASES:
        predichas.extend(tabla_probabilidades[clase].tolist())
        ocurridas.extend((np.asarray(reales) == clase).astype(int).tolist())
    datos = pd.DataFrame({"predicha": predichas, "ocurrio": ocurridas})
    limites = np.linspace(0, 1, tramos + 1)
    filas = []
    for inicio, fin in zip(limites[:-1], limites[1:]):
        if fin == 1:
            grupo = datos[(datos["predicha"] >= inicio) & (datos["predicha"] <= fin)]
        else:
            grupo = datos[(datos["predicha"] >= inicio) & (datos["predicha"] < fin)]
        if grupo.empty:
            continue
        filas.append({"tramo": f"{int(inicio * 100)}-{int(fin * 100)} %", "casos": int(len(grupo)),
                      "probabilidad_media": float(grupo["predicha"].mean()),
                      "frecuencia_real": float(grupo["ocurrio"].mean())})
    return filas
