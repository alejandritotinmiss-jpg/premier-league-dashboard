"""Chatbot híbrido: entiende la intención de la pregunta y consulta funciones del proyecto.

"Híbrido" porque une tres cosas: reglas para entender la pregunta, las estadísticas de
los datos y el modelo predictivo. Nunca inventa un número: cada cifra sale de una
función de src/ (estadísticas, comparador, calendario o modelo).

Cada respuesta es un diccionario que la aplicación sabe dibujar:
    texto           explicación breve
    tabla           tabla de datos (opcional)
    tarjetas        lista de (título, valor, detalle) (opcional)
    probabilidades  predicción de un partido (opcional)
    grafico         datos de un gráfico de barras (opcional)
    fuente          de dónde salen los datos y hasta qué fecha
"""

import re

import pandas as pd

from src import asistente, calendario as cal, comparador, goleadores_probables, records
from src.equipos import normalizar
from src.estadisticas import calcular_clasificacion
from src.jugadores import buscar_jugadores, cargar_jugadores, lideres, ranking
from src.modelo import (NOMBRE_MODELO, NOMBRES_CLASES, explicar_prediccion, predecir_partido,
                        ventaja_local_del_modelo)
from src.partidos import enfrentamientos, fecha_texto, ganador, partidos_de_temporada, tabla_resumen

EJEMPLOS_CHAT = [
    "¿Quién ganó más partidos en 2025/26?",
    "Compara Arsenal y Liverpool",
    "¿Cuál es el próximo partido del Manchester City?",
    "¿Qué probabilidades tiene el Chelsea de ganar su siguiente encuentro?",
    "¿Por qué el modelo estima esas probabilidades?",
    "¿Qué tan confiable es el modelo?",
    "¿Quién tiene más opciones de marcar en la próxima jornada?",
    "¿Quién es el máximo goleador?",
    "Manchester United contra Liverpool",
]

# Estadísticas por equipo para preguntas como "¿qué equipo tuvo más tiros al arco?".
# Palabras clave -> (nombre, columna de la tabla de estadísticas). El orden importa.
ESTADISTICAS_EQUIPO = [
    (["gano mas", "mas partidos gano", "mas victorias", "mas partidos ganados", "mas triunfos",
      "gano menos", "menos victorias"], ("Partidos ganados", "V")),
    (["perdio mas", "mas derrotas", "mas partidos perdidos", "perdio menos", "menos derrotas"],
     ("Partidos perdidos", "D")),
    (["empato mas", "mas empates", "menos empates"], ("Partidos empatados", "E")),
    (["goles recibio", "recibio mas goles", "recibio menos goles", "goles en contra", "goles recibidos",
      "mejor defensa", "peor defensa"], ("Goles recibidos", "GolesContra")),
    (["tiros al arco", "tiros a puerta", "remates al arco"], ("Tiros al arco", "TirosArco")),
    (["tiros", "remates"], ("Tiros", "Tiros")),
    (["corner", "tiros de esquina"], ("Córners", "Corners")),
    (["faltas"], ("Faltas cometidas", "Faltas")),
    (["amarillas"], ("Tarjetas amarillas", "Amarillas")),
    (["rojas", "expulsion"], ("Tarjetas rojas", "Rojas")),
    (["tarjetas"], ("Tarjetas (amarillas y rojas)", "Tarjetas")),
    (["puntos"], ("Puntos", "Puntos")),
    (["goles", "goleador", "anoto mas", "marco mas"], ("Goles anotados", "GolesFavor")),
]

PALABRAS_CONFIABILIDAD = ["confiable", "fiable", "confianza", "que tan bueno", "acierta", "aciertos", "precision",
                          "exactitud", "metricas", "accuracy", "calidad del modelo", "tan preciso"]
PALABRAS_PROBABILIDAD = ["probabilidad", "probable", "posibilidad", "chance", "pronostico", "prediccion", "predice",
                         "predecir", "va a ganar", "ganara", "quien gana", "favorito"]
PALABRAS_PROXIMO = ["proximo", "proxima", "siguiente", "cuando juega", "cuando vuelve a jugar", "calendario"]
PALABRAS_COMPARAR = ["compara", "comparacion", "comparame", " vs ", "versus", "frente a frente"]
PALABRAS_TABLA = ["clasificacion", "tabla de posiciones", "posiciones", "como va la tabla", "tabla", "va primero",
                  "primer lugar", "puntero", "lidera", "lider", "campeon", "gano la liga", "gano la premier",
                  "ganador de la liga", "ganador de la premier", "titulo"]
PALABRAS_DESCENSO = ["descend", "descenso", "bajaron", "relegad", "zona roja"]
PALABRAS_HISTORIAL = ["historial", "historico", "todas las temporadas", "de siempre", "cuantas veces"]
PALABRAS_RECORD = ["record", "en la historia", "historico", "de todas las temporadas", "de siempre"]
PALABRAS_VENTAJA_LOCAL = ["ventaja de local", "local o visitante", "local y visitante", "local vs visitante",
                          "jugar en casa", "en casa o fuera", "factor campo", "localia", "de local o de visitante"]
PALABRAS_JUGADORES_GOLES = ["goleador", "pichichi", "bota de oro", "quien marco mas", "quien anoto mas",
                            "quien marca mas", "quien mete mas", "quien hace mas goles", "quien lleva mas goles",
                            "jugador con mas goles", "jugadores con mas goles"]
PALABRAS_JUGADORES_ASISTENCIAS = ["asistencia", "asistidor", "asistente", "pases de gol", "playmaker"]
# "meta gol", "marque un gol", "haga gol"... (para "¿quién crees que meta gol?")
VERBOS_GOL = re.compile(r"\b(meta|meter|mete|metera|marque|marcar|marcara|marca|anote|anotar|anotara|anota|haga|"
                        r"hacer|hara|convierta|convertir)\b(\s+\w+){0,3}\s+gol")
PALABRAS_FUTURO = ["proximo", "proxima", "siguiente", "probab", "posibilidad", "opciones", "crees", "va a",
                   "podria", "chance", "favorito", "mas probable"]
SALUDOS = {"hola", "holi", "buenas", "buenos", "buen", "dias", "tardes", "noches", "hey", "saludos", "que", "tal",
           "como", "estas", "esta", "hello", "hi"}
PALABRAS_AYUDA = ["que puedes hacer", "que sabes", "que preguntas", "como funcionas", "que haces", "ayuda",
                  "que te puedo preguntar", "en que me ayudas"]


def respuesta(texto, tipo, tabla=None, tarjetas=None, probabilidades=None, grafico=None, fuente=None):
    """Empaqueta la respuesta del chatbot en un diccionario con siempre las mismas claves."""
    return {"tipo": tipo, "texto": texto, "tabla": tabla, "tarjetas": tarjetas,
            "probabilidades": probabilidades, "grafico": grafico, "fuente": fuente}


def porcentaje(valor):
    """0.4567 -> '45,7 %'."""
    return f"{100 * valor:.1f}".replace(".", ",") + " %"


def contiene(texto, palabras):
    return any(palabra in texto for palabra in palabras)


def plural(cantidad, singular, plural_):
    """1 -> 'victoria', 2 -> 'victorias'."""
    return singular if cantidad == 1 else plural_


def datos_de_jugadores(contexto):
    """Goleadores, asistencias y fuentes (los pasa la app; si no, se leen de data/jugadores/)."""
    if contexto.get("jugadores") is None:
        contexto["jugadores"] = cargar_jugadores()
    return contexto["jugadores"]


def temporada_en_curso(contexto, temporada):
    """True si la temporada todavía no tiene sus 380 partidos."""
    return len(partidos_de_temporada(contexto["partidos"], temporada)) < 380


def temporada_mencionada(texto, temporadas):
    """Temporada escrita en la pregunta ("2025/26", "2025-26", "25/26") o None."""
    for temporada in temporadas:                       # por ejemplo "2025/26"
        formas = [temporada, temporada.replace("/", "-"), temporada.replace("/", " "), temporada[2:],
                  temporada[2:].replace("/", "-"), f"{temporada[:4]}/20{temporada[5:]}",
                  f"{temporada[:4]}-20{temporada[5:]}"]
        if any(re.search(r"(?<!\d)" + re.escape(forma) + r"(?!\d)", texto) for forma in formas):
            return temporada
    if contiene(texto, ["temporada actual", "esta temporada", "temporada en curso"]):
        return temporadas[-1]
    if contiene(texto, ["temporada pasada", "temporada anterior"]) and len(temporadas) > 1:
        return temporadas[-2]
    return None


def fuente_estadisticas(contexto, temporada):
    return (f"Fuente: Football-Data.co.uk · temporada {temporada} · datos hasta el "
            f"{fecha_texto(contexto['partidos']['Date'].max())}")


def fuente_modelo(contexto):
    servicio = contexto["servicio_modelo"]()
    return (f"{NOMBRE_MODELO} · {servicio['version']} · datos hasta el {fecha_texto(servicio['fecha_datos'])}. "
            "Es una estimación estadística, no una certeza ni una recomendación de apuestas.")


# ---------------------------------------------------------------------------
# Función principal
# ---------------------------------------------------------------------------
def responder_chat(pregunta, contexto):
    """Responde una pregunta.

    contexto es un diccionario con:
        partidos, estadisticas   tablas del proyecto
        temporada                temporada elegida en la barra lateral
        servicio_modelo          función que devuelve el modelo ya entrenado
        evaluacion               métricas guardadas del modelo (o None)
        memoria                  diccionario con lo último de la conversación (equipos, predicción...)
    """
    texto = normalizar(pregunta)
    texto = " " + re.sub(r"[¿?¡!.,;:]", " ", texto) + " "
    memoria = contexto.setdefault("memoria", {})
    temporadas = sorted(contexto["estadisticas"]["Temporada"].unique())
    if not texto.strip():
        return respuesta("Escribe una pregunta sobre los equipos, los partidos o las predicciones.", "ayuda")

    charla = responder_charla(texto)
    if charla is not None:
        return charla

    temporada_escrita = temporada_mencionada(texto, temporadas)
    temporada = temporada_escrita or contexto["temporada"]
    sin_temporada = re.sub(r"\d{2,4}\s?[/-]\s?\d{2,4}", " ", texto)     # para que "2025/26" no confunda
    if "manchester" in sin_temporada and not re.search(r"manchester (city|united|utd)", sin_temporada):
        return respuesta("¿Te refieres al **Manchester City** o al **Manchester United**? "
                         "Escribe el nombre completo.", "aclaracion")
    equipos = asistente.encontrar_equipos(sin_temporada)

    # Preguntas de seguimiento ("¿y por qué?", "¿y su próximo partido?"): se usan los equipos anteriores.
    es_seguimiento = not equipos and contiene(texto, [" su ", " sus ", " ese ", " esas ", " esos ", " y el ", " y la "])
    equipos_o_memoria = equipos or (memoria.get("equipos", []) if es_seguimiento else [])

    # Jugadores: quién puede marcar en un partido, y goleadores o asistentes de una temporada.
    goleadores, asistencias, _ = datos_de_jugadores(contexto)
    nombres = buscar_jugadores(sin_temporada, goleadores, asistencias)
    if es_pregunta_de_goleador_probable(texto):
        return responder_goleador_probable(contexto, equipos_o_memoria, nombres)
    if nombres and (not equipos or contiene(texto, ["gol", "asist"])):
        return responder_jugador(contexto, nombres, texto)
    pide_asistencias = contiene(texto, PALABRAS_JUGADORES_ASISTENCIAS)
    if (contiene(texto, PALABRAS_JUGADORES_GOLES) or pide_asistencias) and " equipo" not in texto:
        return responder_lideres_jugadores(contexto, temporada, pide_asistencias, equipos[0] if len(equipos) == 1 else None)

    if contiene(texto, PALABRAS_CONFIABILIDAD) and contiene(texto, ["modelo", "prediccion", "pronostico", "confiable",
                                                                  "fiable", "acierta"]):
        return responder_confiabilidad(contexto)
    if contiene(texto, ["baseline", "linea base", "referencia del modelo"]):
        return responder_baseline(contexto)
    if "por que" in texto and (contiene(texto, ["modelo", "probabilidad", "estima", "prediccion", "pronostico"])
                               or "ultima_prediccion" in memoria):
        return responder_por_que(contexto, equipos)
    if contiene(texto, PALABRAS_PROBABILIDAD):
        return responder_probabilidades(contexto, equipos or (memoria.get("equipos", []) if es_seguimiento else []))
    if contiene(texto, PALABRAS_PROXIMO):
        return responder_proximo(contexto, equipos or (memoria.get("equipos", []) if es_seguimiento else []))
    if contiene(texto, PALABRAS_COMPARAR) and len(equipos) == 2:
        return responder_comparacion(contexto, temporada, equipos)
    if contiene(texto, PALABRAS_VENTAJA_LOCAL) and len(equipos) <= 1:
        return responder_ventaja_local(contexto, temporada, equipos[0] if equipos else None)
    if not equipos and contiene(texto, PALABRAS_DESCENSO):
        return responder_descenso(contexto, temporada)
    if not equipos and contiene(texto, PALABRAS_RECORD):
        return responder_record(contexto, texto)
    if not equipos and contiene(texto, ["cuantos partidos"]) and not contiene(texto, ["gano", "perdi", "empat"]):
        return responder_partidos_jugados(contexto, temporada)
    if len(equipos) == 2 and not contiene(texto, PALABRAS_PROBABILIDAD):
        # Si no se escribió una temporada y no se enfrentaron en la elegida (o se pide el historial),
        # se buscan los partidos entre ellos en todas las temporadas.
        en_temporada = enfrentamientos(partidos_de_temporada(contexto["partidos"], temporada), *equipos)
        if contiene(texto, PALABRAS_HISTORIAL) or (temporada_escrita is None and en_temporada.empty):
            return responder_historial(contexto, equipos, temporada)
    if not equipos and contiene(texto, [" mas ", " menos ", "mejor defensa", "peor defensa"]) \
            and contiene(texto, ["equipo", "quien", "cual", "club"]) and " partido " not in texto:
        estadistica = estadistica_de_equipo(texto)
        if estadistica:
            return responder_ranking(contexto, temporada, estadistica, menor=" menos " in texto)
    if not equipos and contiene(texto, PALABRAS_TABLA) and "partido" not in texto:
        return responder_clasificacion(contexto, temporada)

    # Todo lo demás (resultados, enfrentamientos, resumen de un equipo...) lo responde el asistente de reglas.
    partidos_temporada = partidos_de_temporada(contexto["partidos"], temporada)
    resultado = asistente.responder(sin_temporada, partidos_temporada, temporada)
    if equipos:
        memoria["equipos"] = equipos
    if resultado["tipo"] == "ayuda":
        # Opcional: si hay un modelo de lenguaje configurado, se le pide que reescriba la pregunta
        # con palabras que las reglas entiendan. Él no calcula nada: solo interpreta.
        interprete = contexto.get("interprete")
        if interprete is not None:
            reescrita = interprete(pregunta, sorted(contexto["estadisticas"]["Equipo"].unique()), temporadas)
            if reescrita:
                contexto_sin_interprete = dict(contexto, interprete=None)
                segunda = responder_chat(reescrita, contexto_sin_interprete)
                if segunda["tipo"] != "ayuda":
                    segunda["texto"] = f"*(Entendí: «{reescrita}»)*\n\n" + segunda["texto"]
                return segunda
        return respuesta("No entendí la pregunta. Puedes preguntar, por ejemplo:\n\n" +
                         "\n".join(f"- {ejemplo}" for ejemplo in EJEMPLOS_CHAT), "ayuda")
    return respuesta(resultado["texto"], resultado["tipo"], tabla=resultado["tabla"],
                     fuente=fuente_estadisticas(contexto, temporada))


# ---------------------------------------------------------------------------
# Estadísticas
# ---------------------------------------------------------------------------
def estadistica_de_equipo(texto):
    for palabras, datos in ESTADISTICAS_EQUIPO:
        if contiene(texto, palabras):
            return datos
    return None


def responder_ranking(contexto, temporada, estadistica, menor=False):
    """Los equipos con más (o menos) de una estadística en la temporada."""
    nombre, columna = estadistica
    tabla = contexto["estadisticas"]
    tabla = tabla[(tabla["Temporada"] == temporada) & (tabla["Condicion"] == "Total")].copy()
    tabla["Tarjetas"] = tabla["Amarillas"] + tabla["Rojas"]
    tabla = tabla.sort_values(columna, ascending=menor, kind="stable")
    tabla = tabla[["Equipo", "PJ", columna]].rename(columns={columna: nombre}).reset_index(drop=True)
    tabla[nombre] = tabla[nombre].astype(int)
    mejor = tabla[nombre].iloc[0]
    lideres = tabla.loc[tabla[nombre] == mejor, "Equipo"].tolist()
    palabra = "menos" if menor else "más"
    en_curso = temporada_en_curso(contexto, temporada)
    if len(lideres) == 1:
        sujeto, verbo = "el equipo", ("es" if en_curso else "fue")
    else:
        sujeto, verbo = "los equipos", ("son" if en_curso else "fueron")
    hasta_ahora = " hasta ahora" if en_curso else ""
    texto = (f"En {temporada}{hasta_ahora}, {sujeto} con {palabra} {nombre.lower()} {verbo} "
             f"**{' y '.join(lideres)}**, con **{mejor}**.")
    primeros = tabla.head(5)
    return respuesta(texto, "ranking", tabla=primeros,
                     tarjetas=[(f"{palabra.capitalize()} {nombre.lower()} · {temporada}", " y ".join(lideres),
                                f"{mejor} en {int(tabla['PJ'].iloc[0])} partidos")],
                     grafico={"datos": primeros, "etiqueta": "Equipo", "valor": nombre,
                              "titulo": f"{nombre}: los cinco primeros · {temporada}"},
                     fuente=fuente_estadisticas(contexto, temporada))


def responder_clasificacion(contexto, temporada):
    tabla = contexto["estadisticas"]
    tabla = calcular_clasificacion(tabla[(tabla["Temporada"] == temporada) & (tabla["Condicion"] == "Total")])
    tabla = tabla[["Posicion", "Equipo", "PJ", "V", "E", "D", "DG", "Puntos"]].rename(
        columns={"Posicion": "Pos", "Puntos": "Pts"})
    lider = tabla.iloc[0]
    en_curso = int(tabla["PJ"].min()) < 38
    palabra = "va primero" if en_curso else "fue campeón"
    texto = (f"En {temporada}, **{lider['Equipo']}** {palabra} con **{int(lider['Pts'])} puntos** "
             f"en {int(lider['PJ'])} partidos (puntos ganados en el campo).")
    return respuesta(texto, "clasificacion", tabla=tabla,
                     tarjetas=[("Líder" if en_curso else "Campeón", lider["Equipo"], f"{int(lider['Pts'])} puntos")],
                     fuente=fuente_estadisticas(contexto, temporada))


def responder_comparacion(contexto, temporada, equipos):
    equipo_a, equipo_b = equipos
    contexto["memoria"]["equipos"] = equipos
    equipos_temporada = set(contexto["estadisticas"].loc[contexto["estadisticas"]["Temporada"] == temporada, "Equipo"])
    fuera = [equipo for equipo in equipos if equipo not in equipos_temporada]
    if fuera:
        return respuesta(f"{' y '.join(fuera)} no jugó la Premier League en {temporada}, así que no se puede "
                         "comparar en esa temporada.", "sin_datos")
    tabla = comparador.tabla_comparacion(contexto["estadisticas"], temporada, equipo_a, equipo_b)
    gana_a = int((tabla["Más alto"] == equipo_a).sum())
    gana_b = int((tabla["Más alto"] == equipo_b).sum())
    fila_puntos = tabla.set_index("Estadística").loc["Puntos"]
    puntos = {equipo: int(fila_puntos[equipo]) for equipo in equipos}
    texto = (f"En {temporada}, **{equipo_a}** sumó **{puntos[equipo_a]} puntos** y **{equipo_b}** "
             f"**{puntos[equipo_b]}**. De {len(tabla)} estadísticas, {equipo_a} tiene el valor más alto en "
             f"{gana_a} y {equipo_b} en {gana_b} (más alto no siempre es mejor: también cuentan goles "
             "recibidos, derrotas, faltas y tarjetas).")
    return respuesta(texto, "comparacion", tabla=comparador.para_mostrar(tabla, [equipo_a, equipo_b]),
                     tarjetas=[(equipo_a, f"{puntos[equipo_a]} puntos", f"más alto en {gana_a} estadísticas"),
                               (equipo_b, f"{puntos[equipo_b]} puntos", f"más alto en {gana_b} estadísticas")],
                     fuente=fuente_estadisticas(contexto, temporada))


# ---------------------------------------------------------------------------
# Calendario y predicciones
# ---------------------------------------------------------------------------
def pendientes_actuales(contexto):
    """Partidos pendientes de la temporada más reciente y el nombre de esa temporada."""
    temporada = sorted(contexto["partidos"]["Temporada"].unique())[-1]
    jugados = partidos_de_temporada(contexto["partidos"], temporada)
    return cal.partidos_pendientes(cal.cargar_calendario(temporada), jugados), temporada


def responder_proximo(contexto, equipos):
    pendientes, temporada = pendientes_actuales(contexto)
    fuente = f"Calendario: fixturedownload.com · temporada {temporada}. Las fechas pueden cambiar."
    if pendientes.empty:
        return respuesta(f"No hay partidos pendientes en el calendario de {temporada}.", "sin_datos")
    if not equipos:
        tabla = tabla_de_pendientes(cal.proximos_partidos(pendientes, dias=7))
        return respuesta(f"Estos son los próximos partidos de {temporada}:", "calendario", tabla=tabla, fuente=fuente)
    equipo = equipos[0]
    contexto["memoria"]["equipos"] = [equipo]
    fila = cal.proximo_partido_de(pendientes, equipo)
    if fila is None:
        return respuesta(f"{equipo} no tiene partidos pendientes en el calendario de {temporada}.", "sin_datos")
    condicion = "en casa" if fila["HomeTeam"] == equipo else "de visitante"
    texto = (f"El próximo partido de **{equipo}** es **{fila['HomeTeam']} vs. {fila['AwayTeam']}**, "
             f"{condicion}, el {cal.fecha_y_hora_texto(fila['FechaUTC'])} (jornada {int(fila['Jornada'])}).")
    return respuesta(texto, "calendario",
                     tarjetas=[("Local", fila["HomeTeam"], ""),
                               (f"Jornada {int(fila['Jornada'])}", "VS", cal.fecha_y_hora_texto(fila["FechaUTC"])),
                               ("Visitante", fila["AwayTeam"], "")],
                     fuente=fuente)


def tabla_de_pendientes(pendientes):
    return pd.DataFrame({
        "Jornada": pendientes["Jornada"].astype(int),
        "Fecha": [cal.fecha_y_hora_texto(fecha) for fecha in pendientes["FechaUTC"]],
        "Local": pendientes["HomeTeam"], "Visitante": pendientes["AwayTeam"],
    })


def partido_a_predecir(contexto, equipos):
    """Decide qué partido predecir: (local, visitante, fecha, descripción) o un texto de error."""
    pendientes, temporada = pendientes_actuales(contexto)
    equipos_actuales = set(contexto["partidos"].loc[contexto["partidos"]["Temporada"] == temporada, "HomeTeam"])
    fuera = [equipo for equipo in equipos if equipo not in equipos_actuales]
    if fuera:
        return f"{' y '.join(fuera)} no juega la Premier League en {temporada}: no hay datos recientes para predecir."
    dia_siguiente = contexto["partidos"]["Date"].max() + pd.Timedelta(days=1)

    if len(equipos) == 1:
        fila = cal.proximo_partido_de(pendientes, equipos[0]) if not pendientes.empty else None
        if fila is None:
            return f"{equipos[0]} no tiene un próximo partido en el calendario de {temporada}."
        return (fila["HomeTeam"], fila["AwayTeam"], fila["Fecha"],
                f"jornada {int(fila['Jornada'])}, {cal.fecha_y_hora_texto(fila['FechaUTC'])}")
    local, visitante = equipos
    if not pendientes.empty:
        entre_ellos = pendientes[pendientes["HomeTeam"].isin(equipos) & pendientes["AwayTeam"].isin(equipos)]
        if not entre_ellos.empty:
            fila = entre_ellos.iloc[0]
            return (fila["HomeTeam"], fila["AwayTeam"], fila["Fecha"],
                    f"jornada {int(fila['Jornada'])}, {cal.fecha_y_hora_texto(fila['FechaUTC'])}")
    return (local, visitante, dia_siguiente,
            "simulación hipotética: no está en el calendario pendiente; se toma como local al primero que nombraste")


def responder_probabilidades(contexto, equipos):
    if not equipos:
        return respuesta("¿De qué equipo o de qué partido quieres las probabilidades? Por ejemplo: "
                         "«probabilidades del Chelsea» o «probabilidades Arsenal vs Liverpool».", "aclaracion")
    if len(equipos) > 2:
        return respuesta("Nombra uno o dos equipos para calcular las probabilidades de un partido.", "aclaracion")
    partido = partido_a_predecir(contexto, equipos)
    if isinstance(partido, str):
        return respuesta(partido, "sin_datos")
    local, visitante, fecha, descripcion = partido
    servicio = contexto["servicio_modelo"]()
    prediccion = predecir_partido(servicio["modelo"], servicio["historial"], local, visitante, fecha)
    contexto["memoria"]["equipos"] = equipos
    contexto["memoria"]["ultima_prediccion"] = prediccion
    p = prediccion["probabilidades"]
    texto = (f"**{local} vs. {visitante}** ({descripcion}). El modelo estima: victoria de {local} "
             f"**{porcentaje(p['H'])}**, empate **{porcentaje(p['D'])}** y victoria de {visitante} "
             f"**{porcentaje(p['A'])}**.")
    if len(equipos) == 1:
        propia = p["H"] if equipos[0] == local else p["A"]
        texto += f" Es decir, **{equipos[0]}** gana con una probabilidad estimada de **{porcentaje(propia)}**."
    if prediccion["datos_insuficientes"]:
        texto += (" Aviso: uno de los equipos tiene menos de 5 partidos recientes en los datos, así que "
                  "esta estimación es menos fiable.")
    return respuesta(texto, "prediccion", fuente=fuente_modelo(contexto),
                     probabilidades={"local": local, "visitante": visitante, "H": p["H"], "D": p["D"], "A": p["A"]})


def responder_por_que(contexto, equipos):
    memoria = contexto["memoria"]
    if equipos and len(equipos) <= 2:
        calculada = responder_probabilidades(contexto, equipos)       # deja la predicción en la memoria
        if calculada["tipo"] != "prediccion":
            return calculada
    prediccion = memoria.get("ultima_prediccion")
    if prediccion is None:
        return respuesta("Primero pide una predicción (por ejemplo, «probabilidades del Chelsea») y luego "
                         "pregunta por qué.", "aclaracion")
    servicio = contexto["servicio_modelo"]()
    tabla = explicar_prediccion(servicio["modelo"], prediccion)
    principales = tabla[tabla["Favorece a"] != "Casi no influye"].head(3)
    frases = [f"{fila['Variable'].lower()} (favorece a {fila['Favorece a']})" for _, fila in principales.iterrows()]
    texto = (f"Para **{prediccion['local']} vs. {prediccion['visitante']}** el modelo compara lo que hizo cada "
             f"equipo en sus partidos anteriores. Lo que más pesa en esta estimación: {'; '.join(frases)}.")
    if ventaja_local_del_modelo(servicio["modelo"]):
        texto += (" Además, con todo lo demás igual, el modelo le da más opciones al local que al visitante, "
                  "porque así pasó en los partidos con los que se entrenó.")
    p = prediccion["probabilidades"]
    return respuesta(texto, "explicacion", tabla=tabla, fuente=fuente_modelo(contexto),
                     probabilidades={"local": prediccion["local"], "visitante": prediccion["visitante"],
                                     "H": p["H"], "D": p["D"], "A": p["A"]})


def responder_confiabilidad(contexto):
    evaluacion = contexto.get("evaluacion")
    if not evaluacion:
        return respuesta("Todavía no hay una evaluación guardada del modelo (se genera con "
                         "`python -m src.entrenar_modelo`).", "sin_datos")
    prueba = evaluacion["prueba"]
    modelo, baseline = prueba["modelo"], prueba["baseline"]
    empates = modelo["por_clase"][NOMBRES_CLASES["D"]]
    texto = (f"Con moderación. En {modelo['partidos']} partidos que el modelo no había visto "
             f"({fecha_texto(prueba['prueba']['desde'])} a {fecha_texto(prueba['prueba']['hasta'])}) acertó el "
             f"resultado en el **{porcentaje(modelo['accuracy'])}** de los casos. Decir siempre «gana el local» "
             f"acierta el {porcentaje(baseline['accuracy'])}. El modelo mejora esa referencia, pero se equivoca "
             f"en cerca de la mitad de los partidos y casi nunca predice empates (lo hizo "
             f"{empates['veces_predicho']} veces, y hubo {empates['partidos_reales']}). "
             "Sirve para comparar probabilidades, no para saber quién va a ganar.")
    tabla = pd.DataFrame([
        {"Métrica": "Accuracy (aciertos)", "Modelo": round(modelo["accuracy"], 3), "Baseline": round(baseline["accuracy"], 3)},
        {"Métrica": "Balanced accuracy", "Modelo": round(modelo["balanced_accuracy"], 3),
         "Baseline": round(baseline["balanced_accuracy"], 3)},
        {"Métrica": "Log loss (menor es mejor)", "Modelo": round(modelo["log_loss"], 3), "Baseline": round(baseline["log_loss"], 3)},
        {"Métrica": "Brier (menor es mejor)", "Modelo": round(modelo["brier"], 3), "Baseline": round(baseline["brier"], 3)},
    ])
    return respuesta(texto, "confiabilidad", tabla=tabla,
                     tarjetas=[("Aciertos del modelo", porcentaje(modelo["accuracy"]), f"{modelo['partidos']} partidos de prueba"),
                               ("Referencia (baseline)", porcentaje(baseline["accuracy"]), "frecuencias históricas"),
                               ("Log loss", f"{modelo['log_loss']:.3f}".replace(".", ","),
                                f"baseline {baseline['log_loss']:.3f}".replace(".", ","))],
                     fuente=f"{evaluacion['modelo']} · {evaluacion['version']} · validación cronológica")


# ---------------------------------------------------------------------------
# Saludos y ayuda
# ---------------------------------------------------------------------------
QUE_PUEDO_RESPONDER = (
    "- **Tabla y resultados:** «¿quién va primero?», «¿quién ganó la liga 2024/25?», «¿quién descendió en 2025/26?», "
    "«¿cómo va el Liverpool?», «Arsenal contra Tottenham».\n"
    "- **Estadísticas:** «¿qué equipo tuvo más tiros al arco?», «compara Arsenal y Liverpool», "
    "«ventaja de local», «récord de puntos».\n"
    "- **Jugadores:** «¿quién es el máximo goleador?», «asistencias de Bruno Fernandes», "
    "«¿quién crees que marque en el próximo partido del City?».\n"
    "- **Predicciones:** «probabilidades del Chelsea», «¿por qué?», «¿qué tan confiable es el modelo?», "
    "«próximos partidos».")


def responder_charla(texto):
    """Saludos, agradecimientos y "¿qué puedes hacer?". Devuelve None si la pregunta es otra cosa."""
    palabras = texto.split()
    if palabras and all(palabra in SALUDOS for palabra in palabras) and contiene(texto, ["hola", "holi", "buen", "hey",
                                                                                      "saludos", "hello", " hi "]):
        return respuesta("¡Hola! Soy el asistente de *Más allá de la tabla*. Respondo con los datos del proyecto "
                         "(siete temporadas de la Premier League) y con el modelo predictivo. Puedes preguntar, "
                         "por ejemplo:\n\n" + QUE_PUEDO_RESPONDER, "ayuda")
    if contiene(texto, ["gracias", "genial", "perfecto", "excelente"]) and len(palabras) <= 4:
        return respuesta("¡Con gusto! Si quieres, pregunta por otro equipo, jugador o partido.", "ayuda")
    if contiene(texto, PALABRAS_AYUDA) and len(palabras) <= 8:
        return respuesta("Puedo responder preguntas como estas:\n\n" + QUE_PUEDO_RESPONDER, "ayuda")
    return None


# ---------------------------------------------------------------------------
# Jugadores
# ---------------------------------------------------------------------------
def fuente_jugadores(contexto, temporada, asistencias=False):
    """Fuente de la tabla de goleadores (o asistentes) de la temporada y la fecha de consulta."""
    _, _, fuentes = datos_de_jugadores(contexto)
    datos = fuentes.get("temporadas", {}).get(temporada, {})
    origen = datos.get("asistencias" if asistencias else "goleadores", {}).get("fuente", "ESPN")
    consulta = datos.get("fecha_consulta", fuentes.get("fecha_consulta", ""))
    texto = f"Fuente: {origen} · temporada {temporada} · consulta del {fecha_texto(consulta)}" if consulta else \
        f"Fuente: {origen} · temporada {temporada}"
    if datos.get("nota"):
        texto += f". {datos['nota']}"
    return texto


def responder_lideres_jugadores(contexto, temporada, asistencias=False, equipo=None):
    """Máximos goleadores (o asistentes) de una temporada, o los de un equipo."""
    goleadores, tabla_asistencias, _ = datos_de_jugadores(contexto)
    tabla, columna, nombre = ((tabla_asistencias, "Asistencias", "asistente") if asistencias
                              else (goleadores, "Goles", "goleador"))
    orden = ranking(tabla, temporada, columna)
    if orden.empty:
        return respuesta(f"No tengo la tabla de {nombre}es de {temporada}.", "sin_datos")
    en_curso = temporada_en_curso(contexto, temporada)
    mostrar = orden[["Posicion", "Jugador", "Equipo", "Partidos", columna]].rename(columns={"Posicion": "Pos"})
    mostrar["Partidos"] = mostrar["Partidos"].astype("Int64")
    if equipo:
        del_equipo = orden[orden["EquipoCorto"] == equipo]
        if del_equipo.empty:
            return respuesta(f"Ningún jugador de {equipo} aparece entre los máximos {nombre}es de {temporada} "
                             f"(la tabla solo tiene los primeros {len(orden)}).", "sin_datos",
                             fuente=fuente_jugadores(contexto, temporada, asistencias))
        lineas = [f"**{fila['Jugador']}** ({int(fila[columna])})" for _, fila in del_equipo.iterrows()]
        return respuesta(f"Jugadores de {equipo} entre los máximos {nombre}es de {temporada}: "
                         f"{', '.join(lineas)}.", "jugadores",
                         tabla=mostrar[orden["EquipoCorto"] == equipo].reset_index(drop=True),
                         fuente=fuente_jugadores(contexto, temporada, asistencias))
    primeros = lideres(orden)
    nombres = " y ".join(f"**{jugador}** ({equipo_})" for jugador, equipo_ in zip(primeros["Jugador"], primeros["Equipo"]))
    cantidad = int(primeros[columna].iloc[0])
    unidad = plural(cantidad, columna.lower()[:-1], columna.lower())
    if en_curso:
        texto = f"En {temporada} (temporada en curso), va primero {nombres}, con **{cantidad} {unidad}**."
    else:
        texto = f"El máximo {nombre} de {temporada} fue {nombres}, con **{cantidad} {unidad}**."
    grafico_datos = orden.head(10)[["Jugador", columna]].copy()
    return respuesta(texto, "jugadores", tabla=mostrar.head(10),
                     tarjetas=[(f"Máximo {nombre} · {temporada}", " y ".join(primeros["Jugador"]),
                                f"{cantidad} {unidad}")],
                     grafico={"datos": grafico_datos, "etiqueta": "Jugador", "valor": columna,
                              "titulo": f"{columna} · {temporada}"},
                     fuente=fuente_jugadores(contexto, temporada, asistencias))


def responder_jugador(contexto, nombres, texto_pregunta=""):
    """Goles y asistencias de uno o más jugadores en todas las temporadas en que aparecen."""
    goleadores, asistencias, _ = datos_de_jugadores(contexto)
    filas = []
    for jugador in nombres[:3]:
        temporadas = sorted(set(goleadores.loc[goleadores["Jugador"] == jugador, "Temporada"]) |
                            set(asistencias.loc[asistencias["Jugador"] == jugador, "Temporada"]))
        for temporada in temporadas:
            gol = goleadores[(goleadores["Jugador"] == jugador) & (goleadores["Temporada"] == temporada)]
            asi = asistencias[(asistencias["Jugador"] == jugador) & (asistencias["Temporada"] == temporada)]
            fila = gol.iloc[0] if not gol.empty else asi.iloc[0]
            filas.append({"Jugador": jugador, "Temporada": temporada, "Equipo": fila["Equipo"],
                          "Partidos": None if pd.isna(fila["Partidos"]) else int(fila["Partidos"]),
                          "Goles": int(gol["Goles"].iloc[0]) if not gol.empty else None,
                          "Asistencias": int(asi["Asistencias"].iloc[0]) if not asi.empty else None})
    tabla = pd.DataFrame(filas)
    tabla[["Partidos", "Goles", "Asistencias"]] = tabla[["Partidos", "Goles", "Asistencias"]].astype("Int64")
    if len(nombres) > 3:
        texto_extra = f" (encontré {len(nombres)} jugadores con ese nombre; muestro los tres primeros)"
    else:
        texto_extra = ""
    # Qué dato se pregunta: asistencias, goles o los dos.
    if "asist" in texto_pregunta and "gol" not in texto_pregunta:
        columnas = ["Asistencias"]
    elif "gol" in texto_pregunta and "asist" not in texto_pregunta:
        columnas = ["Goles"]
    else:
        columnas = ["Goles", "Asistencias"]
    unidades = {"Goles": ("gol", "goles"), "Asistencias": ("asistencia", "asistencias")}
    partes = []
    for jugador in nombres[:3]:
        filas = tabla[tabla["Jugador"] == jugador]
        con_dato = filas.dropna(subset=columnas, how="all")
        if con_dato.empty:
            nombre_dato = " ni ".join(c.lower() for c in columnas)
            partes.append(f"**{jugador}** no aparece en las tablas de {nombre_dato}")
            continue
        ultima = con_dato.iloc[-1]
        datos = [f"{int(ultima[c])} {plural(int(ultima[c]), *unidades[c])}" for c in columnas if not pd.isna(ultima[c])]
        jugados = f" en {int(ultima['Partidos'])} partidos" if not pd.isna(ultima["Partidos"]) else ""
        partes.append(f"**{jugador}** ({ultima['Equipo']}): {' y '.join(datos)}{jugados} en {ultima['Temporada']}")
    texto = ("; ".join(partes) + f"{texto_extra}. La tabla muestra todas las temporadas en que aparece entre los "
             "máximos goleadores o asistentes (si falta una temporada, es porque no estuvo entre los primeros).")
    contexto["memoria"]["jugadores"] = nombres[:3]
    return respuesta(texto, "jugadores", tabla=tabla,
                     fuente="Fuente: tablas de goleadores y asistentes de ESPN, la Premier League y Wikipedia "
                            "(data/jugadores/fuentes.json).")


def es_pregunta_de_goleador_probable(texto):
    """«¿Quién crees que meta gol en el próximo partido?», «¿quién tiene más opciones de marcar?»."""
    futuro = contiene(texto, PALABRAS_FUTURO)
    if contiene(texto, ["mas goles", "maximo"]) and not futuro:
        return False                            # «¿quién marca más goles?» es una pregunta de estadísticas
    if VERBOS_GOL.search(texto):
        return True
    if contiene(texto, ["anotara", "marcara", "va a marcar", "va a anotar", "van a marcar", "van a anotar",
                        "quien marque", "quien anote"]):
        return True
    return contiene(texto, ["goleador", "anotar", "marcar", "anote", "marque", "anotara", "marcara"]) and futuro


def partido_para_goleadores(contexto, equipos):
    """Partido (local, visitante, texto de fecha, es_hipotetico) o un texto de error."""
    pendientes, temporada = pendientes_actuales(contexto)
    equipos_actuales = set(contexto["partidos"].loc[contexto["partidos"]["Temporada"] == temporada, "HomeTeam"])
    fuera = [equipo for equipo in equipos if equipo not in equipos_actuales]
    if fuera:
        return f"{' y '.join(fuera)} no juega la Premier League en {temporada}."
    if len(equipos) == 1:
        fila = cal.proximo_partido_de(pendientes, equipos[0]) if not pendientes.empty else None
        if fila is None:
            return f"{equipos[0]} no tiene partidos pendientes en el calendario de {temporada}."
        return (fila["HomeTeam"], fila["AwayTeam"],
                f"jornada {int(fila['Jornada'])}, {cal.fecha_y_hora_texto(fila['FechaUTC'])}", False)
    entre_ellos = pendientes[pendientes["HomeTeam"].isin(equipos) & pendientes["AwayTeam"].isin(equipos)] \
        if not pendientes.empty else pendientes
    if not entre_ellos.empty:
        fila = entre_ellos.iloc[0]
        return (fila["HomeTeam"], fila["AwayTeam"],
                f"jornada {int(fila['Jornada'])}, {cal.fecha_y_hora_texto(fila['FechaUTC'])}", False)
    return equipos[0], equipos[1], "partido hipotético", True


def formatear_goleadores(tabla):
    """Tabla para mostrar, con la probabilidad en porcentaje."""
    mostrar = tabla[["Jugador", "Equipo", "Rival", "Goles", "Partidos", "Goles por partido",
                     "Ajuste por rival"]].copy()
    mostrar["Probabilidad de marcar"] = [porcentaje(valor) for valor in tabla["Probabilidad de marcar"]]
    return mostrar


def equipo_actual_del_jugador(goleadores, jugador):
    """Equipo del jugador en la temporada más reciente en que aparece en la tabla de goleadores."""
    filas = goleadores[goleadores["Jugador"] == jugador].sort_values("Temporada")
    return None if filas.empty else filas["EquipoCorto"].iloc[-1]


def responder_goleador_probable(contexto, equipos, jugadores=None):
    """Jugadores con más opciones de marcar en un partido (o en la próxima jornada).

    El orden sale solo de los números (goles por partido del jugador y goles que recibe el
    rival): no hay ninguna lista de jugadores "importantes" ni ajustes a mano.
    """
    goleadores, _, _ = datos_de_jugadores(contexto)
    estadisticas = contexto["estadisticas"]
    pendientes, temporada = pendientes_actuales(contexto)
    jugador_pedido = None
    if jugadores and not equipos:
        con_goles = [j for j in jugadores if equipo_actual_del_jugador(goleadores, j)]
        if not con_goles:
            return respuesta(f"{jugadores[0]} no aparece en las tablas de goleadores, así que no tengo sus goles "
                             "por partido para estimarlo.", "sin_datos")
        jugador_pedido = con_goles[0]
        equipos = [equipo_actual_del_jugador(goleadores, jugador_pedido)]
    fuente = (f"{goleadores_probables.NOMBRE_METODO}. Datos de jugadores: tablas de goleadores (ESPN) de "
              f"{goleadores_probables.temporada_anterior(temporada, estadisticas['Temporada'].unique()) or ''} y "
              f"{temporada}; equipos: Football-Data.co.uk hasta el {fecha_texto(contexto['partidos']['Date'].max())}. "
              "Es una estimación sencilla, no una certeza ni una recomendación de apuestas.")
    aviso = ("No conoce alineaciones, lesiones, sanciones ni quién tira los penales, y solo puede nombrar a "
             "jugadores que están en las tablas de máximos goleadores (unos 10 a 16 por temporada).")
    if len(equipos) > 2:
        return respuesta("Nombra uno o dos equipos para estimar quién puede marcar.", "aclaracion")

    if not equipos:
        if pendientes.empty:
            return respuesta(f"No hay partidos pendientes en el calendario de {temporada}.", "sin_datos")
        jornada = int(pendientes["Jornada"].iloc[0])
        partidos_jornada = pendientes[pendientes["Jornada"] == jornada]
        tablas = []
        for _, fila in partidos_jornada.iterrows():
            for equipo, rival in [(fila["HomeTeam"], fila["AwayTeam"]), (fila["AwayTeam"], fila["HomeTeam"])]:
                tablas.append(goleadores_probables.estimar(goleadores, estadisticas, temporada, equipo, rival)[0])
        tabla = pd.concat(tablas, ignore_index=True).sort_values("Probabilidad de marcar", ascending=False,
                                                                 kind="stable").head(10).reset_index(drop=True)
        if tabla.empty:
            return respuesta("Ningún jugador de los equipos de la próxima jornada aparece en las tablas de "
                             "goleadores.", "sin_datos")
        mejor = tabla.iloc[0]
        texto = (f"Para la **jornada {jornada}**, solo con estadísticas, el jugador con más opciones de marcar es "
                 f"**{mejor['Jugador']}** ({mejor['Equipo']} contra {mejor['Rival']}): "
                 f"**{porcentaje(mejor['Probabilidad de marcar'])}** de marcar al menos un gol si juega. {aviso}")
        return respuesta_goleadores(texto, tabla, fuente)

    partido = partido_para_goleadores(contexto, equipos)
    if isinstance(partido, str):
        return respuesta(partido, "sin_datos")
    local, visitante, descripcion, hipotetico = partido
    contexto["memoria"]["equipos"] = equipos
    pedidos = equipos if len(equipos) == 1 else [local, visitante]
    tablas, sin_jugadores, notas = [], [], []
    for equipo in pedidos:
        rival = visitante if equipo == local else local
        tabla_equipo, origen = goleadores_probables.estimar(goleadores, estadisticas, temporada, equipo, rival)
        if tabla_equipo.empty:
            sin_jugadores.append(equipo)
        elif origen != temporada:
            notas.append(f"{equipo} no tiene jugadores en la tabla de goleadores de {temporada}, así que se usan "
                         f"sus goleadores de {origen} (puede que alguno ya no esté en el club)")
        tablas.append(tabla_equipo)
    tabla = pd.concat(tablas, ignore_index=True).sort_values("Probabilidad de marcar", ascending=False,
                                                             kind="stable").reset_index(drop=True)
    encabezado = f"**{local} vs. {visitante}** ({descripcion})."
    if tabla.empty:
        return respuesta(f"{encabezado} Ningún jugador de {' ni de '.join(sin_jugadores)} aparece en las tablas "
                         "de máximos goleadores, así que no puedo estimar quién marcará sin inventar datos.",
                         "sin_datos", fuente=fuente)
    mejor = tabla.iloc[0]
    texto = (f"{encabezado} Solo con estadísticas (goles por partido de cada jugador y goles que recibe el rival), "
             f"quien tiene más opciones de marcar es **{mejor['Jugador']}** ({mejor['Equipo']}): "
             f"**{porcentaje(mejor['Probabilidad de marcar'])}** de marcar al menos un gol si juega.")
    if jugador_pedido and jugador_pedido in set(tabla["Jugador"]):
        fila = tabla[tabla["Jugador"] == jugador_pedido].iloc[0]
        por_partido = f"{fila['Goles por partido']:.2f}".replace(".", ",")
        ajuste = f"{fila['Ajuste por rival']:.2f}".replace(".", ",")
        texto = (f"{encabezado} **{jugador_pedido}** tiene una probabilidad estimada de "
                 f"**{porcentaje(fila['Probabilidad de marcar'])}** de marcar al menos un gol si juega: "
                 f"{fila['Goles']} goles en {fila['Partidos']} partidos ({por_partido} por partido) y un ajuste "
                 f"por rival de {ajuste}.")
    if sin_jugadores:
        texto += f" De {' y '.join(sin_jugadores)} no hay jugadores en las tablas de goleadores."
    if notas:
        texto += " " + ". ".join(notas) + "."
    texto += f" {aviso}"
    return respuesta_goleadores(texto, tabla, fuente)


def respuesta_goleadores(texto, tabla, fuente):
    grafico = pd.DataFrame({"Jugador": tabla["Jugador"],
                            "Probabilidad (%)": (100 * tabla["Probabilidad de marcar"]).round(1)})
    tarjetas = [(f"{fila['Jugador']}", porcentaje(fila["Probabilidad de marcar"]),
                 f"{fila['Equipo']} · {fila['Goles']} goles en {fila['Partidos']} partidos")
                for _, fila in tabla.head(3).iterrows()]
    return respuesta(texto, "goleador_probable", tabla=formatear_goleadores(tabla), tarjetas=tarjetas,
                     grafico={"datos": grafico, "etiqueta": "Jugador", "valor": "Probabilidad (%)",
                              "titulo": "Probabilidad estimada de marcar al menos un gol"},
                     fuente=fuente)


# ---------------------------------------------------------------------------
# Historial, descenso, récords y otras preguntas de la liga
# ---------------------------------------------------------------------------
def responder_historial(contexto, equipos, temporada_elegida):
    """Todos los partidos entre dos equipos en las temporadas del proyecto."""
    equipo_a, equipo_b = equipos
    contexto["memoria"]["equipos"] = equipos
    tabla = enfrentamientos(contexto["partidos"], equipo_a, equipo_b)
    temporadas = sorted(contexto["partidos"]["Temporada"].unique())
    if tabla.empty:
        return respuesta(f"{equipo_a} y {equipo_b} no se enfrentaron en la Premier League entre {temporadas[0]} y "
                         f"{temporadas[-1]}.", "sin_datos")
    ganadores = [ganador(fila) for _, fila in tabla.iterrows()]
    gana_a, gana_b, empates = ganadores.count(equipo_a), ganadores.count(equipo_b), ganadores.count(None)
    ultimo = tabla.iloc[-1]
    aviso = ""
    if ultimo["Temporada"] != temporada_elegida:
        aviso = f"En {temporada_elegida} todavía no se han enfrentado. "
    texto = (f"{aviso}Entre {temporadas[0]} y {temporadas[-1]} jugaron **{len(tabla)}** "
             f"{plural(len(tabla), 'vez', 'veces')}: {equipo_a} ganó **{gana_a}**, {equipo_b} ganó **{gana_b}** "
             f"y empataron **{empates}**. El último fue el {fecha_texto(ultimo['Date'])}: "
             f"**{ultimo['HomeTeam']} {int(ultimo['FTHG'])}-{int(ultimo['FTAG'])} {ultimo['AwayTeam']}**.")
    mostrar = tabla_resumen(tabla.iloc[::-1])
    mostrar.insert(0, "Temporada", list(tabla["Temporada"].iloc[::-1]))
    return respuesta(texto, "partidos", tabla=mostrar,
                     tarjetas=[(equipo_a, str(gana_a), plural(gana_a, "victoria", "victorias")),
                               ("Empates", str(empates), f"en {len(tabla)} partidos"),
                               (equipo_b, str(gana_b), plural(gana_b, "victoria", "victorias"))],
                     fuente=f"Fuente: Football-Data.co.uk · {temporadas[0]} a {temporadas[-1]}")


def responder_descenso(contexto, temporada):
    tabla = contexto["estadisticas"]
    tabla = calcular_clasificacion(tabla[(tabla["Temporada"] == temporada) & (tabla["Condicion"] == "Total")])
    ultimos = tabla.tail(3)
    nombres = ", ".join(ultimos["Equipo"].iloc[:-1]) + " y " + ultimos["Equipo"].iloc[-1]
    if temporada_en_curso(contexto, temporada):
        texto = (f"{temporada} sigue en curso. Ahora mismo, en zona de descenso están **{nombres}** "
                 "(puestos 18 a 20).")
    else:
        texto = f"En {temporada} descendieron **{nombres}** (puestos 18 a 20 por puntos ganados en el campo)."
    mostrar = ultimos[["Posicion", "Equipo", "PJ", "V", "E", "D", "DG", "Puntos"]].rename(
        columns={"Posicion": "Pos", "Puntos": "Pts"})
    return respuesta(texto, "clasificacion", tabla=mostrar.reset_index(drop=True),
                     fuente=fuente_estadisticas(contexto, temporada))


def responder_partidos_jugados(contexto, temporada):
    partidos = contexto["partidos"]
    en_temporada = len(partidos_de_temporada(partidos, temporada))
    temporadas = sorted(partidos["Temporada"].unique())
    total = f"{len(partidos):,}".replace(",", ".")          # 2380 -> "2.380"
    texto = (f"En {temporada} se han jugado **{en_temporada}** de 380 partidos. En total, los datos del proyecto "
             f"tienen **{total}** partidos ({temporadas[0]} a {temporadas[-1]}).")
    conteo = partidos.groupby("Temporada").size().reset_index(name="Partidos")
    return respuesta(texto, "temporada", tabla=conteo, fuente=fuente_estadisticas(contexto, temporada))


def responder_ventaja_local(contexto, temporada, equipo=None):
    """Cuánto ayuda jugar en casa: a la liga o a un equipo."""
    estadisticas = contexto["estadisticas"]
    if equipo:
        if equipo not in set(estadisticas.loc[estadisticas["Temporada"] == temporada, "Equipo"]):
            return respuesta(f"{equipo} no jugó la Premier League en {temporada}.", "sin_datos")
        frases = comparador.conclusiones_local_visitante(estadisticas, temporada, equipo)
        tabla = comparador.tabla_local_visitante(estadisticas, temporada, equipo)
        return respuesta(" ".join(frases), "comparacion", tabla=tabla, fuente=fuente_estadisticas(contexto, temporada))
    partidos = partidos_de_temporada(contexto["partidos"], temporada)
    local, empate, visitante = [int((partidos["FTR"] == r).sum()) for r in ["H", "D", "A"]]
    por_condicion = estadisticas[(estadisticas["Temporada"] == temporada)]
    puntos = {c: por_condicion.loc[por_condicion["Condicion"] == c, "Puntos"].sum() /
              por_condicion.loc[por_condicion["Condicion"] == c, "PJ"].sum() for c in ["Local", "Visitante"]}
    diferencia = puntos["Local"] - puntos["Visitante"]

    def decimal(valor):
        return f"{valor:.2f}".replace(".", ",")              # 1.53 -> "1,53"

    texto = (f"En {temporada}, de {len(partidos)} partidos, **{local}** los ganó el local, **{empate}** terminaron "
             f"empatados y **{visitante}** los ganó el visitante. Los equipos sumaron {decimal(puntos['Local'])} "
             f"puntos por partido en casa y {decimal(puntos['Visitante'])} fuera")
    if diferencia > 0:
        texto += f": jugar en casa dio **{decimal(diferencia)} puntos más** por partido."
    else:
        texto += ": esa temporada no hubo ventaja de jugar en casa."
    tabla = pd.DataFrame({"Resultado": ["Gana el local", "Empate", "Gana el visitante"],
                          "Partidos": [local, empate, visitante]})
    return respuesta(texto, "temporada", tabla=tabla,
                     tarjetas=[("Gana el local", str(local), "partidos"), ("Empates", str(empate), "partidos"),
                               ("Gana el visitante", str(visitante), "partidos")],
                     fuente=fuente_estadisticas(contexto, temporada))


def responder_record(contexto, texto):
    """Récords de todas las temporadas: de equipos en una temporada o de partidos."""
    estadistica = estadistica_de_equipo(texto)
    temporadas = sorted(contexto["partidos"]["Temporada"].unique())
    fuente = f"Fuente: Football-Data.co.uk · {temporadas[0]} a {temporadas[-1]}"
    if estadistica and " partido" not in texto:
        nombre, columna = estadistica
        menor = " menos " in texto
        tabla = contexto["estadisticas"].copy()
        tabla["Tarjetas"] = tabla["Amarillas"] + tabla["Rojas"]
        orden = records.ranking_una_temporada(tabla, columna, menor).head(5)
        mejor = orden.iloc[0]
        palabra = "menos" if menor else "más"
        texto_respuesta = (f"El récord de {palabra} {nombre.lower()} en una temporada (de {temporadas[0]} a "
                           f"{temporadas[-1]}) es de **{mejor['Equipo']}** en {mejor['Temporada']}, con "
                           f"**{int(mejor[columna])}**.")
        if menor:
            texto_respuesta += " Ojo: la temporada en curso tiene menos partidos, así que puede aparecer arriba."
        return respuesta(texto_respuesta, "ranking", tabla=orden.rename(columns={columna: nombre}), fuente=fuente)
    lista = records.records_de_partidos(contexto["partidos"])
    lineas = [f"- **{r['titulo']}:** {r['valor']}. {r['texto']}" for r in lista]
    return respuesta(f"Récords de partidos de {temporadas[0]} a {temporadas[-1]}:\n\n" + "\n".join(lineas),
                     "partidos", fuente=fuente)


def responder_baseline(contexto):
    evaluacion = contexto.get("evaluacion")
    if not evaluacion:
        return respuesta("Todavía no hay una evaluación guardada del modelo.", "sin_datos")
    baseline = evaluacion["prueba"]["baseline"]
    modelo = evaluacion["prueba"]["modelo"]
    texto = ("El **baseline** es la referencia con la que se compara el modelo: da a todos los partidos las "
             "mismas probabilidades, las frecuencias de victoria local, empate y victoria visitante de los "
             "partidos de entrenamiento. Como el resultado más frecuente es que gane el local, siempre «predice» "
             f"victoria local. En la prueba acierta el **{porcentaje(baseline['accuracy'])}** y el modelo el "
             f"**{porcentaje(modelo['accuracy'])}**: el modelo solo sirve si mejora esta referencia.")
    return respuesta(texto, "confiabilidad", fuente=f"{evaluacion['modelo']} · {evaluacion['version']}")
