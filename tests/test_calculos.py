"""Pruebas de los cálculos con datos de ejemplo controlados.

Ejecutar desde la carpeta raíz del proyecto:
    python -m pytest tests
"""

import numpy as np
import pandas as pd
import pytest

from src.analisis import correlacion, estadisticas_descriptivas, fuerza
from src.estadisticas import (
    agregar_numero_partido,
    calcular_clasificacion,
    empates_sin_resolver,
    estadisticas_por_condicion,
    partidos_a_equipo_partido,
    puntos_y_resultado,
)
from src.limpieza import (
    COLUMNAS_ESPERADAS,
    buscar_tiros_imposibles,
    limpiar_temporada,
    resultado_esperado,
    temporada_es_valida,
    validar_temporada,
)


def partidos_de_ejemplo():
    """Tres partidos con resultado conocido: victoria local, empate y victoria visitante."""
    return pd.DataFrame({
        "PartidoID": [0, 1, 2],
        "Temporada": ["2099/00"] * 3,
        "Date": pd.to_datetime(["2099-08-10", "2099-08-17", "2099-08-24"]),
        "HomeTeam": ["A", "B", "C"], "AwayTeam": ["B", "C", "A"],
        "FTHG": [2, 1, 0], "FTAG": [0, 1, 3], "FTR": ["H", "D", "A"],
        "HS": [10, 8, 5], "AS": [4, 9, 12], "HST": [5, 3, 1], "AST": [1, 3, 6],
        "HC": [6, 2, 3], "AC": [1, 5, 7], "HF": [9, 11, 10], "AF": [12, 10, 8],
        "HY": [1, 2, 0], "AY": [3, 1, 2], "HR": [0, 0, 1], "AR": [1, 0, 0],
    })


# --- Limpieza --------------------------------------------------------------

def test_resultado_esperado():
    assert resultado_esperado(2, 1) == "H"
    assert resultado_esperado(0, 3) == "A"
    assert resultado_esperado(1, 1) == "D"


def test_detecta_y_vacia_tiros_imposibles():
    df = partidos_de_ejemplo()
    df.insert(0, "Referee", "X")
    df = df.drop(columns="PartidoID")
    df.loc[1, ["AS", "AST"]] = [8, 9]  # imposible: 9 al arco con 8 tiros

    casos = buscar_tiros_imposibles(df)
    assert len(casos) == 1 and casos[0]["equipo"] == "C"

    limpio, cambios = limpiar_temporada(df)
    assert "Referee" not in limpio.columns
    assert np.isnan(limpio.loc[1, "AS"]) and np.isnan(limpio.loc[1, "AST"])
    assert limpio.loc[1, "HS"] == 8                      # el local no cambia
    assert limpio.loc[1, ["FTHG", "FTAG"]].tolist() == [1, 1]  # el marcador no cambia
    assert int(limpio.isna().sum().sum()) == 2
    assert cambios[0]["columnas_vaciadas"] == ["AS", "AST"]


def test_temporada_incompleta_no_es_valida():
    df = partidos_de_ejemplo().drop(columns=["PartidoID", "Temporada"])
    df["HTHG"], df["HTAG"], df["HTR"], df["Referee"] = 0, 0, "D", "X"
    df = df[COLUMNAS_ESPERADAS]
    df.insert(0, "Temporada", "2099/00")

    validacion = validar_temporada(df, "2099/00")
    assert validacion["columnas_correctas"] and validacion["resultados_incoherentes"] == 0
    assert validacion["filas"] == 3  # una temporada real tiene 380
    assert temporada_es_valida(validacion) is False


# --- Puntos, goles y agregación ---------------------------------------------

def test_puntos_y_resultado():
    assert puntos_y_resultado(2, 0) == (3, "V")
    assert puntos_y_resultado(1, 1) == (1, "E")
    assert puntos_y_resultado(0, 3) == (0, "D")


def test_equipo_partido_con_datos_controlados():
    registros = partidos_a_equipo_partido(partidos_de_ejemplo())
    assert len(registros) == 6

    # Puntos por partido: 3 con ganador y 2 (1 + 1) con empate.
    assert registros.groupby("PartidoID")["Puntos"].sum().tolist() == [3, 2, 3]

    # Los goles a favor de uno son los goles en contra del otro.
    local = registros[registros["Condicion"] == "Local"].set_index("PartidoID")
    visitante = registros[registros["Condicion"] == "Visitante"].set_index("PartidoID")
    assert (local["GolesFavor"] == visitante["GolesContra"]).all()

    # A ganó 3-0 como visitante: los datos salen de las columnas del visitante.
    fila = registros[(registros["Equipo"] == "A") & (registros["Condicion"] == "Visitante")].iloc[0]
    assert [fila["GolesFavor"], fila["Tiros"], fila["TirosArco"], fila["Puntos"]] == [3, 12, 6, 3]


def test_local_mas_visitante_igual_total():
    registros = agregar_numero_partido(partidos_a_equipo_partido(partidos_de_ejemplo()))
    tabla = estadisticas_por_condicion(registros).set_index(["Equipo", "Condicion"])
    for equipo in ["A", "B", "C"]:
        total = tabla.loc[(equipo, "Total")]
        partes = [tabla.loc[(equipo, c)] for c in ["Local", "Visitante"]]
        for columna in ["PJ", "Puntos", "GolesFavor", "GolesContra", "Tiros"]:
            assert sum(p[columna] for p in partes) == total[columna]
    assert tabla.loc[("A", "Total"), "Puntos"] == 6
    assert tabla.loc[("A", "Total"), "DG"] == 5


def test_numero_partido_y_puntos_acumulados():
    registros = agregar_numero_partido(partidos_a_equipo_partido(partidos_de_ejemplo()))
    a = registros[registros["Equipo"] == "A"]
    assert a["NumeroPartido"].tolist() == [1, 2]
    assert a["PuntosAcumulados"].tolist() == [3, 6]


def test_numero_partido_rechaza_dos_partidos_el_mismo_dia():
    registros = partidos_a_equipo_partido(partidos_de_ejemplo())
    registros.loc[:, "Fecha"] = pd.Timestamp("2099-08-10")
    with pytest.raises(ValueError):
        agregar_numero_partido(registros)


# --- Clasificación ---------------------------------------------------------

def test_clasificacion_usa_los_criterios_en_orden():
    tabla = pd.DataFrame({
        "Temporada": ["T"] * 4,
        "Equipo": ["Menos puntos", "Peor DG", "Menos goles", "Primero"],
        "Puntos": [50, 60, 60, 60],
        "DG": [30, 5, 10, 10],
        "GolesFavor": [80, 70, 40, 50],
    })
    orden = calcular_clasificacion(tabla)["Equipo"].tolist()
    assert orden == ["Primero", "Menos goles", "Peor DG", "Menos puntos"]
    assert empates_sin_resolver(calcular_clasificacion(tabla)).empty


def test_detecta_empates_sin_resolver():
    tabla = pd.DataFrame({
        "Temporada": ["T"] * 3, "Equipo": ["X", "Y", "Z"],
        "Puntos": [40, 40, 30], "DG": [0, 0, 1], "GolesFavor": [45, 45, 50],
    })
    assert sorted(empates_sin_resolver(calcular_clasificacion(tabla))["Equipo"]) == ["X", "Y"]


# --- Análisis ----------------------------------------------------------------

def test_correlacion_casos_conocidos():
    assert correlacion([1, 2, 3, 4], [2, 4, 6, 8]) == pytest.approx(1.0)
    assert correlacion([1, 2, 3, 4], [8, 6, 4, 2]) == pytest.approx(-1.0)
    with pytest.raises(ValueError):
        correlacion([1, 2, np.nan], [1, 2, 3])
    with pytest.raises(ValueError):
        correlacion([1, 2, 3], [1, 2])


def test_descriptivas_coinciden_con_pandas():
    valores = pd.Series([3.0, 1.0, 4.0, 1.0, 5.0, 9.0])
    resultado = estadisticas_descriptivas(valores)
    assert resultado["Media"] == pytest.approx(valores.mean())
    assert resultado["Mediana"] == pytest.approx(valores.median())
    assert resultado["Desv. estándar"] == pytest.approx(valores.std())
    assert (resultado["Mínimo"], resultado["Máximo"]) == (1.0, 9.0)


def test_fuerza():
    assert fuerza(0.86) == "fuerte"
    assert fuerza(-0.37) == "moderada"
    assert fuerza(0.19) == "débil"
