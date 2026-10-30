"""Pruebas con los datos reales de data/raw/.

Comprueban que el procesamiento completo da resultados coherentes y que la
clasificación calculada coincide con las tablas oficiales publicadas.
"""

import pandas as pd
import pytest

from src.preparar_datos import generar_tablas


@pytest.fixture(scope="module")
def tablas():
    """Genera todas las tablas una sola vez para las pruebas de este archivo."""
    resultado, _ = generar_tablas()
    return resultado


def test_tamanos(tablas):
    assert tablas["partidos_limpios"].shape == (1900, 22)
    assert (tablas["partidos_limpios"]["Temporada"].value_counts() == 380).all()
    assert len(tablas["equipo_partido"]) == 3800
    assert len(tablas["estadisticas_equipo_temporada"]) == 300


def test_cada_partido_en_su_temporada(tablas):
    partidos = tablas["partidos_limpios"]
    for temporada, grupo in partidos.groupby("Temporada"):
        anio = int(temporada[:4])
        assert grupo["Date"].min() >= pd.Timestamp(f"{anio}-08-01")
        assert grupo["Date"].max() <= pd.Timestamp(f"{anio + 1}-06-30")


def test_unico_cambio_de_limpieza(tablas):
    partidos = tablas["partidos_limpios"]
    vacias = partidos[partidos.isna().any(axis=1)]
    assert len(vacias) == 1
    fila = vacias.iloc[0]
    assert (fila["HomeTeam"], fila["AwayTeam"], fila["FTHG"], fila["FTAG"]) == ("Newcastle", "West Ham", 2, 4)


def test_puntos_y_goles_coherentes(tablas):
    registros = tablas["equipo_partido"]
    partidos = tablas["partidos_limpios"]
    puntos = registros.groupby("PartidoID")["Puntos"].sum()
    assert set(puntos.unique()) == {2, 3}
    assert (puntos == 2).sum() == (partidos["FTR"] == "D").sum()
    assert registros["GolesFavor"].sum() == registros["GolesContra"].sum()


def test_38_partidos_por_equipo(tablas):
    registros = tablas["equipo_partido"]
    conteo = registros.groupby(["Temporada", "Equipo", "Condicion"]).size()
    assert (conteo == 19).all()
    assert registros["NumeroPartido"].max() == 38


# Tablas finales oficiales: equipo -> (V, E, D, GF, GC, puntos oficiales, sanción).
# 2023/24: NBC Sports. 2024/25: Spurs Odyssey. Consultadas en octubre de 2026.
OFICIAL = {
    "2023/24": {
        "Man City": (28, 7, 3, 96, 34, 91, 0), "Arsenal": (28, 5, 5, 91, 29, 89, 0),
        "Liverpool": (24, 10, 4, 86, 41, 82, 0), "Aston Villa": (20, 8, 10, 76, 61, 68, 0),
        "Tottenham": (20, 6, 12, 74, 61, 66, 0), "Chelsea": (18, 9, 11, 77, 63, 63, 0),
        "Newcastle": (18, 6, 14, 85, 62, 60, 0), "Man United": (18, 6, 14, 57, 58, 60, 0),
        "West Ham": (14, 10, 14, 60, 74, 52, 0), "Crystal Palace": (13, 10, 15, 57, 58, 49, 0),
        "Brighton": (12, 12, 14, 55, 62, 48, 0), "Bournemouth": (13, 9, 16, 54, 67, 48, 0),
        "Fulham": (13, 8, 17, 55, 61, 47, 0), "Wolves": (13, 7, 18, 50, 65, 46, 0),
        "Everton": (13, 9, 16, 40, 51, 40, 8), "Brentford": (10, 9, 19, 56, 65, 39, 0),
        "Nott'm Forest": (9, 9, 20, 49, 67, 32, 4), "Luton": (6, 8, 24, 52, 85, 26, 0),
        "Burnley": (5, 9, 24, 41, 78, 24, 0), "Sheffield United": (3, 7, 28, 35, 104, 16, 0),
    },
    "2024/25": {
        "Liverpool": (25, 9, 4, 86, 41, 84, 0), "Arsenal": (20, 14, 4, 69, 34, 74, 0),
        "Man City": (21, 8, 9, 72, 44, 71, 0), "Chelsea": (20, 9, 9, 64, 43, 69, 0),
        "Newcastle": (20, 6, 12, 68, 47, 66, 0), "Aston Villa": (19, 9, 10, 58, 51, 66, 0),
        "Nott'm Forest": (19, 8, 11, 58, 46, 65, 0), "Brighton": (16, 13, 9, 66, 59, 61, 0),
        "Bournemouth": (15, 11, 12, 58, 46, 56, 0), "Brentford": (16, 8, 14, 66, 57, 56, 0),
        "Fulham": (15, 9, 14, 54, 54, 54, 0), "Crystal Palace": (13, 14, 11, 51, 51, 53, 0),
        "Everton": (11, 15, 12, 42, 44, 48, 0), "West Ham": (11, 10, 17, 46, 62, 43, 0),
        "Man United": (11, 9, 18, 44, 54, 42, 0), "Wolves": (12, 6, 20, 54, 69, 42, 0),
        "Tottenham": (11, 5, 22, 64, 65, 38, 0), "Leicester": (6, 7, 25, 33, 80, 25, 0),
        "Ipswich": (4, 10, 24, 36, 82, 22, 0), "Southampton": (2, 6, 30, 26, 86, 12, 0),
    },
}


@pytest.mark.parametrize("temporada", list(OFICIAL))
def test_clasificacion_coincide_con_la_oficial(tablas, temporada):
    calculada = tablas["clasificacion"]
    calculada = calculada[calculada["Temporada"] == temporada].set_index("Equipo")
    assert len(calculada) == 20
    for equipo, (v, e, d, gf, gc, puntos_oficiales, sancion) in OFICIAL[temporada].items():
        fila = calculada.loc[equipo]
        calculado = (fila["V"], fila["E"], fila["D"], fila["GolesFavor"], fila["GolesContra"])
        assert calculado == (v, e, d, gf, gc), equipo
        assert fila["Puntos"] - sancion == puntos_oficiales, equipo


def test_orden_2024_25_igual_al_oficial(tablas):
    calculada = tablas["clasificacion"]
    orden = calculada[calculada["Temporada"] == "2024/25"]["Equipo"].tolist()
    assert orden == list(OFICIAL["2024/25"])
