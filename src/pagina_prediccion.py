"""Sección «Analizador predictivo»: probabilidades de un partido y calidad del modelo.

Los números de esta página salen siempre del modelo (src/modelo.py) y de su
evaluación guardada (data/modelo/evaluacion.json); aquí solo se muestran.
"""

import pandas as pd
import streamlit as st

from src import calendario as cal
from src import graficos
from src.estilos import encabezado, tarjeta, tarjeta_partido
from src.modelo import CLASES, NOMBRE_MODELO, NOMBRES_CLASES, explicar_prediccion, predecir_partido
from src.partidos import fecha_texto, partidos_de_temporada
from src.variables_modelo import MINIMO_PARTIDOS

AVISO_PREDICCION = ("Estas probabilidades son **estimaciones estadísticas**, no certezas: el fútbol tiene mucho "
                    "azar y el modelo se equivoca a menudo. No son recomendaciones de apuestas.")


def html(texto):
    st.markdown(texto, unsafe_allow_html=True)


def porcentaje(valor, decimales=1):
    return f"{100 * valor:.{decimales}f}".replace(".", ",") + " %"


def pagina_prediccion(partidos, temporada, obtener_modelo, evaluacion):
    html(encabezado("Analizador predictivo",
                    f"Probabilidad de victoria local, empate y victoria visitante · {NOMBRE_MODELO.lower()}"))
    st.warning(AVISO_PREDICCION)

    temporada_actual = sorted(partidos["Temporada"].unique())[-1]
    if temporada != temporada_actual:
        st.caption(f"Las predicciones usan siempre la temporada más reciente ({temporada_actual}), aunque en la "
                   f"barra lateral esté elegida {temporada}.")
    jugados = partidos_de_temporada(partidos, temporada_actual)
    equipos = sorted(set(jugados["HomeTeam"]) | set(jugados["AwayTeam"]))
    pendientes = cal.partidos_pendientes(cal.cargar_calendario(temporada_actual), jugados)

    pestana_prediccion, pestana_calidad = st.tabs(["Predicción de un partido", "Calidad del modelo"])
    with pestana_prediccion:
        partido = elegir_partido(pendientes, equipos, temporada_actual, partidos["Date"].max())
        if partido is not None:
            with st.spinner("Preparando el modelo..."):
                servicio = obtener_modelo()
            mostrar_prediccion(servicio, partido)
    with pestana_calidad:
        mostrar_calidad(evaluacion)


# ---------------------------------------------------------------------------
# Selector de encuentros
# ---------------------------------------------------------------------------
def elegir_partido(pendientes, equipos, temporada, fecha_datos):
    """Devuelve el partido elegido como diccionario, o None si todavía no se puede predecir."""
    opciones = ["Próximos partidos del calendario", "Simulación hipotética"]
    modo = st.radio("Qué partido analizar", opciones, horizontal=True,
                    help="El calendario viene de fixturedownload.com. En la simulación eliges tú los dos equipos.")

    if modo == opciones[0]:
        if pendientes.empty:
            st.info(f"No hay partidos pendientes en el calendario de {temporada}. Usa la simulación hipotética.")
            return None
        izquierda, derecha = st.columns([1, 2])
        equipo = izquierda.selectbox("Equipo", ["Todos"] + equipos, key="equipo_prediccion")
        tabla = cal.proximos_partidos(pendientes)
        if equipo != "Todos":
            tabla = pendientes[(pendientes["HomeTeam"] == equipo) | (pendientes["AwayTeam"] == equipo)].head(5)
        if tabla.empty:
            st.info(f"{equipo} no tiene partidos pendientes en el calendario.")
            return None
        etiquetas = [f"{cal.fecha_y_hora_texto(fila['FechaUTC'])} · {fila['HomeTeam']} vs. {fila['AwayTeam']} "
                     f"(jornada {int(fila['Jornada'])})" for _, fila in tabla.iterrows()]
        elegido = derecha.selectbox("Partido", range(len(tabla)), format_func=lambda i: etiquetas[i],
                                    key=f"partido_prediccion_{equipo}")
        fila = tabla.iloc[elegido]
        return {"local": fila["HomeTeam"], "visitante": fila["AwayTeam"], "fecha": fila["Fecha"],
                "fecha_texto": cal.fecha_y_hora_texto(fila["FechaUTC"]),
                "estado": f"Pendiente · jornada {int(fila['Jornada'])}", "hipotetico": False}

    izquierda, centro, derecha = st.columns(3)
    local = izquierda.selectbox("Equipo local", equipos, index=0)
    visitante = centro.selectbox("Equipo visitante", equipos, index=1)
    derecha.markdown(tarjeta("Temporada", temporada, "equipos de la temporada en curso"), unsafe_allow_html=True)
    if local == visitante:
        st.warning("Elige dos equipos diferentes.")
        return None
    fecha = pd.Timestamp(fecha_datos) + pd.Timedelta(days=1)
    st.info("**Simulación hipotética.** Este partido lo elegiste tú: puede no estar en el calendario. "
            f"Se calcula como si se jugara el {fecha_texto(fecha)}, con todos los partidos anteriores.")
    return {"local": local, "visitante": visitante, "fecha": fecha, "fecha_texto": fecha_texto(fecha),
            "estado": "Simulación hipotética", "hipotetico": True}


# ---------------------------------------------------------------------------
# Tarjeta, probabilidades y explicación
# ---------------------------------------------------------------------------
def mostrar_prediccion(servicio, partido):
    prediccion = predecir_partido(servicio["modelo"], servicio["historial"],
                                  partido["local"], partido["visitante"], partido["fecha"])
    local, visitante = partido["local"], partido["visitante"]
    probabilidad = prediccion["probabilidades"]

    html(tarjeta_partido(local, visitante, partido["fecha_texto"], partido["estado"]))

    mayor = max(CLASES, key=lambda clase: probabilidad[clase])
    titulos = {"H": f"Gana {local}", "D": "Empate", "A": f"Gana {visitante}"}
    for columna, clase in zip(st.columns(3), CLASES):
        columna.markdown(tarjeta(titulos[clase], porcentaje(probabilidad[clase]), NOMBRES_CLASES[clase],
                                 clase == mayor), unsafe_allow_html=True)
    st.altair_chart(graficos.grafico_probabilidades(local, visitante, probabilidad,
                                                    f"{local} vs. {visitante} · probabilidades del modelo"),
                    use_container_width=True)
    suma = sum(probabilidad.values())
    st.caption(f"Las tres probabilidades suman {porcentaje(suma, 0)}. La tarjeta oscura es el resultado más "
               f"probable según el modelo, que aun así solo tiene una probabilidad de {porcentaje(probabilidad[mayor])}.")
    if prediccion["datos_insuficientes"]:
        st.warning(f"**Datos insuficientes.** Al menos uno de los equipos tiene menos de {MINIMO_PARTIDOS} "
                   "partidos de Premier League en el último año (por ejemplo, un recién ascendido). El modelo "
                   "lo trata como «sin historial» y la estimación es menos fiable.")

    st.subheader("Por qué el modelo estima esto")
    forma = []
    for equipo, perfil in [(local, prediccion["perfil_local"]), (visitante, prediccion["perfil_visitante"])]:
        ultimos = " ".join(perfil["ultimos_resultados"]) or "sin partidos anteriores"
        forma.append((f"Últimos resultados de {equipo}", ultimos,
                      f"{perfil['partidos_previos']} partidos anteriores usados (máximo 38)"))
    for columna, (titulo, valor, detalle) in zip(st.columns(2), forma):
        columna.markdown(tarjeta(titulo, valor, detalle), unsafe_allow_html=True)
    st.caption("V = victoria, E = empate, D = derrota; el más reciente está a la derecha.")

    explicacion = explicar_prediccion(servicio["modelo"], prediccion)
    st.dataframe(explicacion, hide_index=True, use_container_width=True)
    st.caption("Cada fila es una variable del modelo, calculada solo con partidos anteriores a la fecha del "
               "encuentro. «Aporte» positivo empuja la estimación hacia el local y negativo hacia el visitante; "
               "cuanto más lejos de cero, más pesa. Una celda vacía significa que la variable es del otro "
               "equipo o que no hay partidos suficientes.")

    st.markdown(
        f"- **Modelo:** {NOMBRE_MODELO} · {servicio['version']}.\n"
        f"- **Datos hasta:** {fecha_texto(servicio['fecha_datos'])}.\n"
        "- **Limitaciones:** no conoce lesiones, sanciones, fichajes, cambios de entrenador ni la importancia "
        "del partido; casi nunca da el empate como resultado más probable; y un partido lejano en el "
        "calendario se estima con los datos de hoy."
    )


# ---------------------------------------------------------------------------
# Panel de calidad
# ---------------------------------------------------------------------------
def mostrar_calidad(evaluacion):
    if not evaluacion:
        st.info("Todavía no hay una evaluación guardada. Se genera con `python -m src.entrenar_modelo`.")
        return
    prueba = evaluacion["prueba"]
    modelo, baseline = prueba["modelo"], prueba["baseline"]
    st.markdown(
        f"El modelo se entrenó con partidos del **{fecha_texto(prueba['entrenamiento']['desde'])}** al "
        f"**{fecha_texto(prueba['entrenamiento']['hasta'])}** ({prueba['entrenamiento']['partidos']} partidos) y se "
        f"probó con **{modelo['partidos']} partidos posteriores** que no había visto "
        f"({fecha_texto(prueba['prueba']['desde'])} a {fecha_texto(prueba['prueba']['hasta'])}). "
        "El **baseline** es la referencia mínima: dar a todos los partidos las frecuencias históricas de "
        "victoria local, empate y victoria visitante.")

    columnas = st.columns(4)
    metricas = [("Aciertos (accuracy)", "accuracy", True), ("Balanced accuracy", "balanced_accuracy", True),
                ("Log loss", "log_loss", False), ("Brier score", "brier", False)]
    for columna, (titulo, clave, mayor_es_mejor) in zip(columnas, metricas):
        if mayor_es_mejor:
            valor, referencia = porcentaje(modelo[clave]), porcentaje(baseline[clave])
        else:
            valor = f"{modelo[clave]:.3f}".replace(".", ",")
            referencia = f"{baseline[clave]:.3f}".replace(".", ",")
        columna.metric(titulo, valor, f"baseline {referencia}", delta_color="off")
    st.caption("Accuracy: porcentaje de partidos en los que acertó el resultado. Balanced accuracy: promedio del "
               "acierto en cada tipo de resultado (penaliza ignorar los empates). Log loss y Brier miden qué "
               "tan buenas son las probabilidades: cuanto más bajos, mejor.")

    empates = modelo["por_clase"][NOMBRES_CLASES["D"]]
    st.info(f"**Lectura honesta.** El modelo acierta el {porcentaje(modelo['accuracy'])} frente al "
            f"{porcentaje(baseline['accuracy'])} del baseline: mejora la referencia, pero falla en cerca de la "
            f"mitad de los partidos. Predijo empate {empates['veces_predicho']} veces y hubo "
            f"{empates['partidos_reales']} empates: es su principal debilidad.")

    st.subheader("Matriz de confusión (partidos de prueba)")
    nombres = [NOMBRES_CLASES[clase] for clase in CLASES]
    matriz = pd.DataFrame(modelo["matriz_confusion"], columns=[f"Predijo: {n.lower()}" for n in nombres])
    matriz.insert(0, "Resultado real", nombres)
    st.dataframe(matriz, hide_index=True, use_container_width=True)
    st.caption("Cada fila es lo que pasó y cada columna lo que el modelo dio como más probable. "
               "Los aciertos están en la diagonal.")

    por_clase = pd.DataFrame([
        {"Resultado": nombre, "Precision": round(datos["precision"], 3), "Recall": round(datos["recall"], 3),
         "F1": round(datos["f1"], 3), "Partidos reales": datos["partidos_reales"],
         "Veces predicho": datos["veces_predicho"]}
        for nombre, datos in modelo["por_clase"].items()])
    st.dataframe(por_clase, hide_index=True, use_container_width=True)
    st.caption("Precision: de las veces que predijo ese resultado, cuántas acertó. Recall: de los partidos que "
               "terminaron así, cuántos predijo. F1 combina las dos.")

    st.subheader("Backtesting por temporada")
    filas, grafico = [], []
    for bloque in evaluacion["backtesting"]:
        m, b = bloque["modelo"], bloque["baseline"]
        filas.append({"Temporada": bloque["temporada"], "Partidos de entrenamiento": bloque["entrenamiento"]["partidos"],
                      "Partidos evaluados": m["partidos"], "Accuracy": round(m["accuracy"], 3),
                      "Accuracy baseline": round(b["accuracy"], 3), "Log loss": round(m["log_loss"], 3),
                      "Log loss baseline": round(b["log_loss"], 3), "Brier": round(m["brier"], 3),
                      "Brier baseline": round(b["brier"], 3)})
        grafico.append({"Temporada": bloque["temporada"], "Serie": "Modelo", "Aciertos": m["accuracy"],
                        "Partidos": m["partidos"]})
        grafico.append({"Temporada": bloque["temporada"], "Serie": "Baseline", "Aciertos": b["accuracy"],
                        "Partidos": m["partidos"]})
    st.altair_chart(graficos.grafico_backtesting(pd.DataFrame(grafico), "Aciertos del modelo y del baseline por temporada"),
                    use_container_width=True)
    st.dataframe(pd.DataFrame(filas), hide_index=True, use_container_width=True)
    st.caption("Para cada temporada, el modelo se entrena solo con las temporadas anteriores y predice esa "
               "temporada completa. Así se comprueba cómo le habría ido sin conocer el futuro. Una temporada "
               "en curso tiene pocos partidos y su resultado cambia mucho de una jornada a otra.")

    st.subheader("Calibración de las probabilidades")
    calibracion = pd.DataFrame(evaluacion["calibracion"]).rename(columns={
        "tramo": "Tramo", "casos": "Casos", "probabilidad_media": "Probabilidad media",
        "frecuencia_real": "Frecuencia real"})
    st.altair_chart(graficos.grafico_calibracion(calibracion, "Lo que dijo el modelo frente a lo que pasó (backtesting)"),
                    use_container_width=True)
    st.caption("Si el modelo dice «30 %» muchas veces, lo ideal es que pase cerca del 30 % de las veces: "
               "los puntos deberían quedar cerca de la línea discontinua.")

    with st.expander("Ficha técnica del modelo"):
        configuracion = evaluacion["configuracion"]
        reparto = evaluacion["reparto_de_temporadas"]
        st.markdown(
            f"- **Modelo:** {evaluacion['modelo']} (scikit-learn, solver `{configuracion['solver']}`, "
            f"C = {configuracion['C']}), dentro de un `Pipeline`: {', '.join(configuracion['pasos'])}.\n"
            f"- **Versión:** {evaluacion['version']}.\n"
            f"- **Reparto cronológico:** entrenamiento {', '.join(reparto['entrenamiento'])}; validación "
            f"{', '.join(reparto['validacion'])} (para elegir C); prueba {', '.join(reparto['prueba'])}.\n"
            f"- **Variables ({len(evaluacion['variables'])}):** diferencias local − visitante de la forma reciente "
            f"(últimos {configuracion['ventana_forma']} partidos) y del nivel (últimos {configuracion['ventana_nivel']}), "
            f"puntos del local en casa y del visitante fuera (últimos {configuracion['ventana_condicion']}) y dos "
            "marcas de «sin historial».\n"
            "- **Sin fuga de datos:** cada variable usa solo partidos de fechas anteriores; los del mismo día "
            "se excluyen porque no hay una hora fiable. La temporada 2020/21 solo sirve de historial."
        )
