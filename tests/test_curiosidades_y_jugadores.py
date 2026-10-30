"""Pruebas de las curiosidades, los datos de jugadores y las insignias de los equipos."""

import pandas as pd
import pytest

from src.curiosidades import curiosidades_temporada, elegir_curiosidad
from src.equipos import EQUIPOS, abreviatura, insignia
from src.jugadores import cargar_jugadores, lideres, ranking
from src.partidos import partidos_de_temporada
from src.preparar_datos import CARPETA_PROCESADOS

TEMPORADAS = ["2020/21", "2021/22", "2022/23", "2023/24", "2024/25"]


@pytest.fixture(scope="module")
def datos():
    partidos = pd.read_csv(CARPETA_PROCESADOS / "partidos_limpios.csv", parse_dates=["Date"])
    equipo_partido = pd.read_csv(CARPETA_PROCESADOS / "equipo_partido.csv")
    return partidos, equipo_partido


@pytest.fixture(scope="module")
def jugadores():
    return cargar_jugadores()


def test_curiosidades_de_2023_24_con_datos_reales(datos):
    partidos, equipo_partido = datos
    lista = curiosidades_temporada(partidos_de_temporada(partidos, "2023/24"),
                                   equipo_partido[equipo_partido["Temporada"] == "2023/24"])
    textos = {c["titulo"]: c["texto"] for c in lista}
    assert len(lista) == 15
    assert "Sheffield United 0-8 Newcastle" in textos["Mayor goleada"]
    assert "Arsenal y Man City" in textos["Equipo con más victorias"]   # 28 victorias cada uno


def test_sorprendeme_no_repite_hasta_mostrar_todas(datos):
    partidos, equipo_partido = datos
    lista = curiosidades_temporada(partidos_de_temporada(partidos, "2022/23"),
                                   equipo_partido[equipo_partido["Temporada"] == "2022/23"])
    vistas = []
    for _ in range(len(lista)):
        _, vistas = elegir_curiosidad(lista, vistas)
    assert len(set(vistas)) == len(lista)
    _, vistas = elegir_curiosidad(lista, vistas)       # se vieron todas: empieza de nuevo
    assert len(vistas) == 1


def test_lideres_coinciden_con_los_premios_oficiales(jugadores):
    goleadores, asistencias, _ = jugadores
    esperados = {
        "2020/21": ({"Harry Kane"}, 23, {"Harry Kane"}, 14),
        "2021/22": ({"Mohamed Salah", "Son Heung-Min"}, 23, {"Mohamed Salah"}, 13),
        "2022/23": ({"Erling Haaland"}, 36, {"Kevin De Bruyne"}, 16),
        "2023/24": ({"Erling Haaland"}, 27, {"Ollie Watkins"}, 13),
        "2024/25": ({"Mohamed Salah"}, 29, {"Mohamed Salah"}, 18),
    }
    for temporada, (gol, n_gol, asis, n_asis) in esperados.items():
        primeros = lideres(ranking(goleadores, temporada, "Goles"))
        assert set(primeros["Jugador"]) == gol and (primeros["Goles"] == n_gol).all(), temporada
        primeros = lideres(ranking(asistencias, temporada, "Asistencias"))
        assert set(primeros["Jugador"]) == asis and (primeros["Asistencias"] == n_asis).all(), temporada


def test_cada_jugador_es_de_un_equipo_que_jugo_esa_temporada(jugadores, datos):
    partidos, _ = datos
    goleadores, asistencias, fuentes = jugadores
    for tabla in [goleadores, asistencias]:
        assert tabla["EquipoCorto"].notna().all()
        for temporada, equipo in zip(tabla["Temporada"], tabla["EquipoCorto"]):
            assert equipo in set(partidos.loc[partidos["Temporada"] == temporada, "HomeTeam"]), (temporada, equipo)
    assert set(fuentes["temporadas"]) == set(TEMPORADAS)
    assert fuentes["temporadas"]["2020/21"]["completo"] is False


def test_insignias_y_abreviaturas_de_los_27_equipos(datos):
    partidos, _ = datos
    equipos = set(partidos["HomeTeam"])
    assert equipos == set(EQUIPOS)
    abreviaturas = [abreviatura(e) for e in equipos]
    assert len(set(abreviaturas)) == len(abreviaturas) == 27
    assert all(insignia(e).startswith("data:image/svg+xml;base64,") for e in equipos)
