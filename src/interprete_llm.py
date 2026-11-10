"""Intérprete opcional con un modelo de lenguaje (LLM). Sin clave configurada no hace nada.

El chatbot funciona completo con reglas. Si además se configura una clave, cuando las
reglas no entienden una pregunta se le pide al modelo de lenguaje que diga QUÉ se está
preguntando (intención, equipos y temporada). El modelo de lenguaje nunca calcula ni
responde cifras: los números siempre salen de las funciones del proyecto.

Configuración (variables de entorno o secretos de Streamlit, nunca en el código):
    LLM_API_KEY   clave de la API de Anthropic
    LLM_MODELO    nombre del modelo (opcional)
"""

import json
import os
import urllib.request

URL_API = "https://api.anthropic.com/v1/messages"
MODELO_POR_DEFECTO = "claude-haiku-5-5"

# Intención -> pregunta escrita con las palabras que entienden las reglas del chatbot.
PLANTILLAS = {
    "probabilidades": "probabilidades {equipos}",
    "proximo_partido": "próximo partido {equipos}",
    "comparar": "compara {equipos} {temporada}",
    "por_que": "por qué el modelo estima esas probabilidades {equipos}",
    "confiabilidad": "qué tan confiable es el modelo",
    "clasificacion": "clasificación {temporada}",
    "resumen_equipo": "{equipos} {temporada}",
    "enfrentamiento": "cuánto quedó {equipos} {temporada}",
}

INSTRUCCIONES = (
    "Clasificas preguntas en español sobre la Premier League. Responde SOLO un JSON con las claves "
    '"intencion", "equipos" y "temporada". "intencion" debe ser una de: {intenciones} o "ninguna". '
    '"equipos" es una lista con cero, uno o dos nombres EXACTOS de esta lista: {equipos}. '
    '"temporada" es una de {temporadas} o null. No respondas la pregunta ni escribas cifras.'
)


def leer_clave(secretos=None):
    """Clave de la API desde los secretos de Streamlit o las variables de entorno (None si no hay)."""
    if secretos is not None:
        try:
            if "LLM_API_KEY" in secretos:
                return str(secretos["LLM_API_KEY"])
        except Exception:       # no existe el archivo de secretos
            pass
    return os.environ.get("LLM_API_KEY") or None


def llamar_api(clave, instrucciones, pregunta, tiempo_maximo=10):
    """Envía la pregunta a la API y devuelve el texto de la respuesta."""
    cuerpo = json.dumps({
        "model": os.environ.get("LLM_MODELO", MODELO_POR_DEFECTO), "max_tokens": 200,
        "system": instrucciones, "messages": [{"role": "user", "content": pregunta}],
    }).encode("utf-8")
    peticion = urllib.request.Request(URL_API, data=cuerpo, headers={
        "content-type": "application/json", "x-api-key": clave, "anthropic-version": "2023-06-01"})
    with urllib.request.urlopen(peticion, timeout=tiempo_maximo) as respuesta:
        datos = json.loads(respuesta.read().decode("utf-8"))
    return datos["content"][0]["text"]


def pregunta_desde_json(texto, equipos_validos, temporadas):
    """Valida lo que devolvió el modelo de lenguaje y arma la pregunta para las reglas (o None)."""
    try:
        inicio, fin = texto.index("{"), texto.rindex("}") + 1
        datos = json.loads(texto[inicio:fin])
    except ValueError:
        return None
    intencion = datos.get("intencion")
    equipos = datos.get("equipos") or []
    temporada = datos.get("temporada")
    # Solo se aceptan valores conocidos: así el modelo de lenguaje no puede inventar equipos ni temporadas.
    if intencion not in PLANTILLAS or not isinstance(equipos, list):
        return None
    if any(equipo not in equipos_validos for equipo in equipos) or len(equipos) > 2:
        return None
    if temporada is not None and temporada not in temporadas:
        return None
    pregunta = PLANTILLAS[intencion].format(equipos=" vs ".join(equipos), temporada=temporada or "")
    return " ".join(pregunta.split())


def crear_interprete(clave, llamar=llamar_api):
    """Devuelve la función que usa el chatbot, o None si no hay clave (modo solo reglas)."""
    if not clave:
        return None

    def interpretar(pregunta, equipos_validos, temporadas):
        instrucciones = INSTRUCCIONES.format(intenciones=", ".join(PLANTILLAS), equipos=", ".join(equipos_validos),
                                             temporadas=", ".join(temporadas))
        try:
            texto = llamar(clave, instrucciones, pregunta[:500])
        except Exception:       # sin internet, clave incorrecta, límite de uso...: se sigue con las reglas
            return None
        return pregunta_desde_json(texto, equipos_validos, temporadas)

    return interpretar
