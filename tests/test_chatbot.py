"""Pruebas del chatbot: entiende las preguntas, no inventa cifras y funciona sin servicios externos."""

import pandas as pd
import pytest

from src import calendario as cal
from src import entrenar_modelo
from src.chatbot import EJEMPLOS_CHAT, responder_chat, temporada_mencionada
from src.interprete_llm import crear_interprete, leer_clave, pregunta_desde_json
from src.modelo import CLASES, predecir_partido
from src.preparar_datos import CARPETA_PROCESADOS
from src.variables_modelo import VARIABLES_MODELO

CLAVES = {"tipo", "texto", "tabla", "tarjetas", "probabilidades", "grafico", "fuente"}


@pytest.fixture(scope="module")
def base():
    partidos = pd.read_csv(CARPETA_PROCESADOS / "partidos_limpios.csv", parse_dates=["Date"])
    estadisticas = pd.read_csv(CARPETA_PROCESADOS / "estadisticas_equipo_temporada.csv")
    evaluacion = entrenar_modelo.cargar_evaluacion()
    servicio = entrenar_modelo.preparar_modelo(partidos, evaluacion["c_elegido"])
    return {"partidos": partidos, "estadisticas": estadisticas, "evaluacion": evaluacion, "servicio": servicio}


def hay_partidos_pendientes(base):
    """True si quedan partidos por jugar en la temporada en curso (al final de la temporada, no)."""
    temporada = sorted(base["partidos"]["Temporada"].unique())[-1]
    jugados = base["partidos"][base["partidos"]["Temporada"] == temporada]
    return not cal.partidos_pendientes(cal.cargar_calendario(temporada), jugados).empty


def contexto_nuevo(base, temporada="2025/26", interprete=None):
    """Contexto de una conversación nueva (sin memoria) y sin modelo de lenguaje."""
    return {"partidos": base["partidos"], "estadisticas": base["estadisticas"], "temporada": temporada,
            "servicio_modelo": lambda: base["servicio"], "evaluacion": base["evaluacion"], "memoria": {},
            "interprete": interprete}


def test_los_ejemplos_se_entienden_y_tienen_la_misma_estructura(base):
    contexto = contexto_nuevo(base)
    tipos = []
    for ejemplo in EJEMPLOS_CHAT:
        resultado = responder_chat(ejemplo, contexto)
        assert set(resultado) == CLAVES
        tipos.append(resultado["tipo"])
    if hay_partidos_pendientes(base):
        assert tipos == ["ranking", "comparacion", "calendario", "prediccion", "explicacion", "confiabilidad"]
    else:
        # Al terminar la temporada no quedan partidos que predecir: el chatbot debe decirlo, no inventar.
        assert tipos[:2] == ["ranking", "comparacion"] and tipos[-1] == "confiabilidad"
        assert "prediccion" not in tipos


def test_estadisticas_salen_de_los_datos(base):
    contexto = contexto_nuevo(base, temporada="2021/22")
    # La temporada escrita en la pregunta manda sobre la de la barra lateral.
    resultado = responder_chat("¿Quién ganó más partidos en 2025/26?", contexto)
    assert "**Arsenal**" in resultado["texto"] and "**26**" in resultado["texto"]
    assert resultado["tabla"].iloc[0].tolist() == ["Arsenal", 38, 26]
    assert "2025/26" in resultado["fuente"] and resultado["grafico"]["datos"].shape[0] == 5

    resultado = responder_chat("¿Qué equipo tuvo más tiros al arco?", contexto)       # usa 2021/22
    estadisticas = base["estadisticas"]
    total = estadisticas[(estadisticas["Temporada"] == "2021/22") & (estadisticas["Condicion"] == "Total")]
    lider = total.sort_values("TirosArco", ascending=False).iloc[0]
    assert f"**{lider['Equipo']}**" in resultado["texto"] and f"**{int(lider['TirosArco'])}**" in resultado["texto"]

    resultado = responder_chat("que equipo recibio menos goles en 2023/24", contexto)
    assert "**Arsenal**" in resultado["texto"] and "**29**" in resultado["texto"]


def test_comparacion_y_clasificacion(base):
    contexto = contexto_nuevo(base)
    resultado = responder_chat("Compara Arsenal y Liverpool", contexto)
    assert resultado["tipo"] == "comparacion" and len(resultado["tabla"]) == 13
    assert "**85 puntos**" in resultado["texto"] and "**60**" in resultado["texto"]
    resultado = responder_chat("¿cómo va la tabla?", contexto)
    assert resultado["tipo"] == "clasificacion" and len(resultado["tabla"]) == 20
    assert "fue campeón" in resultado["texto"] and "Arsenal" in resultado["texto"]
    resultado = responder_chat("compara Arsenal y Luton", contexto)
    assert resultado["tipo"] == "sin_datos"


def test_el_asistente_de_reglas_sigue_respondiendo(base):
    contexto = contexto_nuevo(base, temporada="2024/25")
    resultado = responder_chat("¿Cuánto quedó el Arsenal contra el Liverpool?", contexto)
    assert resultado["tipo"] == "partidos" and "2-2" in resultado["texto"] and len(resultado["tabla"]) == 2
    resultado = responder_chat("¿Cuál fue el partido con más goles?", contexto)
    assert resultado["tipo"] == "partidos"


def test_las_probabilidades_son_las_de_predict_proba(base):
    contexto = contexto_nuevo(base)
    pregunta = "¿Qué probabilidades tiene el Chelsea de ganar su siguiente encuentro?"
    if not hay_partidos_pendientes(base):
        pregunta = "probabilidades Chelsea vs Arsenal"      # partido hipotético
    resultado = responder_chat(pregunta, contexto)
    assert resultado["tipo"] == "prediccion"
    mostradas = resultado["probabilidades"]
    assert mostradas["H"] + mostradas["D"] + mostradas["A"] == pytest.approx(1.0)
    assert "Chelsea" in (mostradas["local"], mostradas["visitante"])

    # Se recalcula directamente con el modelo y predict_proba: debe dar exactamente lo mismo.
    prediccion = contexto["memoria"]["ultima_prediccion"]
    servicio = base["servicio"]
    de_nuevo = predecir_partido(servicio["modelo"], servicio["historial"], prediccion["local"],
                                prediccion["visitante"], prediccion["fecha"])
    fila = pd.DataFrame([de_nuevo["variables"]])[VARIABLES_MODELO]
    directas = dict(zip(servicio["modelo"].classes_, servicio["modelo"].predict_proba(fila)[0]))
    for clase in CLASES:
        assert mostradas[clase] == pytest.approx(directas[clase])
        porcentaje = f"{100 * directas[clase]:.1f}".replace(".", ",") + " %"
        assert porcentaje in resultado["texto"]             # el texto muestra esas mismas cifras
    assert "no una certeza" in resultado["fuente"] and "apuestas" in resultado["fuente"]


def test_por_que_usa_la_ultima_prediccion(base):
    contexto = contexto_nuevo(base)
    sin_prediccion = responder_chat("¿por qué?", contexto)
    assert sin_prediccion["tipo"] != "explicacion"
    responder_chat("probabilidades Arsenal vs Liverpool", contexto)
    resultado = responder_chat("¿por qué?", contexto)
    assert resultado["tipo"] == "explicacion" and len(resultado["tabla"]) == len(VARIABLES_MODELO)
    assert "Arsenal" in resultado["texto"] and "Liverpool" in resultado["texto"]


def test_proximo_partido_viene_del_calendario(base):
    contexto = contexto_nuevo(base)
    resultado = responder_chat("¿Cuál es el próximo partido del Manchester City?", contexto)
    if not hay_partidos_pendientes(base):
        assert resultado["tipo"] == "sin_datos"            # temporada terminada: no inventa partidos
        return
    assert resultado["tipo"] == "calendario" and "Man City" in resultado["texto"]
    assert "fixturedownload.com" in resultado["fuente"]
    assert [tarjeta[1] for tarjeta in resultado["tarjetas"]].count("VS") == 1
    lista = responder_chat("próximos partidos", contexto)
    assert lista["tipo"] == "calendario" and list(lista["tabla"].columns) == ["Jornada", "Fecha", "Local", "Visitante"]


def test_confiabilidad_muestra_las_metricas_guardadas(base):
    resultado = responder_chat("¿Qué tan confiable es el modelo?", contexto_nuevo(base))
    assert resultado["tipo"] == "confiabilidad"
    metricas = base["evaluacion"]["prueba"]["modelo"]
    assert resultado["tabla"].loc[0, "Modelo"] == round(metricas["accuracy"], 3)
    assert "se equivoca" in resultado["texto"]              # no se presenta como infalible
    sin_evaluacion = dict(contexto_nuevo(base), evaluacion=None)
    assert responder_chat("¿Qué tan confiable es el modelo?", sin_evaluacion)["tipo"] == "sin_datos"


def test_preguntas_ambiguas_o_sin_informacion(base):
    contexto = contexto_nuevo(base)
    assert responder_chat("compara manchester y arsenal", contexto)["tipo"] == "aclaracion"
    assert responder_chat("probabilidades", contexto)["tipo"] == "aclaracion"
    assert responder_chat("probabilidades del Luton", contexto)["tipo"] == "sin_datos"     # no juega esta temporada
    assert responder_chat("hola", contexto)["tipo"] == "ayuda"
    assert responder_chat("   ", contexto)["tipo"] == "ayuda"
    assert responder_chat("probabilidades Arsenal, Chelsea y Liverpool", contexto)["tipo"] == "aclaracion"


def test_reconoce_la_temporada_escrita_de_varias_formas():
    temporadas = ["2024/25", "2025/26", "2026/27"]
    assert temporada_mencionada("goles en 2025/26", temporadas) == "2025/26"
    assert temporada_mencionada("goles en 2025-26", temporadas) == "2025/26"
    assert temporada_mencionada("goles en la 24/25", temporadas) == "2024/25"
    assert temporada_mencionada("goles esta temporada", temporadas) == "2026/27"
    assert temporada_mencionada("goles del arsenal", temporadas) is None


# --- Modelo de lenguaje opcional --------------------------------------------------
def test_funciona_sin_api_externa(base, monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    assert leer_clave() is None and crear_interprete(None) is None
    resultado = responder_chat("probabilidades del Arsenal", contexto_nuevo(base))
    assert resultado["tipo"] == "prediccion"


def test_el_modelo_de_lenguaje_solo_interpreta(base):
    llamadas = []

    def api_simulada(clave, instrucciones, pregunta):
        llamadas.append(pregunta)
        return '{"intencion": "probabilidades", "equipos": ["Chelsea"], "temporada": null}'

    interprete = crear_interprete("clave-de-prueba", llamar=api_simulada)
    resultado = responder_chat("¿cómo le irá a los blues?", contexto_nuevo(base, interprete=interprete))
    assert llamadas == ["¿cómo le irá a los blues?"]
    assert resultado["tipo"] == "prediccion" and "Entendí" in resultado["texto"]
    # Una pregunta que las reglas entienden no llega al modelo de lenguaje.
    responder_chat("probabilidades del Arsenal", contexto_nuevo(base, interprete=interprete))
    assert len(llamadas) == 1


def test_el_modelo_de_lenguaje_no_puede_inventar(base):
    equipos, temporadas = ["Chelsea", "Arsenal"], ["2025/26"]
    assert pregunta_desde_json('{"intencion":"comparar","equipos":["Real Madrid"],"temporada":null}', equipos, temporadas) is None
    assert pregunta_desde_json('{"intencion":"inventar","equipos":[],"temporada":null}', equipos, temporadas) is None
    assert pregunta_desde_json('{"intencion":"clasificacion","equipos":[],"temporada":"1999/00"}', equipos, temporadas) is None
    assert pregunta_desde_json("El Chelsea ganará 3-0", equipos, temporadas) is None
    assert pregunta_desde_json('{"intencion":"comparar","equipos":["Chelsea","Arsenal"],"temporada":"2025/26"}',
                               equipos, temporadas) == "compara Chelsea vs Arsenal 2025/26"

    def api_caida(clave, instrucciones, pregunta):
        raise OSError("sin conexión")

    interprete = crear_interprete("clave-de-prueba", llamar=api_caida)
    assert responder_chat("blablabla", contexto_nuevo(base, interprete=interprete))["tipo"] == "ayuda"
