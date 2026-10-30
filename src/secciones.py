"""Las seis secciones de análisis agregadas en la versión 3 de la app.

Cada función dibuja una sección. Los cálculos están en otros archivos de src/
(comparador, correlaciones, records, ranking y sorpresas); aquí solo se muestran.
"""

import streamlit as st

from src import comparador, correlaciones, graficos, ranking, records, sorpresas
from src.analisis import correlacion, fuerza
from src.equipos import nombre_completo
from src.estilos import CONFIG_INSIGNIA, con_insignia, encabezado, tarjeta
from src.partidos import tabla_resumen
from src.tablero import equipos_de_temporada, equipos_por_defecto, recta_tendencia

AVISO_TIROS_WEST_HAM = ("A West Ham le falta el dato de tiros y tiros al arco de un partido de 2021/22 "
                        "(Newcastle 2-4 West Ham, 15/08/2021), porque el dato original era imposible. "
                        "Sus totales de tiros de esa temporada suman 37 partidos y sus promedios se "
                        "calculan sobre esos 37.")


def html(texto):
    """Atajo para escribir HTML propio (tarjetas) en la página."""
    st.markdown(texto, unsafe_allow_html=True)


def formato(numero, decimales=2):
    return f"{numero:.{decimales}f}".replace(".", ",")


def lista_texto(nombres):
    nombres = list(nombres)
    if len(nombres) <= 1:
        return "".join(nombres)
    return ", ".join(nombres[:-1]) + " y " + nombres[-1]


# ---------------------------------------------------------------------------
# Comparador de equipos
# ---------------------------------------------------------------------------
def pagina_comparador(estadisticas, temporada):
    html(encabezado("Comparador de equipos", f"Dos equipos frente a frente · temporada {temporada}"))
    equipos = equipos_de_temporada(estadisticas, temporada)
    primeros = equipos_por_defecto(estadisticas, temporada, 2)
    columna_a, columna_b, columna_c = st.columns([2, 2, 3])
    equipo_a = columna_a.selectbox("Primer equipo", equipos, index=equipos.index(primeros[0]))
    equipo_b = columna_b.selectbox("Segundo equipo", equipos, index=equipos.index(primeros[1]))
    condicion = columna_c.radio("Partidos que se comparan", ["Total", "Local", "Visitante"], horizontal=True,
                                help="Total: los 38 partidos. Local: los 19 en casa. Visitante: los 19 fuera.")

    if equipo_a == equipo_b:
        st.warning("Elegiste el mismo equipo dos veces. Elige dos equipos diferentes para compararlos.")
        return

    comparacion = comparador.tabla_comparacion(estadisticas, temporada, equipo_a, equipo_b, condicion)

    # Tarjetas de cada equipo.
    for columna_pagina, equipo in zip(st.columns(2), [equipo_a, equipo_b]):
        fila = comparador.fila_equipo(estadisticas, temporada, equipo, condicion)
        with columna_pagina:
            html(tarjeta(nombre_completo(equipo), f"{int(fila['Puntos'])} puntos",
                         f"{int(fila['V'])} victorias · {int(fila['E'])} empates · {int(fila['D'])} derrotas "
                         f"({int(fila['PJ'])} partidos, {condicion.lower()})", True))
            pequenas = st.columns(3)
            pequenas[0].markdown(tarjeta("Goles", int(fila["GolesFavor"]),
                                         f"{formato(fila['GolesFavorPorPartido'])} por partido"), unsafe_allow_html=True)
            pequenas[1].markdown(tarjeta("Recibidos", int(fila["GolesContra"]),
                                         f"{formato(fila['GolesContraPorPartido'])} por partido"), unsafe_allow_html=True)
            pequenas[2].markdown(tarjeta("Tiros al arco", int(fila["TirosArco"]),
                                         f"de {int(fila['Tiros'])} tiros"), unsafe_allow_html=True)

    # En qué tiene cada equipo un valor más alto.
    st.subheader("En qué estadísticas tiene más cada equipo")
    for columna_pagina, equipo in zip(st.columns(2), [equipo_a, equipo_b]):
        nombres = comparacion.loc[comparacion["Más alto"] == equipo, "Estadística"].str.lower().tolist()
        texto = lista_texto(nombres) if nombres else "ninguna estadística"
        columna_pagina.markdown(tarjeta(f"{equipo} tiene más", f"{len(nombres)} de {len(comparacion)}", texto),
                                unsafe_allow_html=True)
    iguales = comparacion.loc[comparacion["Más alto"] == "Igual", "Estadística"].str.lower().tolist()
    if iguales:
        st.caption(f"Empatan en: {lista_texto(iguales)}.")
    st.caption("«Tener más» no siempre es bueno: en goles recibidos, derrotas, faltas y tarjetas, "
               "un valor más alto es peor.")

    datos = comparador.reparto_por_estadistica(comparacion, equipo_a, equipo_b)
    st.altair_chart(graficos.grafico_reparto(
        datos, equipo_a, equipo_b, f"{equipo_a} y {equipo_b} · {temporada} · {condicion.lower()}"),
        use_container_width=True)
    st.caption("Cada barra reparte el total de los dos equipos: si un equipo tiene el 60 %, tuvo más "
               "que el otro. El número dentro de la barra es el valor real. Se usa este gráfico en lugar "
               "de un radar porque las estadísticas tienen escalas muy distintas (cientos de tiros, "
               "pocas tarjetas rojas) y en un radar se verían deformadas.")

    st.dataframe(comparador.para_mostrar(comparacion, [equipo_a, equipo_b]), hide_index=True,
                 use_container_width=True)

    st.subheader("Como local y como visitante")
    por_condicion = comparador.puntos_por_condicion(estadisticas, temporada, [equipo_a, equipo_b])
    st.altair_chart(graficos.grafico_puntos_condicion(
        por_condicion, [equipo_a, equipo_b], f"Puntos por partido de local y de visitante · {temporada}"),
        use_container_width=True)
    st.dataframe(por_condicion.rename(columns={"Condicion": "Condición", "PuntosPorPartido": "Puntos por partido"}),
                 hide_index=True, use_container_width=True)

    for equipo in [equipo_a, equipo_b]:
        if comparador.falta_dato_de_tiros(comparador.fila_equipo(estadisticas, temporada, equipo, condicion)):
            st.info(AVISO_TIROS_WEST_HAM)


# ---------------------------------------------------------------------------
# Local vs. visitante
# ---------------------------------------------------------------------------
def pagina_local_visitante(estadisticas, temporada):
    html(encabezado("Local vs. visitante", f"Cómo cambia un equipo dentro y fuera de casa · temporada {temporada}"))
    equipos = equipos_de_temporada(estadisticas, temporada)
    lider = equipos_por_defecto(estadisticas, temporada, 1)[0]
    equipo = st.selectbox("Equipo", equipos, index=equipos.index(lider))

    local = comparador.fila_equipo(estadisticas, temporada, equipo, "Local")
    visitante = comparador.fila_equipo(estadisticas, temporada, equipo, "Visitante")

    columnas = st.columns(4)
    for columna_pagina, nombre, fila in [(columnas[0], "Local", local), (columnas[1], "Visitante", visitante)]:
        columna_pagina.markdown(tarjeta(
            f"Puntos como {nombre.lower()}", f"{int(fila['Puntos'])} de {3 * int(fila['PJ'])}",
            f"{formato(comparador.porcentaje_de_puntos(fila), 1)} % de los puntos posibles · "
            f"{int(fila['V'])} V, {int(fila['E'])} E, {int(fila['D'])} D", nombre == "Local"), unsafe_allow_html=True)
    columnas[2].markdown(tarjeta("Goles", f"{int(local['GolesFavor'])} en casa · {int(visitante['GolesFavor'])} fuera",
                                 f"{formato(local['GolesFavorPorPartido'])} y {formato(visitante['GolesFavorPorPartido'])} "
                                 "por partido"), unsafe_allow_html=True)
    columnas[3].markdown(tarjeta("Goles recibidos",
                                 f"{int(local['GolesContra'])} en casa · {int(visitante['GolesContra'])} fuera",
                                 f"{formato(local['GolesContraPorPartido'])} y "
                                 f"{formato(visitante['GolesContraPorPartido'])} por partido"), unsafe_allow_html=True)

    total_puntos = int(local["Puntos"] + visitante["Puntos"])
    if total_puntos > 0:
        st.progress(int(local["Puntos"]) / total_puntos,
                    text=f"De sus {total_puntos} puntos, el {formato(100 * local['Puntos'] / total_puntos, 1)} % "
                         "los ganó en casa.")

    st.subheader("Conclusión calculada con los datos")
    st.markdown("\n".join(f"- {frase}" for frase in comparador.conclusiones_local_visitante(estadisticas, temporada, equipo)))

    datos = comparador.datos_por_partido(estadisticas, temporada, equipo)
    st.altair_chart(graficos.grafico_local_visitante_equipo(
        datos, f"{equipo} · promedios por partido de local y de visitante · {temporada}"))
    st.caption("Se comparan promedios por partido porque de local y de visitante se juegan los mismos "
               "partidos (19), y así las estadísticas de distinto tamaño se leen en su propio panel.")

    tabla = comparador.tabla_local_visitante(estadisticas, temporada, equipo)
    st.dataframe(comparador.para_mostrar(tabla, ["Local", "Visitante", "Diferencia"]), hide_index=True,
                 use_container_width=True)
    if comparador.falta_dato_de_tiros(visitante):
        st.info(AVISO_TIROS_WEST_HAM)


# ---------------------------------------------------------------------------
# Relaciones y correlaciones
# ---------------------------------------------------------------------------
def pagina_correlaciones(estadisticas, temporada):
    html(encabezado("Relaciones y correlaciones",
                    "Qué estadísticas suben y bajan juntas (un punto = un equipo en una temporada)"))
    izquierda, derecha = st.columns(2)
    opciones_alcance = ["Las cinco temporadas (100 equipo-temporada)", f"Solo {temporada} (20 equipos)"]
    alcance = izquierda.radio("Datos", opciones_alcance, horizontal=True)
    condicion = derecha.radio("Partidos", ["Total", "Local", "Visitante"], horizontal=True, key="condicion_corr")
    temporada_datos = None if alcance == opciones_alcance[0] else temporada
    tabla = correlaciones.preparar_tabla(estadisticas, condicion, temporada_datos)
    n = len(tabla)

    st.warning("**Correlación no es causalidad.** Una correlación alta dice que dos estadísticas suelen "
               "subir o bajar juntas, no que una cause la otra. Por ejemplo, la calidad de un equipo puede "
               "explicar a la vez que tire más y que gane más.")

    st.subheader("Las siete relaciones del proyecto")
    relaciones = correlaciones.tabla_relaciones(tabla)
    relaciones["r"] = [formato(r) for r in relaciones["r"]]
    st.dataframe(relaciones, hide_index=True, use_container_width=True)
    st.caption(f"Coeficiente de Pearson con n = {n}. Débil: |r| < 0,3 · moderada: hasta 0,7 · fuerte: más de 0,7. "
               "Todas las variables son promedios por partido de cada equipo en la temporada.")

    st.subheader("Gráfico de dispersión")
    nombres_relaciones = [f"{x} y {y.lower()}" for x, y in correlaciones.RELACIONES]
    elegida = st.selectbox("Relación", nombres_relaciones + ["Elegir otras variables"])
    if elegida == "Elegir otras variables":
        columna_x, columna_y = st.columns(2)
        variables = list(correlaciones.VARIABLES)
        nombre_x = columna_x.selectbox("Variable del eje horizontal", variables, index=5)
        nombre_y = columna_y.selectbox("Variable del eje vertical", variables, index=2)
    else:
        nombre_x, nombre_y = correlaciones.RELACIONES[nombres_relaciones.index(elegida)]

    if nombre_x == nombre_y:
        st.info("Elige dos variables diferentes: una variable siempre tiene r = 1 consigo misma.")
    else:
        datos = correlaciones.datos_dispersion(tabla, nombre_x, nombre_y)
        r = correlacion(datos["x"], datos["y"])
        recta = recta_tendencia(datos["x"], datos["y"]).rename(columns={"Valor": "x", "PuntosPorPartido": "y"})
        metrica, grafico = st.columns([1, 3])
        metrica.metric("Correlación de Pearson (r)", formato(r), f"relación {fuerza(r)} · n = {n}", delta_color="off")
        with grafico:
            st.altair_chart(graficos.grafico_dispersion_xy(
                datos, recta, nombre_x, nombre_y, f"{nombre_x} y {nombre_y.lower()} por partido · {condicion.lower()}",
                temporada if temporada_datos is None else None), use_container_width=True)
        st.info(correlaciones.explicar(r, nombre_x, nombre_y, n))
        if temporada_datos is None:
            st.caption(f"Los puntos de {temporada} se ven más fuertes. La línea discontinua es la recta de "
                       "mínimos cuadrados (np.polyfit).")

    st.subheader("Matriz de correlación")
    elegidas = st.multiselect("Variables de la matriz", list(correlaciones.VARIABLES),
                              default=list(correlaciones.VARIABLES))
    if len(elegidas) < 2:
        st.info("Elige al menos dos variables para calcular la matriz.")
        return
    matriz = correlaciones.matriz_correlacion(tabla, elegidas)
    st.altair_chart(graficos.grafico_mapa_calor(correlaciones.matriz_formato_largo(matriz), elegidas,
                                                f"Mapa de calor · {condicion.lower()} · n = {n}"))
    st.caption("Morado: relación positiva (suben juntas). Naranja: negativa (cuando una sube, la otra baja). "
               "Gris claro: casi sin relación. La diagonal vale 1 porque es cada variable consigo misma.")
    with st.expander("Ver la matriz como tabla"):
        st.dataframe(matriz.round(2), use_container_width=True)


# ---------------------------------------------------------------------------
# Récords históricos
# ---------------------------------------------------------------------------
def pagina_records(estadisticas, partidos, temporada):
    html(encabezado("Récords históricos", "Lo máximo de las cinco temporadas, de 2020/21 a 2024/25"))
    st.caption("Esta sección compara las cinco temporadas, así que no depende de la temporada elegida en la "
               f"barra lateral; las filas de {temporada} se resaltan en los gráficos.")
    tipo = st.radio("Tipo de récord", ["De una sola temporada", "Acumulado de las cinco temporadas",
                                       "Récords de partidos"], horizontal=True)

    if tipo == "Récords de partidos":
        mostrar_records_de_partidos(partidos)
        return

    nombre = st.selectbox("Récord", list(records.METRICAS_RECORD))
    columna, menor_es_mejor = records.METRICAS_RECORD[nombre]
    titulo_valor = nombre.replace("Más ", "").replace("Menos ", "").capitalize()

    if tipo == "De una sola temporada":
        izquierda, derecha = st.columns(2)
        todas = sorted(estadisticas["Temporada"].unique())
        temporadas = izquierda.multiselect("Temporadas incluidas", todas, default=todas)
        equipo = derecha.selectbox("Equipo", ["Todos"] + sorted(estadisticas["Equipo"].unique()))
        if not temporadas:
            st.info("Elige al menos una temporada.")
            return
        tabla = records.ranking_una_temporada(estadisticas, columna, menor_es_mejor, temporadas)
        primeros = tabla[tabla["Pos"] == 1]
        html(tarjeta(f"Récord · {nombre.lower()} en una temporada",
                     f"{int(primeros[columna].iloc[0])}",
                     "; ".join(f"{f['Equipo']} en {f['Temporada']}" for _, f in primeros.iterrows()), True))
        if equipo != "Todos":
            tabla = tabla[tabla["Equipo"] == equipo]
            st.caption(f"Temporadas de {equipo} y su posición entre todos los equipo-temporada incluidos.")
            if tabla.empty:
                st.info(f"{equipo} no jugó en las temporadas elegidas.")
                return
        else:
            tabla = tabla.head(10)
        tabla = tabla.assign(Etiqueta=tabla["Equipo"] + " · " + tabla["Temporada"],
                             Resaltado=tabla["Temporada"] == temporada)
        st.altair_chart(graficos.grafico_barras_ordenadas(
            tabla, "Etiqueta", columna, titulo_valor, f"{nombre} en una temporada"), use_container_width=True)
        st.dataframe(con_insignia(tabla.drop(columns=["Etiqueta", "Resaltado"])).rename(columns={columna: titulo_valor}),
                     hide_index=True, use_container_width=True, column_config=CONFIG_INSIGNIA)

        lideres = records.lideres_por_temporada(estadisticas, columna, menor_es_mejor)
        st.altair_chart(graficos.grafico_lideres_por_temporada(
            lideres, titulo_valor, f"{nombre}: el mejor de cada temporada"), use_container_width=True)
    else:
        tabla = records.ranking_acumulado(estadisticas, columna, menor_es_mejor)
        primeros = tabla[tabla["Pos"] == 1]
        html(tarjeta(f"Récord acumulado · {nombre.lower()}", f"{int(primeros[columna].iloc[0])}",
                     f"{lista_texto(primeros['Equipo'])} en las cinco temporadas", True))
        top = tabla.head(10)
        st.altair_chart(graficos.grafico_barras_ordenadas(
            top, "Equipo", columna, f"{titulo_valor} (suma de 5 temporadas)", f"{nombre} sumando las cinco temporadas"),
            use_container_width=True)
        st.dataframe(con_insignia(tabla).rename(columns={columna: titulo_valor}), hide_index=True,
                     use_container_width=True, column_config=CONFIG_INSIGNIA)
        if menor_es_mejor:
            st.caption("Solo se comparan los 13 equipos que jugaron las cinco temporadas: un equipo con menos "
                       "temporadas recibiría menos goles solo por haber jugado menos partidos.")
        else:
            st.caption("No todos los equipos jugaron las cinco temporadas (columna «Temporadas»): los "
                       "acumulados favorecen a los que jugaron más.")
    if columna in ["Tiros", "TirosArco"]:
        st.info(AVISO_TIROS_WEST_HAM)


def mostrar_records_de_partidos(partidos):
    """Tarjetas de los cuatro récords de partidos y tablas por temporada."""
    lista = records.records_de_partidos(partidos)
    columnas = st.columns(2)
    for indice, record in enumerate(lista):
        columnas[indice % 2].markdown(tarjeta(record["titulo"], record["valor"], record["texto"], True),
                                      unsafe_allow_html=True)
    for record in lista:
        if record["partidos"] is not None and len(record["partidos"]) > 1:
            with st.expander(f"{record['titulo']}: los {len(record['partidos'])} partidos"):
                st.dataframe(tabla_resumen(record["partidos"]), hide_index=True, use_container_width=True)

    st.subheader("Récords de partidos en cada temporada")
    st.dataframe(records.records_de_partidos_por_temporada(partidos), hide_index=True, use_container_width=True)

    st.subheader("Resultados más repetidos (1.900 partidos)")
    repetidos = records.resultados_mas_repetidos(partidos)
    st.altair_chart(graficos.grafico_barras_ordenadas(
        repetidos, "Resultado", "Partidos", "Partidos", "Resultados más frecuentes, sin importar quién ganó",
        nombre_etiqueta="Resultado"),
        use_container_width=True)


# ---------------------------------------------------------------------------
# Ranking personalizado
# ---------------------------------------------------------------------------
def pagina_ranking(estadisticas, temporada):
    html(encabezado("Ranking personalizado", f"Elige una estadística y ordena los 20 equipos · temporada {temporada}"))
    izquierda, derecha = st.columns(2)
    opcion = izquierda.selectbox("Estadística", list(ranking.OPCIONES_RANKING))
    ordenes = [ranking.ORDEN_DESCENDENTE, ranking.ORDEN_ASCENDENTE]
    # El orden por defecto pone primero al mejor; la clave cambia con la estadística para reiniciarlo.
    orden = derecha.radio("Orden", ordenes, index=ordenes.index(ranking.orden_recomendado(opcion)),
                          key=f"orden_{opcion}")

    datos_opcion = ranking.OPCIONES_RANKING[opcion]
    equipos_lideres, valor_lider = ranking.lider(estadisticas, temporada, opcion)
    valor_texto = formato(valor_lider) if isinstance(valor_lider, float) else str(valor_lider)
    explicacion = "el valor más bajo es el mejor" if datos_opcion["menor_es_mejor"] else "el valor más alto es el mejor"
    html(tarjeta(f"Líder · {opcion.lower()}", lista_texto(equipos_lideres), f"{valor_texto} · en esta categoría "
                 f"{explicacion}", True))

    tabla = ranking.ranking_personalizado(estadisticas, temporada, opcion, orden)
    es_promedio = datos_opcion["columna"].endswith("PorPartido")
    nombre_valor = {"Mejor rendimiento como local": "Puntos como local",
                    "Mejor rendimiento como visitante": "Puntos como visitante"}.get(
        opcion, opcion.replace("Más ", "").replace("Menos ", "").replace("Mayor ", "").capitalize())
    st.altair_chart(graficos.grafico_barras_ordenadas(
        tabla.assign(Resaltado=tabla["Equipo"].isin(equipos_lideres)), "Equipo", "Valor", nombre_valor,
        f"{opcion} · {temporada}", color=graficos.COLORES_CONDICION[datos_opcion["condicion"]],
        formato=".2f" if es_promedio else ""), use_container_width=True)
    st.dataframe(con_insignia(tabla).rename(columns={"Valor": nombre_valor}), hide_index=True,
                 use_container_width=True, column_config=CONFIG_INSIGNIA, height=740)
    st.caption("La posición sigue el orden elegido y los equipos empatados comparten posición. "
               "PJ, V, E y D corresponden a los partidos de la estadística (total, local o visitante).")
    if temporada == "2021/22" and datos_opcion["columna"] in ["Tiros", "TirosArco"]:
        st.info(AVISO_TIROS_WEST_HAM)


# ---------------------------------------------------------------------------
# Detector de sorpresas
# ---------------------------------------------------------------------------
def pagina_sorpresas(partidos_temporada, temporada):
    html(encabezado("Detector de sorpresas", f"Partidos en los que las estadísticas contrastan con el resultado · {temporada}"))
    equipos = sorted(set(partidos_temporada["HomeTeam"]))
    columna_1, columna_2, columna_3 = st.columns([3, 2, 2])
    criterio = columna_1.selectbox("Qué buscar", list(sorpresas.CRITERIOS))
    equipo = columna_2.selectbox("Equipo (opcional)", ["Todos"] + equipos)
    minimo = columna_3.slider("Diferencia mínima", 1, 25, 1,
                              help="Diferencia mínima en la estadística que define la sorpresa (tiros, tiros al "
                                   "arco o córners). En el empate es la suma de las tres diferencias.")
    st.caption(sorpresas.CRITERIOS[criterio])

    tabla, sin_datos = sorpresas.buscar_sorpresas(partidos_temporada, criterio,
                                                  None if equipo == "Todos" else equipo, minimo)
    if sin_datos:
        st.caption(f"{sin_datos} partido(s) no se revisan porque les falta el dato de tiros.")
    if tabla.empty:
        st.info("No hay partidos que cumplan estas condiciones. Prueba con una diferencia mínima más baja u otro equipo.")
        return

    st.markdown(f"**{len(tabla)} {'partido cumple' if len(tabla) == 1 else 'partidos cumplen'} el criterio.** "
                "Los más llamativos (mayor diferencia):")
    columnas = st.columns(3)
    for indice, (_, fila) in enumerate(tabla.head(6).iterrows()):
        columnas[indice % 3].markdown(tarjeta(f"{fila['Fecha']} · diferencia {fila['Diferencia']}",
                                              f"{fila['Local']} {fila['Resultado']} {fila['Visitante']}",
                                              fila["Por qué"], indice == 0), unsafe_allow_html=True)

    st.dataframe(tabla, hide_index=True, use_container_width=True,
                 column_config={"Por qué": st.column_config.TextColumn(width="large")})
    st.caption("Cada pareja de números es local - visitante. El detector solo describe qué estadísticas "
               "fueron mayores y el resultado: tener más tiros o córners no significa que un equipo haya "
               "sido mejor en todo el partido.")
