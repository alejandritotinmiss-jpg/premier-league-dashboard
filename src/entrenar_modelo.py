"""Entrena y evalúa el modelo predictivo y guarda los resultados en data/modelo/.

Uso: python -m src.entrenar_modelo

Reparto cronológico de los partidos (nunca al azar):
    entrenamiento  temporadas más antiguas
    validación     la temporada siguiente: sirve para elegir C
    prueba         las temporadas más recientes: se usan una sola vez, para medir el modelo
"""

import json
from pathlib import Path

import pandas as pd

from src import calendario as cal
from src.evaluacion import backtesting, evaluar, tabla_calibracion
from src.modelo import (CLASES, NOMBRE_MODELO, entrenar, filas_para_entrenar, predecir_partido,
                        version_del_modelo)
from src.preparar_datos import CARPETA_PROCESADOS, RAIZ_PROYECTO
from src.variables_modelo import (ANTIGUEDAD_MAXIMA_DIAS, MINIMO_PARTIDOS, VARIABLES_MODELO, VENTANA_CONDICION,
                                  VENTANA_FORMA, VENTANA_NIVEL, construir_historial, tabla_del_modelo)

CARPETA_MODELO = RAIZ_PROYECTO / "data" / "modelo"
VALORES_C = [0.01, 0.1, 1.0, 10.0]     # candidatos para la regularización
C_POR_DEFECTO = 0.1
TEMPORADAS_ENTRENAMIENTO_INICIAL = 3   # temporadas del primer entrenamiento
TEMPORADAS_MINIMAS_BACKTESTING = 2     # el backtesting empieza cuando hay 2 temporadas para entrenar


def leer_partidos(carpeta=CARPETA_PROCESADOS):
    return pd.read_csv(Path(carpeta) / "partidos_limpios.csv", parse_dates=["Date"])


def repartir_temporadas(tabla):
    """Reparte las temporadas en entrenamiento, validación y prueba, en orden de tiempo."""
    temporadas = sorted(tabla["Temporada"].unique())
    if len(temporadas) < TEMPORADAS_ENTRENAMIENTO_INICIAL + 2:
        raise ValueError("Se necesitan al menos cinco temporadas con variables para evaluar el modelo.")
    return {
        "entrenamiento": temporadas[:TEMPORADAS_ENTRENAMIENTO_INICIAL],
        "validacion": [temporadas[TEMPORADAS_ENTRENAMIENTO_INICIAL]],
        "prueba": temporadas[TEMPORADAS_ENTRENAMIENTO_INICIAL + 1:],
    }


def elegir_c(entrenamiento, validacion):
    """Prueba varios valores de C y se queda con el de menor log loss en la validación."""
    resultados = {}
    for c in VALORES_C:
        resultado, _ = evaluar(entrenamiento, validacion, c)
        resultados[c] = resultado["modelo"]["log_loss"]
    mejor = min(resultados, key=resultados.get)
    return mejor, resultados


def evaluar_modelo(tabla):
    """Evaluación completa: elección de C, prueba final, backtesting y calibración."""
    reparto = repartir_temporadas(tabla)
    entrenamiento = tabla[tabla["Temporada"].isin(reparto["entrenamiento"])]
    validacion = tabla[tabla["Temporada"].isin(reparto["validacion"])]
    prueba = tabla[tabla["Temporada"].isin(reparto["prueba"])]

    c, log_loss_por_c = elegir_c(entrenamiento, validacion)
    resultado_validacion, _ = evaluar(entrenamiento, validacion, c)
    # Para la prueba final se entrena con entrenamiento + validación (todo lo anterior a la prueba).
    resultado_prueba, _ = evaluar(pd.concat([entrenamiento, validacion]), prueba, c)

    temporadas = sorted(tabla["Temporada"].unique())
    resultados_backtesting, probabilidades_backtesting = backtesting(
        tabla, temporadas[TEMPORADAS_MINIMAS_BACKTESTING:], c)
    calibracion = tabla_calibracion(probabilidades_backtesting["Resultado"], probabilidades_backtesting)

    return {
        "reparto_de_temporadas": reparto,
        "c_elegido": c,
        "log_loss_en_validacion_por_c": {str(valor): perdida for valor, perdida in log_loss_por_c.items()},
        "validacion": resultado_validacion,
        "prueba": resultado_prueba,
        "backtesting": resultados_backtesting,
        "calibracion": calibracion,
    }


def predicciones_proximas(modelo, historial, partidos, carpeta_calendario=cal.CARPETA_CALENDARIO):
    """Probabilidades de los próximos partidos pendientes de la temporada en curso."""
    temporada = sorted(partidos["Temporada"].unique())[-1]
    partidos_temporada = partidos[partidos["Temporada"] == temporada]
    calendario = cal.cargar_calendario(temporada, carpeta_calendario)
    pendientes = cal.proximos_partidos(cal.partidos_pendientes(calendario, partidos_temporada))
    filas = []
    for _, fila in pendientes.iterrows():
        prediccion = predecir_partido(modelo, historial, fila["HomeTeam"], fila["AwayTeam"], fila["Fecha"])
        filas.append({
            "Temporada": temporada, "Jornada": int(fila["Jornada"]),
            "FechaUTC": fila["FechaUTC"].strftime("%Y-%m-%d %H:%M:%SZ"),
            "HomeTeam": fila["HomeTeam"], "AwayTeam": fila["AwayTeam"],
            "P_local": round(prediccion["probabilidades"]["H"], 4),
            "P_empate": round(prediccion["probabilidades"]["D"], 4),
            "P_visitante": round(prediccion["probabilidades"]["A"], 4),
        })
    columnas = ["Temporada", "Jornada", "FechaUTC", "HomeTeam", "AwayTeam", "P_local", "P_empate", "P_visitante"]
    return pd.DataFrame(filas, columns=columnas)


def cargar_evaluacion(carpeta_modelo=CARPETA_MODELO):
    """Lee data/modelo/evaluacion.json (None si todavía no existe)."""
    ruta = Path(carpeta_modelo) / "evaluacion.json"
    if not ruta.exists():
        return None
    with open(ruta, encoding="utf-8") as archivo:
        return json.load(archivo)


def preparar_modelo(partidos, c=C_POR_DEFECTO):
    """Entrena el modelo final con todos los partidos jugados y devuelve lo necesario para predecir.

    La aplicación llama a esta función una sola vez por versión de los datos (queda en caché).
    """
    historial = construir_historial(partidos)
    tabla = filas_para_entrenar(tabla_del_modelo(partidos, historial))
    return {
        "modelo": entrenar(tabla, c), "historial": historial, "tabla": tabla, "c": c,
        "version": version_del_modelo(tabla), "fecha_datos": partidos["Date"].max(),
    }


def generar(partidos, carpeta_calendario=cal.CARPETA_CALENDARIO):
    """Devuelve (evaluación, predicciones) listos para guardar."""
    historial = construir_historial(partidos)
    tabla = filas_para_entrenar(tabla_del_modelo(partidos, historial))
    evaluacion = evaluar_modelo(tabla)

    modelo = entrenar(tabla, evaluacion["c_elegido"])       # modelo final: todos los partidos jugados
    evaluacion.update({
        "modelo": NOMBRE_MODELO,
        "version": version_del_modelo(tabla),
        "configuracion": {
            "solver": "lbfgs", "C": evaluacion["c_elegido"], "max_iter": 1000,
            "pasos": ["imputar con la mediana", "escalar (media 0, desviación 1)", "regresión logística"],
            "ventana_forma": VENTANA_FORMA, "ventana_nivel": VENTANA_NIVEL,
            "ventana_condicion": VENTANA_CONDICION, "minimo_partidos": MINIMO_PARTIDOS,
            "antiguedad_maxima_dias": ANTIGUEDAD_MAXIMA_DIAS,
        },
        "variables": VARIABLES_MODELO,
        "clases": CLASES,
        "partidos_de_entrenamiento_final": int(len(tabla)),
        "fecha_ultimo_partido": str(partidos["Date"].max().date()),
    })
    return evaluacion, predicciones_proximas(modelo, historial, partidos, carpeta_calendario)


def guardar(carpeta_procesados=CARPETA_PROCESADOS, carpeta_modelo=CARPETA_MODELO,
            carpeta_calendario=cal.CARPETA_CALENDARIO):
    """Calcula la evaluación y las predicciones y las guarda en data/modelo/."""
    evaluacion, predicciones = generar(leer_partidos(carpeta_procesados), carpeta_calendario)
    carpeta_modelo = Path(carpeta_modelo)
    carpeta_modelo.mkdir(parents=True, exist_ok=True)
    with open(carpeta_modelo / "evaluacion.json", "w", encoding="utf-8", newline="\n") as archivo:
        json.dump(evaluacion, archivo, ensure_ascii=False, indent=2)
    predicciones.to_csv(carpeta_modelo / "predicciones.csv", index=False, lineterminator="\n")
    return evaluacion, predicciones


def main():
    evaluacion, predicciones = guardar()
    prueba = evaluacion["prueba"]
    print(f"Modelo: {evaluacion['version']} (C = {evaluacion['c_elegido']})")
    print(f"Prueba ({prueba['prueba']['partidos']} partidos, {prueba['prueba']['desde']} a {prueba['prueba']['hasta']}):")
    for nombre in ["modelo", "baseline"]:
        m = prueba[nombre]
        print(f"  {nombre:9s} accuracy {m['accuracy']:.3f} · balanced accuracy {m['balanced_accuracy']:.3f} · "
              f"log loss {m['log_loss']:.4f} · Brier {m['brier']:.4f}")
    print(f"Predicciones guardadas: {len(predicciones)} partidos pendientes")


if __name__ == "__main__":
    main()
