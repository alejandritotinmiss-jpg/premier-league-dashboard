"""Pruebas del modelo predictivo: variables sin fuga de datos, probabilidades y evaluación cronológica."""

import math

import numpy as np
import pandas as pd
import pytest

from src import calendario as cal
from src import entrenar_modelo
from src.evaluacion import (backtesting, brier_multiclase, calcular_metricas, evaluar, log_loss_ordenado,
                            probabilidades_baseline, tabla_calibracion)
from src.modelo import (CLASES, entrenar, explicar_prediccion, filas_para_entrenar, predecir_partido,
                        probabilidades, version_del_modelo)
from src.preparar_datos import CARPETA_PROCESADOS
from src.variables_modelo import (MINIMO_PARTIDOS, VARIABLES_MODELO, construir_historial, partidos_anteriores,
                                  perfil_equipo, tabla_del_modelo, variables_del_partido)

FECHA_DE_CORTE = pd.Timestamp("2025-01-01")


@pytest.fixture(scope="module")
def partidos():
    return pd.read_csv(CARPETA_PROCESADOS / "partidos_limpios.csv", parse_dates=["Date"])


@pytest.fixture(scope="module")
def tabla(partidos):
    return filas_para_entrenar(tabla_del_modelo(partidos))


@pytest.fixture(scope="module")
def servicio(partidos):
    return entrenar_modelo.preparar_modelo(partidos)


def alterar_desde(partidos, fecha):
    """Copia de los partidos con TODOS los resultados y estadísticas cambiados desde una fecha."""
    alterados = partidos.copy()
    futuro = alterados["Date"] >= fecha
    alterados.loc[futuro, ["FTHG", "FTAG"]] = alterados.loc[futuro, ["FTAG", "FTHG"]].to_numpy() + [[3, 0]]
    alterados.loc[futuro, "FTR"] = "H"
    for columna in ["HS", "AS", "HST", "AST", "HC", "AC", "HF", "AF", "HY", "AY", "HR", "AR"]:
        alterados.loc[futuro, columna] = alterados.loc[futuro, columna] + 7
    return alterados


# --- Variables y fuga de datos -------------------------------------------------
def test_las_variables_solo_usan_partidos_de_fechas_anteriores(partidos):
    historial = construir_historial(partidos)
    for _, fila in partidos.sample(60, random_state=1).iterrows():
        for equipo in [fila["HomeTeam"], fila["AwayTeam"]]:
            anteriores = partidos_anteriores(historial, equipo, fila["Date"], 38)
            assert all(registro["fecha"] < fila["Date"] for registro in anteriores)


def test_los_partidos_del_mismo_dia_no_se_usan(partidos):
    historial = construir_historial(partidos)
    fila = partidos[partidos["Temporada"] == "2024/25"].iloc[200]
    equipo, dia = fila["HomeTeam"], fila["Date"]
    # El día del partido, ese partido todavía no cuenta; al día siguiente sí.
    fechas_antes = [r["fecha"] for r in partidos_anteriores(historial, equipo, dia, 38)]
    fechas_despues = [r["fecha"] for r in partidos_anteriores(historial, equipo, dia + pd.Timedelta(days=1), 38)]
    assert dia not in fechas_antes and max(fechas_antes) < dia
    assert fechas_despues[-1] == dia
    antes = perfil_equipo(historial, equipo, dia, "Local")
    despues = perfil_equipo(historial, equipo, dia + pd.Timedelta(days=1), "Local")
    assert antes["ultimos_resultados"] != despues["ultimos_resultados"] or antes["nivel_tiros"] != despues["nivel_tiros"]


def test_cambiar_resultados_futuros_no_altera_las_variables_pasadas(partidos):
    original = tabla_del_modelo(partidos)
    alterada = tabla_del_modelo(alterar_desde(partidos, FECHA_DE_CORTE))
    # Todos los partidos hasta la fecha de corte (incluida) conservan exactamente sus variables.
    pasado = original["Date"] <= FECHA_DE_CORTE
    assert pasado.sum() > 1500 and (~pasado).sum() > 500
    pd.testing.assert_frame_equal(original.loc[pasado, VARIABLES_MODELO], alterada.loc[pasado, VARIABLES_MODELO])
    # Y sí cambian las de partidos posteriores (la prueba detecta diferencias cuando las hay).
    assert not original.loc[~pasado, VARIABLES_MODELO].equals(alterada.loc[~pasado, VARIABLES_MODELO])


def test_cambiar_resultados_futuros_no_altera_una_prediccion_pasada(partidos):
    alterados = alterar_desde(partidos, FECHA_DE_CORTE)
    resultados = []
    for datos in [partidos, alterados]:
        historial = construir_historial(datos)
        tabla_previa = filas_para_entrenar(tabla_del_modelo(datos[datos["Date"] < FECHA_DE_CORTE], historial))
        modelo = entrenar(tabla_previa, 0.1)
        prediccion = predecir_partido(modelo, historial, "Arsenal", "Liverpool", FECHA_DE_CORTE)
        resultados.append(prediccion["probabilidades"])
    assert resultados[0] == resultados[1]


def test_el_resultado_del_propio_partido_no_entra_en_sus_variables(partidos):
    historial = construir_historial(partidos)
    fila = partidos[partidos["Temporada"] == "2025/26"].iloc[150]
    antes, _, _ = variables_del_partido(historial, fila["HomeTeam"], fila["AwayTeam"], fila["Date"])
    cambiado = partidos.copy()
    indice = fila.name
    cambiado.loc[indice, ["FTHG", "FTAG", "FTR", "HS", "HST"]] = [9, 0, "H", 40, 30]
    despues, _, _ = variables_del_partido(construir_historial(cambiado), fila["HomeTeam"], fila["AwayTeam"], fila["Date"])
    assert {k: v for k, v in antes.items()} == {k: v for k, v in despues.items()}


def test_equipo_sin_historial_queda_marcado(partidos):
    historial = construir_historial(partidos)
    primer_partido = partidos[partidos["Temporada"] == "2025/26"]
    primer_sunderland = primer_partido[primer_partido["HomeTeam"] == "Sunderland"].iloc[0]   # recién ascendido
    perfil = perfil_equipo(historial, "Sunderland", primer_sunderland["Date"], "Local")
    assert perfil["sin_historial"] == 1 and perfil["partidos_previos"] < MINIMO_PARTIDOS
    assert math.isnan(perfil["nivel_puntos"])


# --- Modelo ---------------------------------------------------------------------
def test_probabilidades_validas_y_suman_uno(tabla, servicio):
    tabla_probabilidades = probabilidades(servicio["modelo"], tabla)
    assert list(tabla_probabilidades.columns) == CLASES
    assert ((tabla_probabilidades >= 0) & (tabla_probabilidades <= 1)).all().all()
    assert np.allclose(tabla_probabilidades.sum(axis=1), 1.0)
    # Son exactamente las de predict_proba, reordenadas a H, D, A.
    directas = servicio["modelo"].predict_proba(tabla[VARIABLES_MODELO])
    orden = [list(servicio["modelo"].classes_).index(clase) for clase in CLASES]
    assert np.allclose(tabla_probabilidades.to_numpy(), directas[:, orden])


def test_entrenamiento_reproducible(tabla):
    primero = probabilidades(entrenar(tabla, 0.1), tabla.head(50))
    segundo = probabilidades(entrenar(tabla, 0.1), tabla.head(50))
    assert np.array_equal(primero.to_numpy(), segundo.to_numpy())


def test_datos_insuficientes(tabla, servicio):
    with pytest.raises(ValueError):
        entrenar(tabla.head(50), 0.1)                    # muy pocos partidos
    with pytest.raises(ValueError):
        predecir_partido(servicio["modelo"], servicio["historial"], "Arsenal", "Arsenal", "2026-12-01")
    # Un equipo que no está en los datos: se avisa, pero las probabilidades siguen siendo válidas.
    prediccion = predecir_partido(servicio["modelo"], servicio["historial"], "Equipo Nuevo", "Arsenal", "2026-12-01")
    assert prediccion["datos_insuficientes"] is True
    assert sum(prediccion["probabilidades"].values()) == pytest.approx(1.0)


def test_explicacion_tiene_todas_las_variables(servicio, partidos):
    fecha = partidos["Date"].max() + pd.Timedelta(days=1)
    prediccion = predecir_partido(servicio["modelo"], servicio["historial"], "Arsenal", "Chelsea", fecha)
    explicacion = explicar_prediccion(servicio["modelo"], prediccion)
    assert len(explicacion) == len(VARIABLES_MODELO)
    assert set(explicacion["Favorece a"]) <= {"Arsenal", "Chelsea", "Casi no influye"}
    assert explicacion["Aporte"].abs().is_monotonic_decreasing


# --- Evaluación -----------------------------------------------------------------
def test_metricas_con_un_ejemplo_calculado_a_mano():
    reales = ["H", "D", "A", "H"]
    perfectas = pd.DataFrame({"H": [1.0, 0, 0, 1], "D": [0, 1.0, 0, 0], "A": [0, 0, 1.0, 0]})
    uniformes = pd.DataFrame({"H": [1 / 3] * 4, "D": [1 / 3] * 4, "A": [1 / 3] * 4})
    assert brier_multiclase(reales, perfectas) == pytest.approx(0.0)
    assert brier_multiclase(reales, uniformes) == pytest.approx(2 / 3)
    assert log_loss_ordenado(reales, uniformes) == pytest.approx(math.log(3))
    metricas = calcular_metricas(reales, perfectas)
    assert metricas["accuracy"] == 1.0 and metricas["balanced_accuracy"] == 1.0
    assert metricas["matriz_confusion"] == [[2, 0, 0], [0, 1, 0], [0, 0, 1]]
    # Si siempre se predice H: acierta 2 de 4 y la balanced accuracy es 1/3.
    siempre_local = pd.DataFrame({"H": [0.5] * 4, "D": [0.3] * 4, "A": [0.2] * 4})
    metricas = calcular_metricas(reales, siempre_local)
    assert metricas["accuracy"] == 0.5 and metricas["balanced_accuracy"] == pytest.approx(1 / 3)
    assert metricas["por_clase"]["Empate"]["veces_predicho"] == 0


def test_la_evaluacion_exige_orden_cronologico(tabla):
    antiguos = tabla[tabla["Temporada"] == "2021/22"]
    recientes = tabla[tabla["Temporada"] == "2023/24"]
    with pytest.raises(ValueError):
        evaluar(recientes, antiguos, 0.1)                # entrenar con el futuro y probar con el pasado
    resultado, _ = evaluar(antiguos, recientes, 0.1)
    assert resultado["entrenamiento"]["hasta"] < resultado["prueba"]["desde"]
    assert resultado["modelo"]["partidos"] == 380


def test_backtesting_entrena_solo_con_temporadas_anteriores(tabla):
    resultados, todas = backtesting(tabla, ["2023/24", "2024/25"], 0.1)
    assert [r["temporada"] for r in resultados] == ["2023/24", "2024/25"]
    for resultado in resultados:
        assert resultado["entrenamiento"]["hasta"] < resultado["prueba"]["desde"]
    assert resultados[0]["entrenamiento"]["partidos"] == 760 and resultados[1]["entrenamiento"]["partidos"] == 1140
    assert len(todas) == 760
    calibracion = tabla_calibracion(todas["Resultado"], todas)
    assert sum(tramo["casos"] for tramo in calibracion) == 3 * 760


def test_baseline_usa_las_frecuencias_del_entrenamiento(tabla):
    entrenamiento = tabla[tabla["Temporada"] == "2021/22"]
    baseline = probabilidades_baseline(entrenamiento, 5)
    frecuencia_local = (entrenamiento["Resultado"] == "H").mean()
    assert (baseline["H"] == frecuencia_local).all() and np.allclose(baseline.sum(axis=1), 1.0)


def test_reparto_de_temporadas_en_orden(tabla):
    reparto = entrenar_modelo.repartir_temporadas(tabla)
    orden = reparto["entrenamiento"] + reparto["validacion"] + reparto["prueba"]
    assert orden == sorted(tabla["Temporada"].unique())
    assert reparto["entrenamiento"] == ["2021/22", "2022/23", "2023/24"] and reparto["validacion"] == ["2024/25"]


# --- Archivos guardados (data/modelo/) -------------------------------------------
def test_la_evaluacion_guardada_corresponde_a_los_datos_actuales(tabla, partidos):
    evaluacion = entrenar_modelo.cargar_evaluacion()
    assert evaluacion is not None
    assert evaluacion["version"] == version_del_modelo(tabla)
    assert evaluacion["fecha_ultimo_partido"] == str(partidos["Date"].max().date())
    assert evaluacion["variables"] == VARIABLES_MODELO
    prueba = evaluacion["prueba"]
    assert prueba["entrenamiento"]["hasta"] < prueba["prueba"]["desde"]
    for nombre in ["modelo", "baseline"]:
        metricas = prueba[nombre]
        assert 0 <= metricas["accuracy"] <= 1 and metricas["log_loss"] > 0 and 0 <= metricas["brier"] <= 2
        assert sum(sum(fila) for fila in metricas["matriz_confusion"]) == metricas["partidos"]
    for bloque in evaluacion["backtesting"]:
        assert bloque["entrenamiento"]["hasta"] < bloque["prueba"]["desde"]


def test_las_predicciones_guardadas_salen_del_modelo(servicio, partidos):
    guardadas = pd.read_csv(entrenar_modelo.CARPETA_MODELO / "predicciones.csv")
    assert np.allclose(guardadas[["P_local", "P_empate", "P_visitante"]].sum(axis=1), 1.0, atol=0.001)
    evaluacion = entrenar_modelo.cargar_evaluacion()
    modelo = entrenar(servicio["tabla"], evaluacion["c_elegido"])
    for _, fila in guardadas.head(10).iterrows():
        fecha = pd.Timestamp(fila["FechaUTC"]).tz_localize(None).normalize()
        prediccion = predecir_partido(modelo, servicio["historial"], fila["HomeTeam"], fila["AwayTeam"], fecha)
        assert prediccion["probabilidades"]["H"] == pytest.approx(fila["P_local"], abs=0.0001)
        assert prediccion["probabilidades"]["A"] == pytest.approx(fila["P_visitante"], abs=0.0001)
    # Ningún partido "pendiente" aparece ya entre los jugados.
    temporada = sorted(partidos["Temporada"].unique())[-1]
    jugados = set(zip(partidos.loc[partidos["Temporada"] == temporada, "HomeTeam"],
                      partidos.loc[partidos["Temporada"] == temporada, "AwayTeam"]))
    assert not any((local, visitante) in jugados for local, visitante in zip(guardadas["HomeTeam"], guardadas["AwayTeam"]))


def test_calendario_valido_e_independiente_de_los_resultados(partidos):
    temporada = sorted(partidos["Temporada"].unique())[-1]
    calendario = cal.cargar_calendario(temporada)
    jugados = partidos[partidos["Temporada"] == temporada]
    assert cal.calendario_es_valido(calendario, set(jugados["HomeTeam"]))
    pendientes = cal.partidos_pendientes(calendario, jugados)
    assert len(pendientes) == 380 - len(jugados)
    assert pendientes["FechaUTC"].is_monotonic_increasing
    assert cal.cargar_calendario("1999/00").empty          # sin archivo: tabla vacía, no un error
