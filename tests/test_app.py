"""Prueba de la aplicación con la herramienta oficial de Streamlit (AppTest).

Ejecuta app.py sin abrir el navegador, recorre las trece secciones, cambia los
filtros y comprueba que la página no da errores y que el contenido cambia.
Requiere tener Streamlit instalado (pip install -r requirements.txt).
"""

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

RUTA_APP = "../app.py"  # relativa a esta carpeta (tests/)
SECCIONES = ["Inicio", "Clasificación", "Análisis", "Comparador de equipos", "Local vs. visitante",
             "Relaciones y correlaciones", "Ranking personalizado", "Récords históricos",
             "Goleadores y Asistencias", "Partidos", "Detector de sorpresas", "Asistente IA", "Curiosidades"]


def iniciar(seccion="Inicio"):
    """Ejecuta la app, abre una sección y comprueba que no haya errores."""
    app = AppTest.from_file(RUTA_APP, default_timeout=60)
    app.run()
    assert not app.exception, app.exception
    if seccion != "Inicio":
        app.sidebar.radio[0].set_value(seccion).run()
        assert not app.exception, app.exception
    return app


def textos(app):
    return " ".join(elemento.value for elemento in app.markdown)


def boton(app, etiqueta):
    return next(b for b in app.button if b.label == etiqueta)


def test_el_menu_tiene_las_trece_secciones_y_la_temporada():
    app = iniciar()
    assert list(app.sidebar.radio[0].options) == SECCIONES
    assert app.sidebar.selectbox[0].value == "2024/25"
    assert "PREMIER LEAGUE DATA ANALYTICS" in textos(app)
    assert "no oficial" in textos(app).lower() or "No es un producto oficial" in textos(app)


@pytest.mark.parametrize("seccion", SECCIONES)
def test_cada_seccion_abre_sin_errores_en_todas_las_temporadas(seccion):
    app = iniciar(seccion)
    for temporada in ["2020/21", "2021/22", "2022/23", "2023/24", "2024/25"]:
        app.sidebar.selectbox[0].select(temporada).run()
        assert not app.exception, (seccion, temporada, app.exception)


def test_clasificacion_cambia_con_la_temporada_y_la_condicion():
    app = iniciar("Clasificación")
    assert app.sidebar.multiselect[0].value == ["Liverpool", "Arsenal", "Man City"]
    app.sidebar.selectbox[0].select("2023/24").run()
    assert not app.exception
    tabla = app.dataframe[0].value
    assert tabla.loc[0, "Equipo"] == "Man City"
    assert "Pts oficiales" in tabla.columns and "Insignia" in tabla.columns
    assert len(app.warning) == 1                    # aviso de las sanciones
    assert "Luton" in app.sidebar.multiselect[0].options
    app.sidebar.radio[1].set_value("Local").run()
    assert not app.exception
    assert (app.dataframe[0].value["PJ"] == 19).all()


def test_sin_equipos_elegidos_muestra_avisos_y_no_falla():
    app = iniciar("Análisis")
    app.sidebar.multiselect[0].set_value([]).run()
    assert not app.exception
    assert any("al menos un equipo" in aviso.value for aviso in app.info)


def test_cambiar_metrica_y_alcance_actualiza_la_correlacion():
    app = iniciar("Análisis")
    valor_inicial = app.metric[3].value
    app.sidebar.selectbox[1].select("Faltas").run()
    assert not app.exception
    assert app.metric[3].value != valor_inicial
    app.sidebar.toggle[0].set_value(False).run()
    assert not app.exception
    assert "n = 20" in app.metric[3].delta


def test_goleadores_muestra_lideres_y_aviso_de_datos_parciales():
    app = iniciar("Goleadores y Asistencias")
    assert "Mohamed Salah" in textos(app)           # 2024/25: 29 goles y 18 asistencias
    app.sidebar.selectbox[0].select("2020/21").run()
    assert not app.exception
    assert "Harry Kane" in textos(app)
    assert any("incompletos" in aviso.value for aviso in app.warning)
    assert len(app.dataframe[1].value) == 3          # solo 3 asistentes en 2020/21


def test_partidos_filtra_un_enfrentamiento():
    app = iniciar("Partidos")
    assert len(app.dataframe[0].value) == 380
    app.main.selectbox[0].select("Liverpool").run()   # Equipo
    app.main.selectbox[1].select("Arsenal").run()     # Rival
    assert not app.exception
    assert len(app.dataframe[0].value) == 2


def test_asistente_responde_y_guarda_el_historial():
    app = iniciar("Asistente IA")
    app.chat_input[0].set_value("¿Cuánto quedó el Arsenal contra el Liverpool?").run()
    assert not app.exception
    assert "2-2" in textos(app)
    boton(app, "¿Cuántos partidos ganó el Chelsea?").click().run()
    assert not app.exception
    assert len(app.session_state["chat"]) == 4
    boton(app, "Borrar conversación").click().run()
    assert not app.exception
    assert app.session_state["chat"] == []


def test_sorprendeme_muestra_una_curiosidad():
    app = iniciar("Curiosidades")
    boton(app, "SORPRÉNDEME").click().run()
    assert not app.exception
    assert len(app.session_state["curiosidades_vistas"]["2024/25"]) == 1
    boton(app, "SORPRÉNDEME").click().run()
    vistas = app.session_state["curiosidades_vistas"]["2024/25"]
    assert len(vistas) == 2 and vistas[0] != vistas[1]


# --- Secciones nuevas (versión 3) ---------------------------------------------
def test_comparador_avisa_si_se_elige_el_mismo_equipo():
    app = iniciar("Comparador de equipos")
    assert len(app.dataframe) == 2                    # tabla de comparación y de local/visitante
    app.main.selectbox[1].select(app.main.selectbox[0].value).run()
    assert not app.exception
    assert any("mismo equipo" in aviso.value for aviso in app.warning)
    assert len(app.dataframe) == 0


def test_comparador_cambia_con_la_condicion():
    app = iniciar("Comparador de equipos")
    total = app.dataframe[0].value
    app.main.radio[0].set_value("Local").run()
    assert not app.exception
    assert not app.dataframe[0].value.equals(total)


def test_local_visitante_muestra_conclusion_y_aviso_de_west_ham():
    app = iniciar("Local vs. visitante")
    app.sidebar.selectbox[0].select("2021/22").run()
    app.main.selectbox[0].select("West Ham").run()
    assert not app.exception
    assert "West Ham obtuvo más puntos como local (32) que como visitante (24)" in textos(app)
    assert any("37 partidos" in aviso.value for aviso in app.info)


def test_correlaciones_cambian_con_el_alcance_y_las_variables():
    app = iniciar("Relaciones y correlaciones")
    assert "n = 100" in app.metric[0].delta                             # cinco temporadas
    # El valor de r puede coincidir por casualidad (tiros y goles: 0,83 en los dos casos),
    # así que se comprueba el número de observaciones.
    app.main.radio[0].set_value(app.main.radio[0].options[1]).run()    # solo la temporada elegida
    assert not app.exception
    assert "n = 20" in app.metric[0].delta
    app.main.selectbox[0].select("Faltas y tarjetas").run()
    assert not app.exception and "n = 20" in app.metric[0].delta
    app.main.multiselect[0].set_value(["Puntos"]).run()
    assert any("al menos dos variables" in aviso.value for aviso in app.info)


def test_records_de_todos_los_tipos():
    app = iniciar("Récords históricos")
    assert "93" in textos(app)                        # Man City 2021/22, récord de puntos
    for tipo in ["Acumulado de las cinco temporadas", "Récords de partidos"]:
        app.main.radio[0].set_value(tipo).run()
        assert not app.exception
    assert "Man United 9-0 Southampton" in textos(app)


def test_ranking_menos_goles_recibidos_empieza_por_el_menor():
    app = iniciar("Ranking personalizado")
    app.main.selectbox[0].select("Menos goles recibidos").run()
    assert not app.exception
    valores = app.dataframe[0].value["Goles recibidos"]
    assert valores.is_monotonic_increasing


def test_detector_de_sorpresas_filtra_y_avisa_si_no_hay_partidos():
    app = iniciar("Detector de sorpresas")
    todos = len(app.dataframe[0].value)
    app.main.selectbox[1].select("Liverpool").run()
    assert not app.exception
    assert len(app.dataframe[0].value) < todos
    app.main.slider[0].set_value(25).run()
    assert not app.exception
