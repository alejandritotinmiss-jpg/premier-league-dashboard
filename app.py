"""Premier League Data Analytics: rendimiento de los equipos de la Premier League, 2020/21 a 2024/25.

Ejecutar desde la carpeta raíz del proyecto:
    streamlit run app.py

La app tiene trece secciones que se eligen en la barra lateral. La lógica está en src/:
    src/tablero.py       datos de cada gráfico según los filtros
    src/secciones.py     las seis secciones de análisis de la versión 3
    src/comparador.py    comparador de equipos y local contra visitante
    src/correlaciones.py matriz de correlación y explicaciones
    src/records.py       récords de las cinco temporadas
    src/ranking.py       ranking personalizado
    src/sorpresas.py     detector de sorpresas
    src/graficos.py      gráficos (Altair)
    src/jugadores.py     goleadores y asistentes
    src/partidos.py      búsqueda y ficha de partidos
    src/asistente.py     asistente basado en reglas
    src/curiosidades.py  curiosidades de cada temporada
    src/estilos.py       colores, encabezado y tarjetas
"""

import pandas as pd
import streamlit as st

from src import graficos, secciones, tablero
from src.analisis import correlacion, fuerza, tabla_correlaciones
from src.asistente import EJEMPLOS, responder
from src.curiosidades import curiosidades_temporada, elegir_curiosidad
from src.equipos import nombre_completo
from src.estilos import CONFIG_INSIGNIA, CSS, con_insignia, encabezado, tarjeta
from src.jugadores import cargar_jugadores, lideres, ranking
from src.partidos import fecha_texto, ficha_partido, marcador, partidos_de_temporada, tabla_resumen
from src.preparar_datos import CARPETA_PROCESADOS, guardar_tablas

st.set_page_config(page_title="Premier League Data Analytics", page_icon="⚽", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)

SECCIONES = ["Inicio", "Clasificación", "Análisis", "Comparador de equipos", "Local vs. visitante",
             "Relaciones y correlaciones", "Ranking personalizado", "Récords históricos",
             "Goleadores y Asistencias", "Partidos", "Detector de sorpresas", "Asistente IA", "Curiosidades"]


def formato(numero, decimales=2):
    """Escribe un número con coma decimal, como se usa en español."""
    return f"{numero:.{decimales}f}".replace(".", ",")


@st.cache_data
def cargar_datos():
    """Lee las tablas procesadas (si no existen, las genera a partir de data/raw/).

    @st.cache_data guarda el resultado: los archivos se leen una sola vez,
    no cada vez que el usuario cambia un filtro.
    """
    rutas = {
        "partidos": CARPETA_PROCESADOS / "partidos_limpios.csv",
        "equipo_partido": CARPETA_PROCESADOS / "equipo_partido.csv",
        "estadisticas": CARPETA_PROCESADOS / "estadisticas_equipo_temporada.csv",
    }
    if any(not ruta.exists() for ruta in rutas.values()):
        guardar_tablas()
    partidos = pd.read_csv(rutas["partidos"], parse_dates=["Date"])
    equipo_partido = pd.read_csv(rutas["equipo_partido"])
    estadisticas = pd.read_csv(rutas["estadisticas"])
    return partidos, equipo_partido, estadisticas


@st.cache_data
def cargar_datos_jugadores():
    return cargar_jugadores()


try:
    partidos, equipo_partido, estadisticas = cargar_datos()
    goleadores, asistencias, fuentes_jugadores = cargar_datos_jugadores()
except (FileNotFoundError, ValueError) as error:
    st.error(f"No se pudieron cargar los datos: {error}")
    st.stop()

# ---------------------------------------------------------------------------
# Barra lateral: menú, temporada y filtros de la sección
# ---------------------------------------------------------------------------
st.sidebar.markdown('<div class="marca-lateral">PREMIER LEAGUE DATA ANALYTICS</div>',
                    unsafe_allow_html=True)
seccion = st.sidebar.radio("Sección", SECCIONES)

temporadas = tablero.temporadas_disponibles(estadisticas)
temporada = st.sidebar.selectbox("Temporada", temporadas, index=len(temporadas) - 1,
                                 help="Se aplica a todas las secciones.")
equipos_temporada = tablero.equipos_de_temporada(estadisticas, temporada)
partidos_temporada = partidos_de_temporada(partidos, temporada)

condicion = "Total"
seleccionados = tablero.equipos_por_defecto(estadisticas, temporada)
nombre_metrica = "Tiros al arco"
todas_las_temporadas = True

if seccion in ["Clasificación", "Análisis"]:
    st.sidebar.divider()
    condicion = st.sidebar.radio(
        "Partidos", tablero.CONDICIONES, horizontal=True,
        help="Total: los 38 partidos. Local: los 19 en casa. Visitante: los 19 fuera.")
    # Las opciones dependen de la temporada: solo aparecen los 20 equipos que la jugaron.
    seleccionados = st.sidebar.multiselect(
        "Equipos (hasta 6)", equipos_temporada,
        default=tablero.equipos_por_defecto(estadisticas, temporada), max_selections=6,
        help="Se resaltan en los gráficos. Al abrir se muestran los tres primeros de la temporada.")

if seccion == "Análisis":
    nombre_metrica = st.sidebar.selectbox(
        "Estadística de juego", list(tablero.METRICAS), index=1,
        help="Se compara con los puntos y entre local y visitante. Todas son promedios por partido.")
    todas_las_temporadas = st.sidebar.toggle(
        "Relación con los puntos: usar las cinco temporadas", value=True,
        help="Activado: 100 equipo-temporada. Desactivado: solo los 20 equipos de la temporada elegida.")

columna_metrica = tablero.METRICAS[nombre_metrica]

st.sidebar.divider()
st.sidebar.caption("Partidos: Football-Data.co.uk, vía DataHub (dominio público). Goleadores y "
                   "asistencias: ESPN, Premier League y Wikipedia (ver la sección). Puntos "
                   "calculados con los resultados de los partidos.")

# Cálculos que usan varias secciones.
clasificacion = tablero.tabla_clasificacion(estadisticas, temporada, condicion)
resultados = tablero.resultados_temporada(equipo_partido, temporada)
ventaja = tablero.ventaja_local_por_temporada(estadisticas)
ventaja_temporada = ventaja[ventaja["Temporada"] == temporada].set_index("Condicion")["PuntosPorPartido"]


# ---------------------------------------------------------------------------
# 1. Inicio
# ---------------------------------------------------------------------------
def pagina_inicio():
    st.markdown(encabezado("Más allá de la tabla",
                           "Exploración interactiva del rendimiento de los equipos de la Premier "
                           "League, de 2020/21 a 2024/25"), unsafe_allow_html=True)
    st.markdown("**Pregunta guía:** ¿cómo se relacionan los tiros, tiros al arco, córners, faltas y "
                "tarjetas con los goles y los puntos, y qué diferencias hay entre jugar de local y "
                "de visitante?")

    total = tablero.tabla_clasificacion(estadisticas, temporada, "Total")
    tabla_goles = ranking(goleadores, temporada, "Goles")
    lider_goles = lideres(tabla_goles)
    columnas = st.columns(4)
    columnas[0].markdown(tarjeta(f"Campeón {temporada}", total.loc[0, "Equipo"],
                                 f"{total.loc[0, 'Pts']} puntos ganados en el campo", True),
                         unsafe_allow_html=True)
    columnas[1].markdown(tarjeta("Partidos ganados por el local", f"{resultados['Gana el local']} de 380",
                                 f"{resultados['Gana el visitante']} ganados por el visitante y "
                                 f"{resultados['Empate']} empates"), unsafe_allow_html=True)
    columnas[2].markdown(tarjeta("Ventaja de local", formato(ventaja_temporada["Local"] - ventaja_temporada["Visitante"]),
                                 f"puntos por partido de diferencia (local {formato(ventaja_temporada['Local'])}, "
                                 f"visitante {formato(ventaja_temporada['Visitante'])})"), unsafe_allow_html=True)
    columnas[3].markdown(tarjeta("Máximo goleador", " y ".join(lider_goles["Jugador"]),
                                 f"{int(lider_goles['Goles'].iloc[0])} goles"), unsafe_allow_html=True)

    r_arco = {}
    for nombre_condicion in tablero.CONDICIONES:
        r_arco[nombre_condicion], _ = tablero.correlacion_con_puntos(
            estadisticas, None, nombre_condicion, "TirosArcoPorPartido", True)
    mejor_local, total_equipos, diferencia_media = tablero.equipos_mejor_de_local(estadisticas)

    st.subheader("Hallazgos principales (cinco temporadas, 100 equipo-temporada)")
    st.markdown(
        f"1. **Los tiros al arco son la estadística de juego más relacionada con los puntos** "
        f"(r = {formato(r_arco['Total'])}).\n"
        f"2. **La relación es parecida de local y de visitante** "
        f"(r = {formato(r_arco['Local'])} y {formato(r_arco['Visitante'])}): la diferencia es "
        f"menor que la variación entre temporadas.\n"
        f"3. **Lo que cambia es el nivel:** de local los equipos suman de media "
        f"{formato(diferencia_media)} puntos más por partido, y {mejor_local} de los "
        f"{total_equipos} equipo-temporada rindieron mejor en casa.\n"
        f"4. **2020/21, jugada casi sin público, es la excepción:** fue la única temporada en que "
        f"los visitantes ganaron más partidos que los locales."
    )

    st.subheader("Qué hay en cada sección")
    descripciones = [
        ("Clasificación", "Tabla de la temporada (total, local o visitante) y evolución de los puntos."),
        ("Análisis", "Relación de cada estadística con los puntos y los goles, rankings y local contra visitante."),
        ("Comparador de equipos", "Dos equipos frente a frente en 13 estadísticas, en total, de local o de visitante."),
        ("Local vs. visitante", "Cómo cambia un equipo dentro y fuera de casa, con una conclusión calculada."),
        ("Relaciones y correlaciones", "Matriz de correlación, mapa de calor y dispersión con explicación sencilla."),
        ("Ranking personalizado", "Ordena los 20 equipos por la estadística que elijas."),
        ("Récords históricos", "Lo máximo de las cinco temporadas: de una temporada, acumulados y de partidos."),
        ("Goleadores y Asistencias", "Los jugadores con más goles y asistencias de cada temporada."),
        ("Partidos", "Busca un partido o un enfrentamiento y mira su ficha completa."),
        ("Detector de sorpresas", "Partidos en los que tiros o córners contrastan con el resultado."),
        ("Asistente IA", "Haz preguntas en lenguaje natural sobre los partidos de la temporada."),
        ("Curiosidades", "Datos llamativos de la temporada y el botón SORPRÉNDEME."),
    ]
    columnas = st.columns(3)
    for indice, (nombre, texto) in enumerate(descripciones):
        columnas[indice % 3].markdown(tarjeta(nombre, "", texto), unsafe_allow_html=True)

    with st.expander("Datos y método"):
        st.markdown(
            "- **Fuente de los partidos:** [English Premier League](https://datahub.io/football/english-premier-league), "
            "DataHub, a partir de Football-Data.co.uk. Licencia de dominio público (ODC-PDDL-1.0).\n"
            "- **Datos:** 1.900 partidos de cinco temporadas (380 por temporada), sin valores "
            "faltantes ni duplicados.\n"
            "- **Limpieza:** se excluyó la columna del árbitro. En Newcastle 2-4 West Ham (15/08/2021) "
            "el dato de tiros del West Ham era imposible (9 al arco con 8 tiros) y se dejó vacío; el "
            "marcador sí cuenta.\n"
            "- **Cálculos:** cada partido se convierte en dos registros (local y visitante). Los puntos "
            "salen del resultado: 3 por ganar, 1 por empatar y 0 por perder. Las estadísticas se "
            "resumen por equipo y temporada como promedios por partido.\n"
            "- **Correlaciones:** coeficiente de Pearson calculado con `numpy.corrcoef`.\n"
            "- **Goleadores y asistencias:** tablas consultadas en ESPN, la web oficial de la Premier "
            "League y Wikipedia (detalle en su sección)."
        )
    with st.expander("Limitaciones"):
        st.markdown(
            "- Correlación no es causalidad; la calidad del equipo es un factor común.\n"
            "- Un equipo que va ganando puede tirar menos: con datos por temporada no se ve ese efecto.\n"
            "- Los mismos equipos se repiten entre temporadas, así que las observaciones no son "
            "independientes. Los resultados son descriptivos.\n"
            "- No hay datos de posesión ni de calidad de las ocasiones, y los autogoles no se identifican.\n"
            "- Los puntos son los ganados en el campo: no incluyen las sanciones de 2023/24.\n"
            "- Los datos de goleadores de 2020/21 están incompletos."
        )


# ---------------------------------------------------------------------------
# 2. Clasificación
# ---------------------------------------------------------------------------
def pagina_clasificacion():
    st.markdown(encabezado("Clasificación", f"Temporada {temporada} · partidos: {condicion.lower()}"),
                unsafe_allow_html=True)
    st.markdown(f"**Clasificación calculada · {temporada} · {condicion.lower()}**")
    st.dataframe(con_insignia(clasificacion), hide_index=True, use_container_width=True,
                 height=740, column_config=CONFIG_INSIGNIA)
    st.caption("Orden: puntos, diferencia de goles (DG) y goles a favor (GF). La tabla de local "
               "o de visitante usa solo esos 19 partidos.")
    if "Pts oficiales" in clasificacion.columns:
        st.warning(
            "En 2023/24, Everton perdió 8 puntos y Nottingham Forest 4 por incumplir las reglas "
            "financieras de la liga. Esta clasificación usa los puntos ganados en el campo, porque "
            "el proyecto estudia la relación entre el juego y los puntos. La columna "
            "«Pts oficiales» muestra los puntos tras la sanción."
        )

    datos = tablero.puntos_por_equipo(estadisticas, temporada, condicion, seleccionados)
    titulo = f"Puntos por equipo en {temporada} ({condicion.lower()})"
    st.altair_chart(graficos.grafico_puntos_por_equipo(datos, condicion, titulo),
                    use_container_width=True)

    st.subheader("Evolución de los puntos")
    if not seleccionados:
        st.info("Elige al menos un equipo en la barra lateral para ver su evolución.")
    else:
        datos = tablero.evolucion_puntos(equipo_partido, temporada, seleccionados)
        st.altair_chart(
            graficos.grafico_evolucion(datos, seleccionados, f"Puntos acumulados en {temporada}"),
            use_container_width=True,
        )
        st.caption("El eje horizontal es el número de partido de cada equipo (1 a 38, por fecha), "
                   "no la jornada oficial: los partidos aplazados cambian el orden de las jornadas. "
                   "Esta vista siempre usa los 38 partidos.")


# ---------------------------------------------------------------------------
# 3. Análisis
# ---------------------------------------------------------------------------
def pagina_analisis():
    st.markdown(encabezado("Análisis", f"Temporada {temporada} · {nombre_metrica.lower()} · "
                                       f"partidos: {condicion.lower()}"), unsafe_allow_html=True)
    r_metrica, n_metrica = tablero.correlacion_con_puntos(
        estadisticas, temporada, condicion, columna_metrica, todas_las_temporadas)

    columna1, columna2, columna3, columna4 = st.columns(4)
    columna1.metric(f"Líder ({condicion.lower()})", clasificacion.loc[0, "Equipo"],
                    f"{clasificacion.loc[0, 'Pts']} puntos", delta_color="off")
    columna2.metric("Partidos ganados por el local", f"{resultados['Gana el local']} de 380",
                    f"{resultados['Gana el visitante']} ganados por el visitante", delta_color="off")
    columna3.metric("Ventaja de local (puntos por partido)",
                    formato(ventaja_temporada["Local"] - ventaja_temporada["Visitante"]),
                    f"local {formato(ventaja_temporada['Local'])} · visitante "
                    f"{formato(ventaja_temporada['Visitante'])}", delta_color="off")
    columna4.metric(f"Correlación: {nombre_metrica.lower()} y puntos", formato(r_metrica),
                    f"relación {fuerza(r_metrica)} · n = {n_metrica}", delta_color="off")

    pestanas = st.tabs(["Juego y puntos", "Tiros al arco y goles", "Ranking por estadística",
                        "Local y visitante"])

    with pestanas[0]:
        alcance = "las cinco temporadas" if todas_las_temporadas else temporada
        datos = tablero.datos_dispersion(estadisticas, temporada, condicion, columna_metrica,
                                         todas_las_temporadas, seleccionados)
        recta = tablero.recta_tendencia(datos["Valor"], datos["PuntosPorPartido"])
        titulo = (f"{nombre_metrica} frente a puntos por partido · {condicion.lower()} · "
                  f"{alcance} · r = {formato(r_metrica)} (n = {n_metrica})")
        st.altair_chart(graficos.grafico_dispersion(datos, recta, nombre_metrica, condicion, titulo),
                        use_container_width=True)
        st.caption("Cada punto es un equipo en una temporada. Los equipos elegidos de la temporada "
                   f"{temporada} aparecen más grandes y con su nombre. La línea discontinua es la "
                   "tendencia (recta de mínimos cuadrados con np.polyfit).")

        temporada_r = None if todas_las_temporadas else temporada
        correlaciones = tabla_correlaciones(estadisticas, temporada=temporada_r)
        st.altair_chart(
            graficos.grafico_correlaciones(
                correlaciones,
                f"Correlación de cada estadística con los puntos, de local y de visitante · {alcance}"),
            use_container_width=True,
        )
        st.info("**Correlación no es causalidad.** Que los equipos con más tiros al arco sumen más "
                "puntos no demuestra que tirar más cause más puntos: la calidad del equipo puede "
                "explicar las dos cosas. Con una sola temporada (20 equipos) las correlaciones "
                "varían más que con las cinco juntas.")

    with pestanas[1]:
        datos = tablero.datos_tiros_arco_goles(estadisticas, temporada, condicion, seleccionados)
        r_goles = correlacion(datos["TirosArcoPorPartido"], datos["GolesFavorPorPartido"])
        recta = tablero.recta_tendencia(datos["TirosArcoPorPartido"], datos["GolesFavorPorPartido"])
        recta = recta.rename(columns={"Valor": "TirosArcoPorPartido", "PuntosPorPartido": "GolesFavorPorPartido"})
        st.altair_chart(graficos.grafico_tiros_arco_goles(
            datos, recta, f"Tiros al arco y goles por partido · {temporada} · {condicion.lower()} · "
                          f"r = {formato(r_goles)} (n = {len(datos)})"), use_container_width=True)
        st.caption(f"Cada punto es uno de los 20 equipos de {temporada}. La relación es {fuerza(r_goles)}: "
                   "los equipos que más tiran al arco suelen marcar más goles.")

    with pestanas[2]:
        datos = tablero.ranking_metrica(estadisticas, temporada, condicion, columna_metrica, seleccionados)
        st.altair_chart(graficos.grafico_ranking(
            datos, nombre_metrica, condicion,
            f"{nombre_metrica} por partido · {temporada} · {condicion.lower()}"), use_container_width=True)
        st.caption("Cambia la estadística en la barra lateral (tiros, córners, faltas, tarjetas...). "
                   "Los equipos elegidos aparecen resaltados.")

    with pestanas[3]:
        if not seleccionados:
            st.info("Elige al menos un equipo en la barra lateral para comparar su rendimiento.")
        else:
            datos = tablero.comparacion_local_visitante(estadisticas, temporada, seleccionados,
                                                        columna_metrica)
            st.altair_chart(graficos.grafico_local_visitante(
                datos, nombre_metrica, f"{nombre_metrica} por partido de local y de visitante · {temporada}"),
                use_container_width=True)

        st.altair_chart(graficos.grafico_ventaja_local(
            ventaja, temporada, "Puntos por partido de local y de visitante en cada temporada"),
            use_container_width=True)
        st.markdown(
            f"En **{temporada}** el local ganó **{resultados['Gana el local']}** partidos, hubo "
            f"**{resultados['Empate']}** empates y el visitante ganó **{resultados['Gana el visitante']}**."
        )
        st.caption("2020/21 se jugó casi entera sin público por la pandemia. Coincide con la única "
                   "temporada en que los visitantes ganaron más partidos que los locales, pero estos "
                   "datos no permiten demostrar que esa sea la causa.")


# ---------------------------------------------------------------------------
# 4. Goleadores y Asistencias
# ---------------------------------------------------------------------------
def tabla_jugadores(tabla_ranking, columna):
    """Tabla de jugadores lista para mostrar, con insignia del equipo."""
    columnas = ["Posicion", "Jugador", "EquipoCorto", "Partidos", columna]
    tabla = tabla_ranking[columnas].rename(columns={"Posicion": "Pos", "EquipoCorto": "Equipo"})
    if tabla["Partidos"].isna().all():
        tabla = tabla.drop(columns="Partidos")
    else:
        tabla["Partidos"] = tabla["Partidos"].astype("Int64")
    return con_insignia(tabla)


def pagina_jugadores():
    st.markdown(encabezado("Goleadores y Asistencias", f"Temporada {temporada}"), unsafe_allow_html=True)
    fuente = fuentes_jugadores["temporadas"][temporada]
    if not fuente["completo"]:
        st.warning(f"**Datos incompletos.** {fuente['nota']}")
    elif fuente["nota"]:
        st.info(fuente["nota"])

    tabla_goles = ranking(goleadores, temporada, "Goles")
    tabla_asistencias = ranking(asistencias, temporada, "Asistencias")
    tablas = [(tabla_goles, "Goles", "Máximo goleador"), (tabla_asistencias, "Asistencias", "Máximo asistente")]

    # Arriba, las tarjetas de los líderes una al lado de la otra.
    columnas = st.columns(2)
    for columna_pagina, (tabla, nombre, titulo) in zip(columnas, tablas):
        primeros = lideres(tabla)
        if len(primeros) > 1:
            titulo += " (empate)"
        equipos_lideres = " y ".join(sorted(set(primeros["Equipo"])))
        columna_pagina.markdown(tarjeta(titulo, " y ".join(primeros["Jugador"]),
                                        f"{int(primeros[nombre].iloc[0])} {nombre.lower()} · {equipos_lideres}",
                                        True), unsafe_allow_html=True)

    # Debajo, cada tabla a lo ancho para que se vean todas las columnas.
    for tabla, nombre, _ in tablas:
        st.subheader("Goleadores" if nombre == "Goles" else "Asistencias")
        st.dataframe(tabla_jugadores(tabla, nombre), hide_index=True, use_container_width=True,
                     column_config=CONFIG_INSIGNIA)

    st.caption(
        f"Goles: [{fuente['goleadores']['fuente']}]({fuente['goleadores']['url']}) · "
        f"Asistencias: [{fuente['asistencias']['fuente']}]({fuente['asistencias']['url']}) · "
        f"consultado el {fecha_texto(fuentes_jugadores['fecha_consulta'])}. Se muestran los primeros puestos "
        "completos (si hay empate en el último puesto, entran todos los empatados)."
    )


# ---------------------------------------------------------------------------
# 5. Partidos
# ---------------------------------------------------------------------------
def pagina_partidos():
    st.markdown(encabezado("Partidos", f"Busca partidos de la temporada {temporada}"),
                unsafe_allow_html=True)
    izquierda, derecha = st.columns(2)
    equipo = izquierda.selectbox("Equipo", ["Todos"] + equipos_temporada)
    rivales = ["Todos"] + [e for e in equipos_temporada if e != equipo]
    rival = derecha.selectbox("Rival", rivales, disabled=(equipo == "Todos"))

    tabla = partidos_temporada
    if equipo != "Todos":
        tabla = tabla[(tabla["HomeTeam"] == equipo) | (tabla["AwayTeam"] == equipo)]
        if rival != "Todos":
            tabla = tabla[(tabla["HomeTeam"] == rival) | (tabla["AwayTeam"] == rival)]
    tabla = tabla.reset_index(drop=True)

    st.markdown(f"**{len(tabla)} {'partido' if len(tabla) == 1 else 'partidos'}** "
                "(los valores de tiros, córners y tarjetas aparecen como local - visitante).")
    st.dataframe(tabla_resumen(tabla), hide_index=True, use_container_width=True,
                 height=min(420, 38 + 35 * len(tabla)))

    if tabla.empty:
        return
    st.subheader("Ficha del partido")
    etiquetas = [f"{fecha_texto(fila['Date'])} · {marcador(fila)}" for _, fila in tabla.iterrows()]
    elegido = st.selectbox("Elige un partido", range(len(tabla)), format_func=lambda i: etiquetas[i])
    fila = tabla.iloc[elegido]

    local, centro, visitante = st.columns([2, 1, 2])
    local.markdown(tarjeta("Local", nombre_completo(fila["HomeTeam"]), fila["HomeTeam"]), unsafe_allow_html=True)
    centro.markdown(tarjeta(fecha_texto(fila["Date"]), f"{int(fila['FTHG'])} - {int(fila['FTAG'])}",
                            f"Descanso: {int(fila['HTHG'])} - {int(fila['HTAG'])}", True),
                    unsafe_allow_html=True)
    visitante.markdown(tarjeta("Visitante", nombre_completo(fila["AwayTeam"]), fila["AwayTeam"]),
                       unsafe_allow_html=True)
    st.dataframe(ficha_partido(fila), hide_index=True, use_container_width=True)


# ---------------------------------------------------------------------------
# 6. Asistente IA
# ---------------------------------------------------------------------------
def pagina_asistente():
    st.markdown(encabezado("Asistente IA Premier League",
                           f"Pregunta sobre los partidos de la temporada {temporada}"),
                unsafe_allow_html=True)
    st.caption("Asistente basado en reglas: reconoce equipos y palabras clave y busca la respuesta "
               "en los datos del proyecto. No usa un modelo de lenguaje externo ni internet, y solo "
               "responde sobre la temporada elegida en la barra lateral.")

    if "chat" not in st.session_state:
        st.session_state["chat"] = []

    st.markdown("**Prueba con un ejemplo:**")
    pregunta = None
    columnas = st.columns(3)
    for indice, ejemplo in enumerate(EJEMPLOS[:3]):
        if columnas[indice].button(ejemplo, key=f"ejemplo_{indice}", use_container_width=True):
            pregunta = ejemplo

    escrita = st.chat_input("Escribe tu pregunta, por ejemplo: ¿cuántos goles marcó el Arsenal?")
    if escrita:
        pregunta = escrita

    if pregunta:
        resultado = responder(pregunta, partidos_temporada, temporada)
        st.session_state["chat"].append({"rol": "user", "texto": pregunta})
        st.session_state["chat"].append({"rol": "assistant", "texto": resultado["texto"],
                                         "tabla": resultado["tabla"], "temporada": temporada})

    for mensaje in st.session_state["chat"]:
        with st.chat_message(mensaje["rol"]):
            st.markdown(mensaje["texto"])
            if mensaje.get("tabla") is not None and not mensaje["tabla"].empty:
                st.dataframe(mensaje["tabla"], hide_index=True, use_container_width=True)
            if mensaje["rol"] == "assistant":
                st.caption(f"Temporada consultada: {mensaje['temporada']}")

    if st.session_state["chat"] and st.button("Borrar conversación"):
        st.session_state["chat"] = []
        st.rerun()


# ---------------------------------------------------------------------------
# 7. Curiosidades
# ---------------------------------------------------------------------------
def pagina_curiosidades():
    st.markdown(encabezado("Curiosidades", f"Datos llamativos de la temporada {temporada}"),
                unsafe_allow_html=True)
    filtro = equipo_partido["Temporada"] == temporada
    curiosidades = curiosidades_temporada(partidos_temporada, equipo_partido[filtro])

    vistas = st.session_state.setdefault("curiosidades_vistas", {})
    actual = st.session_state.setdefault("curiosidad_actual", {})
    if st.button("SORPRÉNDEME", type="primary"):
        elegida, vistas[temporada] = elegir_curiosidad(curiosidades, vistas.get(temporada, []))
        actual[temporada] = elegida
    if temporada in actual:
        st.markdown(tarjeta(actual[temporada]["titulo"], "", actual[temporada]["texto"], True),
                    unsafe_allow_html=True)
        st.caption(f"Has visto {len(vistas[temporada])} de {len(curiosidades)} curiosidades de esta "
                   "temporada. Cuando las veas todas, empiezan de nuevo.")

    st.subheader("Todas las curiosidades")
    columnas = st.columns(3)
    for indice, curiosidad in enumerate(curiosidades):
        columnas[indice % 3].markdown(tarjeta(curiosidad["titulo"], "", curiosidad["texto"]),
                                      unsafe_allow_html=True)


PAGINAS = {
    "Inicio": pagina_inicio,
    "Clasificación": pagina_clasificacion,
    "Análisis": pagina_analisis,
    "Comparador de equipos": lambda: secciones.pagina_comparador(estadisticas, temporada),
    "Local vs. visitante": lambda: secciones.pagina_local_visitante(estadisticas, temporada),
    "Relaciones y correlaciones": lambda: secciones.pagina_correlaciones(estadisticas, temporada),
    "Ranking personalizado": lambda: secciones.pagina_ranking(estadisticas, temporada),
    "Récords históricos": lambda: secciones.pagina_records(estadisticas, partidos, temporada),
    "Goleadores y Asistencias": pagina_jugadores,
    "Partidos": pagina_partidos,
    "Detector de sorpresas": lambda: secciones.pagina_sorpresas(partidos_temporada, temporada),
    "Asistente IA": pagina_asistente,
    "Curiosidades": pagina_curiosidades,
}
PAGINAS[seccion]()
