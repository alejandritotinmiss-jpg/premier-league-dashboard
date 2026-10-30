"""Pruebas de los filtros del dashboard: cada filtro debe cambiar los datos que se muestran."""

import numpy as np
import pandas as pd
import pytest

from src import tablero
from src.analisis import tabla_correlaciones
from src.preparar_datos import CARPETA_PROCESADOS


@pytest.fixture(scope="module")
def datos():
    """Lee una sola vez las tablas procesadas que usan las pruebas de este archivo."""
    estadisticas = pd.read_csv(CARPETA_PROCESADOS / "estadisticas_equipo_temporada.csv")
    equipo_partido = pd.read_csv(CARPETA_PROCESADOS / "equipo_partido.csv")
    return estadisticas, equipo_partido


def test_filtro_temporada_cambia_los_equipos(datos):
    estadisticas, _ = datos
    equipos_2324 = tablero.equipos_de_temporada(estadisticas, "2023/24")
    equipos_2425 = tablero.equipos_de_temporada(estadisticas, "2024/25")
    assert len(equipos_2324) == len(equipos_2425) == 20
    assert "Luton" in equipos_2324 and "Luton" not in equipos_2425
    assert "Ipswich" in equipos_2425 and "Ipswich" not in equipos_2324


def test_equipos_por_defecto_son_los_tres_primeros(datos):
    estadisticas, _ = datos
    assert tablero.equipos_por_defecto(estadisticas, "2024/25") == ["Liverpool", "Arsenal", "Man City"]


def test_filtro_condicion_cambia_la_clasificacion(datos):
    estadisticas, _ = datos
    total = tablero.tabla_clasificacion(estadisticas, "2024/25", "Total")
    local = tablero.tabla_clasificacion(estadisticas, "2024/25", "Local")
    visitante = tablero.tabla_clasificacion(estadisticas, "2024/25", "Visitante")
    assert (total["PJ"] == 38).all() and (local["PJ"] == 19).all() and (visitante["PJ"] == 19).all()
    # Cada tabla tiene otro orden: se ordenan por equipo antes de comparar.
    puntos = lambda tabla: tabla.set_index("Equipo")["Pts"].sort_index()
    assert (puntos(local) + puntos(visitante) == puntos(total)).all()
    assert local["Equipo"].tolist() != total["Equipo"].tolist()  # el orden sí cambia


def test_sanciones_solo_en_2023_24_total(datos):
    estadisticas, _ = datos
    tabla = tablero.tabla_clasificacion(estadisticas, "2023/24", "Total").set_index("Equipo")
    assert tabla.loc["Everton", "Pts"] == 48 and tabla.loc["Everton", "Pts oficiales"] == 40
    assert tabla.loc["Nott'm Forest", "Pts oficiales"] == 32
    assert "Pts oficiales" not in tablero.tabla_clasificacion(estadisticas, "2023/24", "Local").columns
    assert "Pts oficiales" not in tablero.tabla_clasificacion(estadisticas, "2024/25", "Total").columns


def test_filtro_equipos_resalta_en_el_grafico_de_puntos(datos):
    estadisticas, _ = datos
    tabla = tablero.puntos_por_equipo(estadisticas, "2024/25", "Total", ["Everton", "Fulham"])
    assert len(tabla) == 20
    assert sorted(tabla.loc[tabla["Seleccionado"], "Equipo"]) == ["Everton", "Fulham"]


def test_evolucion_responde_a_los_equipos(datos):
    _, equipo_partido = datos
    dos = tablero.evolucion_puntos(equipo_partido, "2024/25", ["Liverpool", "Arsenal"])
    assert len(dos) == 76
    assert dos[dos["Equipo"] == "Liverpool"]["PuntosAcumulados"].iloc[-1] == 84
    assert tablero.evolucion_puntos(equipo_partido, "2024/25", []).empty  # ningún equipo elegido
    assert tablero.evolucion_puntos(equipo_partido, "2024/25", ["Luton"]).empty  # no jugó esa temporada


def test_dispersion_responde_a_temporada_condicion_y_metrica(datos):
    estadisticas, _ = datos
    todas = tablero.datos_dispersion(
        estadisticas, "2020/21", "Local", "TirosArcoPorPartido", True, ["Arsenal"])
    una = tablero.datos_dispersion(
        estadisticas, "2020/21", "Local", "TirosArcoPorPartido", False, ["Arsenal"])
    assert len(todas) == 100 and len(una) == 20
    # Solo se resalta el Arsenal de la temporada elegida, no el de otras temporadas.
    assert todas["Seleccionado"].sum() == 1
    faltas = tablero.datos_dispersion(estadisticas, "2020/21", "Local", "FaltasPorPartido", False, [])
    assert not np.allclose(una["Valor"], faltas["Valor"])


def test_correlaciones_coinciden_con_el_analisis(datos):
    estadisticas, _ = datos
    r, n = tablero.correlacion_con_puntos(estadisticas, None, "Total", "TirosArcoPorPartido", True)
    assert n == 100 and r == pytest.approx(0.858, abs=0.001)
    r_temporada, n_temporada = tablero.correlacion_con_puntos(
        estadisticas, "2021/22", "Total", "TirosArcoPorPartido", False)
    assert n_temporada == 20 and r_temporada != pytest.approx(r)

    tabla = tabla_correlaciones(estadisticas).set_index(["Variable", "Condicion"])["r"]
    assert tabla[("Tiros al arco", "Local")] == pytest.approx(0.821, abs=0.001)
    assert tabla[("Tiros al arco", "Visitante")] == pytest.approx(0.779, abs=0.001)


def test_recta_tendencia_igual_a_polyfit():
    x = np.array([1.0, 2.0, 3.0, 4.0])
    y = 2 * x + 1
    recta = tablero.recta_tendencia(x, y)
    assert recta["PuntosPorPartido"].tolist() == pytest.approx([3.0, 9.0])


def test_comparacion_local_visitante(datos):
    estadisticas, _ = datos
    tabla = tablero.comparacion_local_visitante(
        estadisticas, "2024/25", ["Liverpool", "Everton"], "TirosPorPartido")
    assert len(tabla) == 4
    assert set(tabla["Condicion"]) == {"Local", "Visitante"}


def test_ventaja_local_y_resultados(datos):
    estadisticas, equipo_partido = datos
    assert tablero.resultados_temporada(equipo_partido, "2020/21") == {
        "Gana el local": 144, "Empate": 83, "Gana el visitante": 153}
    mejor_local, total, diferencia = tablero.equipos_mejor_de_local(estadisticas)
    assert (mejor_local, total) == (73, 100)
    assert diferencia == pytest.approx(0.276, abs=0.001)
