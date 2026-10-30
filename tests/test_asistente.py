"""Pruebas del asistente: reconoce equipos y preguntas y responde con los datos reales."""

import pandas as pd
import pytest

from src.asistente import encontrar_equipos, responder
from src.equipos import normalizar
from src.partidos import partidos_de_temporada
from src.preparar_datos import CARPETA_PROCESADOS


@pytest.fixture(scope="module")
def temporada_2324():
    partidos = pd.read_csv(CARPETA_PROCESADOS / "partidos_limpios.csv", parse_dates=["Date"])
    return partidos_de_temporada(partidos, "2023/24")


def preguntar(texto, partidos):
    return responder(texto, partidos, "2023/24")


def test_reconoce_alias_y_no_confunde_nombres_parecidos():
    assert encontrar_equipos(normalizar("man city contra los spurs")) == ["Man City", "Tottenham"]
    assert encontrar_equipos(normalizar("Leicester City")) == ["Leicester"]
    assert encontrar_equipos(normalizar("Newcastle United vs Manchester United")) == ["Newcastle", "Man United"]
    assert encontrar_equipos(normalizar("Nottingham Forest")) == ["Nott'm Forest"]


def test_reconoce_equipos_con_errores_de_escritura():
    assert encontrar_equipos(normalizar("liverpol")) == ["Liverpool"]


def test_resultado_de_un_enfrentamiento(temporada_2324):
    r = preguntar("¿Cuánto quedó el Man City contra Liverpool?", temporada_2324)
    assert r["tipo"] == "partidos"
    assert "Man City 1-1 Liverpool" in r["texto"] and "Liverpool 1-1 Man City" in r["texto"]
    assert len(r["tabla"]) == 2


def test_victorias_de_un_equipo(temporada_2324):
    r = preguntar("¿Cuántos partidos ganó el Chelsea?", temporada_2324)
    assert "ganó **18**" in r["texto"] and "**63 puntos**" in r["texto"]


def test_campeon_y_mayor_goleada(temporada_2324):
    assert "**Man City**, con 91 puntos" in preguntar("¿Quién fue el campeón?", temporada_2324)["texto"]
    assert "Sheffield United 0-8 Newcastle" in preguntar("mayor goleada", temporada_2324)["texto"]


def test_partido_con_mas_goles_incluye_todos_los_empatados(temporada_2324):
    texto = preguntar("¿Cuál fue el partido con más goles?", temporada_2324)["texto"]
    for partido in ["Sheffield United 0-8 Newcastle", "Chelsea 4-4 Man City", "Newcastle 4-4 Luton"]:
        assert partido in texto


def test_estadistica_en_un_enfrentamiento(temporada_2324):
    texto = preguntar("¿Cuántos tiros al arco tuvo el Arsenal contra el Tottenham?", temporada_2324)["texto"]
    assert "tiros al arco" in texto and "Arsenal 2-2 Tottenham" in texto


def test_equipo_que_no_jugo_la_temporada(temporada_2324):
    r = preguntar("goles del Leicester", temporada_2324)
    assert r["tipo"] == "sin_datos" and "no jugó" in r["texto"]


def test_pide_aclaracion_si_solo_dice_manchester(temporada_2324):
    assert preguntar("partidos del manchester", temporada_2324)["tipo"] == "aclaracion"


def test_pregunta_que_no_entiende_devuelve_ayuda(temporada_2324):
    assert preguntar("hola", temporada_2324)["tipo"] == "ayuda"
    assert preguntar("   ", temporada_2324)["tipo"] == "ayuda"
