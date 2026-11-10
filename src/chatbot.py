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

from src import asistente, calendario as cal, comparador
from src.equipos import normalizar
from src.estadisticas import calcular_clasificacion
from src.modelo import (NOMBRE_MODELO, NOMBRES_CLASES, explicar_prediccion, predecir_partido,
                        ventaja_local_del_modelo)
from src.partidos import fecha_texto, partidos_de_temporada

EJEMPLOS_CHAT = [
    "¿Quién ganó más partidos en 2025/26?",
    "Compara Arsenal y Liverpool",
    "¿Cuál es el próximo partido del Manchester City?",
    "¿Qué probabilidades tiene el Chelsea de ganar su siguiente encuentro?",
    "¿Por qué el modelo estima esas probabilidades?",
    "¿Qué tan confiable es el modelo?",
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
                  "primer lugar", "puntero", "lidera", "lider", "campeon"]


def respuesta(texto, tipo, tabla=None, tarjetas=None, probabilidades=None, grafico=None, fuente=None):
    """Empaqueta la respuesta del chatbot en un diccionario con siempre las mismas claves."""
    return {"tipo": tipo, "texto": texto, "tabla": tabla, "tarjetas": tarjetas,
            "probabilidades": probabilidades, "grafico": grafico, "fuente": fuente}


def porcentaje(valor):
    """0.4567 -> '45,7 %'."""
    return f"{100 * valor:.1f}".replace(".", ",") + " %"


def contiene(texto, palabras):
    return any(palabra in texto for palabra in palabras)


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

    temporada = temporada_mencionada(texto, temporadas) or contexto["temporada"]
    sin_temporada = re.sub(r"\d{2,4}\s?[/-]\s?\d{2,4}", " ", texto)     # para que "2025/26" no confunda
    if "manchester" in sin_temporada and not re.search(r"manchester (city|united|utd)", sin_temporada):
        return respuesta("¿Te refieres al **Manchester City** o al **Manchester United**? "
                         "Escribe el nombre completo.", "aclaracion")
    equipos = asistente.encontrar_equipos(sin_temporada)

    # Preguntas de seguimiento ("¿y por qué?", "¿y su próximo partido?"): se usan los equipos anteriores.
    es_seguimiento = not equipos and contiene(texto, [" su ", " sus ", " ese ", " esas ", " esos ", " y el ", " y la "])

    if contiene(texto, PALABRAS_CONFIABILIDAD) and contiene(texto, ["modelo", "prediccion", "pronostico", "confiable",
                                                                  "fiable", "acierta"]):
        return responder_confiabilidad(contexto)
    if "por que" in texto and (contiene(texto, ["modelo", "probabilidad", "estima", "prediccion", "pronostico"])
                               or "ultima_prediccion" in memoria):
        return responder_por_que(contexto, equipos)
    if contiene(texto, PALABRAS_PROBABILIDAD):
        return responder_probabilidades(contexto, equipos or (memoria.get("equipos", []) if es_seguimiento else []))
    if contiene(texto, PALABRAS_PROXIMO):
        return responder_proximo(contexto, equipos or (memoria.get("equipos", []) if es_seguimiento else []))
    if contiene(texto, PALABRAS_COMPARAR) and len(equipos) == 2:
        return responder_comparacion(contexto, temporada, equipos)
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
    verbo = "fue" if len(lideres) == 1 else "fueron"
    texto = (f"En {temporada}, el equipo con {palabra} {nombre.lower()} {verbo} "
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
