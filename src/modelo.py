"""Modelo predictivo: regresión logística multinomial (local gana, empate o visitante gana).

El modelo estima tres probabilidades que suman 1. No "adivina" el resultado: resume
con qué frecuencia ganó el local, se empató o ganó el visitante en partidos anteriores
con variables parecidas.
"""

import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.variables_modelo import NOMBRES_VARIABLES, VARIABLES_EQUIPO, VARIABLES_MODELO, variables_del_partido

CLASES = ["H", "D", "A"]
NOMBRES_CLASES = {"H": "Victoria local", "D": "Empate", "A": "Victoria visitante"}
NOMBRE_MODELO = "Regresión logística multinomial"
# La primera temporada de los datos solo sirve de historial: en ella ningún equipo tiene
# partidos anteriores, así que sus variables saldrían vacías.
TEMPORADA_SOLO_HISTORIAL = "2020/21"


def crear_pipeline(c=1.0):
    """Tres pasos encadenados; todos se ajustan solo con los datos de entrenamiento.

    1. Imputar: rellena las celdas vacías con la mediana de la columna.
    2. Escalar: deja todas las variables con media 0 y desviación 1.
    3. Regresión logística: con el solver "lbfgs" y tres clases es multinomial.
       C controla la regularización (más pequeño = modelo más prudente).
    """
    return Pipeline([
        ("imputar", SimpleImputer(strategy="median")),
        ("escalar", StandardScaler()),
        ("regresion", LogisticRegression(C=c, solver="lbfgs", max_iter=1000)),
    ])


def filas_para_entrenar(tabla):
    """Quita la temporada que solo sirve de historial."""
    return tabla[tabla["Temporada"] != TEMPORADA_SOLO_HISTORIAL].reset_index(drop=True)


def entrenar(tabla, c=1.0):
    """Entrena el modelo con las filas recibidas (variables previas y resultado real)."""
    if len(tabla) < 100 or tabla["Resultado"].nunique() < 3:
        raise ValueError("No hay suficientes partidos para entrenar el modelo (se necesitan al menos 100 "
                         "y que haya victorias locales, empates y victorias visitantes).")
    modelo = crear_pipeline(c)
    modelo.fit(tabla[VARIABLES_MODELO], tabla["Resultado"])
    return modelo


def probabilidades(modelo, variables):
    """Tabla con las probabilidades H, D y A de cada fila, en ese orden."""
    resultado = pd.DataFrame(modelo.predict_proba(variables[VARIABLES_MODELO]),
                             columns=list(modelo.classes_), index=variables.index)
    return resultado[CLASES]


def version_del_modelo(tabla_entrenamiento):
    """Texto que identifica el modelo: con cuántos partidos y hasta qué fecha se entrenó."""
    fecha = pd.Timestamp(tabla_entrenamiento["Date"].max())
    return (f"RL multinomial v1 · {len(tabla_entrenamiento)} partidos · "
            f"hasta {fecha.day:02d}/{fecha.month:02d}/{fecha.year}")


def predecir_partido(modelo, historial, local, visitante, fecha):
    """Probabilidades de un partido usando solo partidos anteriores a la fecha."""
    if local == visitante:
        raise ValueError("El equipo local y el visitante deben ser diferentes.")
    variables, perfil_local, perfil_visitante = variables_del_partido(historial, local, visitante, fecha)
    fila = pd.DataFrame([variables])
    probabilidad = probabilidades(modelo, fila).iloc[0]
    return {
        "local": local, "visitante": visitante, "fecha": pd.Timestamp(fecha),
        "probabilidades": {clase: float(probabilidad[clase]) for clase in CLASES},
        "variables": variables, "perfil_local": perfil_local, "perfil_visitante": perfil_visitante,
        "datos_insuficientes": bool(perfil_local["sin_historial"] or perfil_visitante["sin_historial"]),
    }


def explicar_prediccion(modelo, prediccion):
    """Tabla que explica una predicción: cada variable, su valor y a quién favorece.

    En una regresión logística cada variable suma o resta a la "puntuación" de cada
    resultado. Aquí se compara la puntuación de "gana el local" con la de "gana el
    visitante": un aporte positivo favorece al local y uno negativo al visitante.
    """
    variables = pd.DataFrame([prediccion["variables"]])[VARIABLES_MODELO]
    imputadas = modelo.named_steps["imputar"].transform(variables)
    escaladas = modelo.named_steps["escalar"].transform(imputadas)[0]
    regresion = modelo.named_steps["regresion"]
    clases = list(regresion.classes_)
    diferencia_coeficientes = regresion.coef_[clases.index("H")] - regresion.coef_[clases.index("A")]

    filas = []
    for posicion, variable in enumerate(VARIABLES_MODELO):
        aporte = float(diferencia_coeficientes[posicion] * escaladas[posicion])
        filas.append({"Variable": nombre_de_variable(variable),
                      "Local": valor_de_equipo(prediccion["perfil_local"], variable, "local"),
                      "Visitante": valor_de_equipo(prediccion["perfil_visitante"], variable, "visitante"),
                      "Aporte": round(aporte, 3),
                      "Favorece a": favorecido(aporte, prediccion)})
    tabla = pd.DataFrame(filas)
    orden = tabla["Aporte"].abs().sort_values(ascending=False).index
    return tabla.loc[orden].reset_index(drop=True)


def favorecido(aporte, prediccion):
    if abs(aporte) < 0.02:
        return "Casi no influye"
    return prediccion["local"] if aporte > 0 else prediccion["visitante"]


def nombre_de_variable(variable):
    """Nombre legible de una variable del modelo."""
    if variable.startswith("dif_"):
        return NOMBRES_VARIABLES[variable[4:]]
    return {
        "local_puntos_en_casa": "Puntos por partido del local en casa (últimos 10)",
        "visitante_puntos_fuera": "Puntos por partido del visitante fuera (últimos 10)",
        "local_sin_historial": "El local no tiene historial reciente (1 = sí)",
        "visitante_sin_historial": "El visitante no tiene historial reciente (1 = sí)",
    }[variable]


def valor_de_equipo(perfil, variable, lado):
    """Valor de un equipo en la variable (None si la variable es del otro equipo o no hay dato)."""
    if variable.startswith("dif_"):
        valor = perfil[variable[4:]]
    elif variable.startswith(lado):
        valor = perfil["sin_historial"] if variable.endswith("sin_historial") else perfil["condicion_puntos"]
    else:
        return None
    return None if pd.isna(valor) else round(float(valor), 2)


def ventaja_local_del_modelo(modelo):
    """True si, con todas las variables en su valor medio, el modelo da más opciones al local."""
    regresion = modelo.named_steps["regresion"]
    clases = list(regresion.classes_)
    return bool(regresion.intercept_[clases.index("H")] > regresion.intercept_[clases.index("A")])


def coeficientes(modelo):
    """Coeficientes del modelo: una fila por variable y una columna por resultado."""
    regresion = modelo.named_steps["regresion"]
    tabla = pd.DataFrame(regresion.coef_.T, columns=[NOMBRES_CLASES[c] for c in regresion.classes_])
    tabla.insert(0, "Variable", [nombre_de_variable(v) for v in VARIABLES_MODELO])
    return tabla[["Variable"] + [NOMBRES_CLASES[c] for c in CLASES]].round(3)


# Para que los nombres estén disponibles desde un solo módulo.
__all__ = ["CLASES", "NOMBRES_CLASES", "NOMBRE_MODELO", "VARIABLES_EQUIPO", "VARIABLES_MODELO", "crear_pipeline",
           "entrenar", "probabilidades", "predecir_partido", "explicar_prediccion", "coeficientes",
           "filas_para_entrenar", "version_del_modelo", "ventaja_local_del_modelo"]
