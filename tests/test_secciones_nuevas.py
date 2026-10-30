"""Pruebas de las seis secciones nuevas con los datos reales.

Comprueban que los cálculos coinciden con los partidos (sin contar nada dos veces),
que local + visitante = total y que los rankings, récords y sorpresas son correctos.
"""

import numpy as np
import pandas as pd
import pytest

from src import comparador, correlaciones, ranking, records, sorpresas
from src.partidos import partidos_de_temporada
from src.preparar_datos import CARPETA_PROCESADOS

TEMPORADAS = ["2020/21", "2021/22", "2022/23", "2023/24", "2024/25"]


@pytest.fixture(scope="module")
def datos():
    estadisticas = pd.read_csv(CARPETA_PROCESADOS / "estadisticas_equipo_temporada.csv")
    partidos = pd.read_csv(CARPETA_PROCESADOS / "partidos_limpios.csv", parse_dates=["Date"])
    return estadisticas, partidos


# --- Comparador y local vs. visitante -----------------------------------------
def test_comparador_coincide_con_los_partidos(datos):
    estadisticas, partidos = datos
    tabla = comparador.tabla_comparacion(estadisticas, "2024/25", "Liverpool", "Arsenal").set_index("Estadística")
    temporada = partidos_de_temporada(partidos, "2024/25")
    de_liverpool = temporada[(temporada["HomeTeam"] == "Liverpool") | (temporada["AwayTeam"] == "Liverpool")]
    goles = sum(f["FTHG"] if f["HomeTeam"] == "Liverpool" else f["FTAG"] for _, f in de_liverpool.iterrows())
    assert len(de_liverpool) == 38
    assert tabla.loc["Goles anotados", "Liverpool"] == goles == 86
    assert tabla.loc["Puntos", "Liverpool"] == 84 and tabla.loc["Puntos", "Arsenal"] == 74
    assert tabla.loc["Partidos perdidos", "Más alto"] == "Igual"          # 4 derrotas cada uno


def test_reparto_suma_100_por_estadistica(datos):
    estadisticas, _ = datos
    tabla = comparador.tabla_comparacion(estadisticas, "2023/24", "Man City", "Arsenal")
    reparto = comparador.reparto_por_estadistica(tabla, "Man City", "Arsenal")
    sumas = reparto.groupby("Estadística")["Porcentaje"].sum()
    assert np.allclose(sumas, 100)


@pytest.mark.parametrize("temporada", TEMPORADAS)
def test_local_mas_visitante_es_el_total(datos, temporada):
    estadisticas, _ = datos
    for equipo in estadisticas.loc[estadisticas["Temporada"] == temporada, "Equipo"].unique():
        total = comparador.fila_equipo(estadisticas, temporada, equipo, "Total")
        tabla = comparador.tabla_local_visitante(estadisticas, temporada, equipo).set_index("Estadística")
        for nombre, columna in comparador.ESTADISTICAS_EQUIPO.items():
            if not columna.endswith("PorPartido"):
                assert tabla.loc[nombre, "Local"] + tabla.loc[nombre, "Visitante"] == total[columna], (equipo, nombre)


def test_conclusiones_siguen_a_los_datos(datos):
    estadisticas, _ = datos
    frases = comparador.conclusiones_local_visitante(estadisticas, "2020/21", "Man City")
    assert "más puntos como visitante (45) que como local (41)" in frases[0]
    assert "más fuera que en casa" in frases[4]          # en 2020/21 la liga sumó más fuera
    frases = comparador.conclusiones_local_visitante(estadisticas, "2024/25", "Liverpool")
    assert "más puntos como local (46) que como visitante (38)" in frases[0]


# --- Correlaciones ------------------------------------------------------------
def test_matriz_igual_a_pandas_y_simetrica(datos):
    estadisticas, _ = datos
    tabla = correlaciones.preparar_tabla(estadisticas)
    nombres = list(correlaciones.VARIABLES)
    matriz = correlaciones.matriz_correlacion(tabla, nombres)
    columnas = [correlaciones.VARIABLES[n] for n in nombres]
    assert np.allclose(matriz.values, tabla[columnas].corr().values)
    assert np.allclose(matriz.values, matriz.values.T)
    assert round(matriz.loc["Tiros al arco", "Puntos"], 2) == 0.86


def test_explicacion_no_habla_de_causas_como_hecho(datos):
    texto = correlaciones.explicar(0.86, "Tiros al arco", "Puntos", 100)
    assert "no demuestra que una cosa cause la otra" in texto and "fuerte" in texto
    assert "tienden a tener menos" in correlaciones.explicar(-0.37, "Faltas", "Puntos", 100)


# --- Récords ------------------------------------------------------------------
def test_records_de_una_temporada_y_acumulados(datos):
    estadisticas, _ = datos
    puntos = records.ranking_una_temporada(estadisticas, "Puntos", False)
    assert len(puntos) == 100
    assert tuple(puntos.loc[0, ["Temporada", "Equipo", "Puntos"]]) == ("2021/22", "Man City", 93)
    recibidos = records.ranking_una_temporada(estadisticas, "GolesContra", True)
    assert set(recibidos.loc[recibidos["Pos"] == 1, "Equipo"]) == {"Liverpool", "Man City"}   # 26 en 2021/22
    acumulado = records.ranking_acumulado(estadisticas, "GolesContra", True)
    assert (acumulado["Temporadas"] == 5).all()


def test_records_de_partidos(datos):
    _, partidos = datos
    lista = {r["titulo"]: r for r in records.records_de_partidos(partidos)}
    assert lista["Mayor diferencia de goles"]["valor"] == "9 goles"
    assert "Man United 9-0 Southampton" in lista["Mayor diferencia de goles"]["texto"]
    assert "Liverpool 9-0 Bournemouth" in lista["Más goles de un equipo en un partido"]["texto"]
    assert lista["Resultado más repetido"]["valor"] == "1-0"


# --- Ranking personalizado ----------------------------------------------------
def test_ranking_menos_goles_recibidos_ordena_de_menor_a_mayor(datos):
    estadisticas, _ = datos
    orden = ranking.orden_recomendado("Menos goles recibidos")
    assert orden == ranking.ORDEN_ASCENDENTE
    tabla = ranking.ranking_personalizado(estadisticas, "2024/25", "Menos goles recibidos", orden)
    assert tabla["Valor"].is_monotonic_increasing and tabla.loc[0, "Equipo"] == "Arsenal"


@pytest.mark.parametrize("opcion", list(ranking.OPCIONES_RANKING))
def test_cada_opcion_de_ranking_tiene_20_equipos_ordenados(datos, opcion):
    estadisticas, _ = datos
    for orden in [ranking.ORDEN_DESCENDENTE, ranking.ORDEN_ASCENDENTE]:
        tabla = ranking.ranking_personalizado(estadisticas, "2022/23", opcion, orden)
        assert len(tabla) == 20 and tabla["Pos"].iloc[0] == 1
        creciente = tabla["Valor"].is_monotonic_increasing
        assert creciente if orden == ranking.ORDEN_ASCENDENTE else tabla["Valor"].is_monotonic_decreasing


# --- Detector de sorpresas ----------------------------------------------------
@pytest.mark.parametrize("temporada", TEMPORADAS)
def test_sorpresas_cumplen_su_criterio(datos, temporada):
    _, partidos = datos
    temporada_partidos = partidos_de_temporada(partidos, temporada)
    tabla, _ = sorpresas.buscar_sorpresas(temporada_partidos, "Perdió con más tiros")
    validos = temporada_partidos.dropna(subset=["HS", "AS"])
    esperado = ((validos["HS"] > validos["AS"]) & (validos["FTHG"] < validos["FTAG"])).sum() + \
               ((validos["AS"] > validos["HS"]) & (validos["FTAG"] < validos["FTHG"])).sum()
    assert len(tabla) == esperado
    assert tabla["Diferencia"].is_monotonic_decreasing
    for _, fila in tabla.iterrows():
        tiros_local, tiros_visitante = [int(x) for x in fila["Tiros"].split(" - ")]
        goles_local, goles_visitante = [int(x) for x in fila["Resultado"].split(" - ")]
        assert (tiros_local - tiros_visitante) * (goles_local - goles_visitante) < 0


def test_sorpresas_excluye_el_partido_sin_tiros(datos):
    _, partidos = datos
    tabla, sin_datos = sorpresas.buscar_sorpresas(partidos_de_temporada(partidos, "2021/22"),
                                                  "Perdió con más tiros al arco", "West Ham")
    assert sin_datos == 1
    assert not (tabla["Fecha"] == "15/08/2021").any()
