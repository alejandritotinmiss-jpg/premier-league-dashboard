"""Gráficos del dashboard, hechos con Altair.

Altair se instala junto con Streamlit, que lo usa para sus propios gráficos.
Lo usamos directamente porque permite controlar el orden de las barras, fijar
los colores de local y visitante, y mostrar información al pasar el ratón.
"""

import altair as alt
import pandas as pd

# Colores fijos: local siempre morado y visitante siempre naranja (pareja comprobada
# para personas con daltonismo). El total usa el morado oscuro del encabezado.
COLORES_CONDICION = {"Total": "#4b1d78", "Local": "#7c3aed", "Visitante": "#eb6834"}
# Colores para distinguir equipos, siempre en el mismo orden.
PALETA_EQUIPOS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]
COLOR_TEXTO = "#52514e"

ESCALA_CONDICION = alt.Scale(domain=["Local", "Visitante"],
                             range=[COLORES_CONDICION["Local"], COLORES_CONDICION["Visitante"]])


def grafico_puntos_por_equipo(datos, condicion, titulo):
    """Barras horizontales de puntos por equipo; los equipos elegidos se resaltan."""
    base = alt.Chart(datos).encode(
        x=alt.X("Puntos:Q", title="Puntos"),
        y=alt.Y("Equipo:N", sort="-x", title=None),
        tooltip=[alt.Tooltip("Posicion:Q", title="Posición"),
                 alt.Tooltip("Equipo:N"), alt.Tooltip("Puntos:Q")],
    )
    barras = base.mark_bar(color=COLORES_CONDICION[condicion], cornerRadiusEnd=4).encode(
        opacity=alt.condition("datum.Seleccionado", alt.value(1.0), alt.value(0.35)),
    )
    etiquetas = base.mark_text(align="left", dx=4, color=COLOR_TEXTO).encode(text="Puntos:Q")
    return (barras + etiquetas).properties(title=titulo, height=520)


def grafico_evolucion(datos, equipos, titulo):
    """Líneas de puntos acumulados por número de partido, una por equipo."""
    escala = alt.Scale(domain=equipos, range=PALETA_EQUIPOS[:len(equipos)])
    lineas = alt.Chart(datos).mark_line(strokeWidth=2, point=alt.OverlayMarkDef(size=28)).encode(
        x=alt.X("NumeroPartido:Q", title="Número de partido del equipo (orden por fecha)",
                scale=alt.Scale(domain=[1, 38])),
        y=alt.Y("PuntosAcumulados:Q", title="Puntos acumulados"),
        color=alt.Color("Equipo:N", scale=escala, legend=alt.Legend(title="Equipo", orient="top")),
        tooltip=[alt.Tooltip("Equipo:N"), alt.Tooltip("NumeroPartido:Q", title="Partido n.º"),
                 alt.Tooltip("Rival:N"), alt.Tooltip("Condicion:N", title="Condición"),
                 alt.Tooltip("Marcador:N"), alt.Tooltip("PuntosAcumulados:Q", title="Puntos acumulados")],
    )
    # Etiqueta directa al final de cada línea.
    finales = alt.Chart(datos).transform_filter("datum.NumeroPartido == 38").mark_text(
        align="left", dx=6, color=COLOR_TEXTO,
    ).encode(x="NumeroPartido:Q", y="PuntosAcumulados:Q", text="PuntosAcumulados:Q")
    return (lineas + finales).properties(title=titulo, height=420)


def grafico_dispersion(datos, recta, nombre_metrica, condicion, titulo):
    """Dispersión de una métrica frente a los puntos por partido, con recta de tendencia."""
    base = alt.Chart(datos).encode(
        x=alt.X("Valor:Q", title=f"{nombre_metrica} por partido", scale=alt.Scale(zero=False)),
        y=alt.Y("PuntosPorPartido:Q", title="Puntos por partido", scale=alt.Scale(zero=False)),
    )
    puntos = base.mark_circle(color=COLORES_CONDICION[condicion], stroke="white", strokeWidth=1).encode(
        size=alt.condition("datum.Seleccionado", alt.value(160), alt.value(60)),
        opacity=alt.condition("datum.Seleccionado", alt.value(1.0), alt.value(0.5)),
        tooltip=[alt.Tooltip("Equipo:N"), alt.Tooltip("Temporada:N"),
                 alt.Tooltip("Valor:Q", title=nombre_metrica, format=".2f"),
                 alt.Tooltip("PuntosPorPartido:Q", title="Puntos por partido", format=".2f")],
    )
    etiquetas = base.transform_filter("datum.Seleccionado").mark_text(
        align="left", dx=9, dy=-7, color=COLOR_TEXTO,
    ).encode(text="Equipo:N")
    tendencia = alt.Chart(recta).mark_line(color=COLOR_TEXTO, strokeWidth=1.5, strokeDash=[5, 3]).encode(
        x="Valor:Q", y="PuntosPorPartido:Q",
    )
    return (puntos + tendencia + etiquetas).properties(title=titulo, height=420)


def grafico_correlaciones(datos, titulo):
    """Barras agrupadas: correlación de cada métrica con los puntos, de local y de visitante."""
    base = alt.Chart(datos).encode(
        x=alt.X("Variable:N", title=None, sort=None, axis=alt.Axis(labelAngle=0)),
        xOffset=alt.XOffset("Condicion:N", sort=["Local", "Visitante"]),
        y=alt.Y("r:Q", title="Correlación (r) con puntos por partido", scale=alt.Scale(domain=[-1, 1])),
    )
    barras = base.mark_bar(cornerRadius=3).encode(
        color=alt.Color("Condicion:N", scale=ESCALA_CONDICION, legend=alt.Legend(title=None, orient="top")),
        tooltip=[alt.Tooltip("Variable:N"), alt.Tooltip("Condicion:N", title="Condición"),
                 alt.Tooltip("r:Q", format=".2f"), alt.Tooltip("n:Q", title="Observaciones")],
    )
    # Etiquetas encima de las barras positivas y debajo de las negativas.
    texto = alt.Text("r:Q", format=".2f")
    sobre_positivas = base.transform_filter("datum.r >= 0").mark_text(
        dy=-8, color=COLOR_TEXTO, fontSize=10).encode(text=texto)
    bajo_negativas = base.transform_filter("datum.r < 0").mark_text(
        dy=10, color=COLOR_TEXTO, fontSize=10).encode(text=texto)
    cero = alt.Chart(pd.DataFrame({"cero": [0]})).mark_rule(color=COLOR_TEXTO).encode(y="cero:Q")
    return alt.layer(barras, sobre_positivas, bajo_negativas, cero).properties(title=titulo, height=380)


def grafico_local_visitante(datos, nombre_metrica, titulo):
    """Barras agrupadas por equipo: una métrica de local y de visitante."""
    return alt.Chart(datos).mark_bar(cornerRadiusEnd=4).encode(
        x=alt.X("Equipo:N", title=None, axis=alt.Axis(labelAngle=0)),
        xOffset=alt.XOffset("Condicion:N", sort=["Local", "Visitante"]),
        y=alt.Y("Valor:Q", title=f"{nombre_metrica} por partido"),
        color=alt.Color("Condicion:N", scale=ESCALA_CONDICION, legend=alt.Legend(title=None, orient="top")),
        tooltip=[alt.Tooltip("Equipo:N"), alt.Tooltip("Condicion:N", title="Condición"),
                 alt.Tooltip("Valor:Q", title=nombre_metrica, format=".2f")],
    ).properties(title=titulo, height=380)


def grafico_ventaja_local(datos, temporada_elegida, titulo):
    """Barras agrupadas por temporada: puntos por partido de local y de visitante."""
    base = alt.Chart(datos).encode(
        x=alt.X("Temporada:N", title=None, axis=alt.Axis(labelAngle=0)),
        xOffset=alt.XOffset("Condicion:N", sort=["Local", "Visitante"]),
        y=alt.Y("PuntosPorPartido:Q", title="Puntos por partido (media de los 20 equipos)"),
    )
    barras = base.mark_bar(cornerRadiusEnd=4).encode(
        color=alt.Color("Condicion:N", scale=ESCALA_CONDICION, legend=alt.Legend(title=None, orient="top")),
        opacity=alt.condition(f"datum.Temporada == '{temporada_elegida}'", alt.value(1.0), alt.value(0.45)),
        tooltip=[alt.Tooltip("Temporada:N"), alt.Tooltip("Condicion:N", title="Condición"),
                 alt.Tooltip("PuntosPorPartido:Q", title="Puntos por partido", format=".2f")],
    )
    etiquetas = base.mark_text(dy=-8, color=COLOR_TEXTO, fontSize=10).encode(
        text=alt.Text("PuntosPorPartido:Q", format=".2f"),
    )
    return (barras + etiquetas).properties(title=titulo, height=360)


def grafico_tiros_arco_goles(datos, recta, titulo):
    """Dispersión de tiros al arco frente a goles por partido, con recta de tendencia."""
    base = alt.Chart(datos).encode(
        x=alt.X("TirosArcoPorPartido:Q", title="Tiros al arco por partido", scale=alt.Scale(zero=False)),
        y=alt.Y("GolesFavorPorPartido:Q", title="Goles a favor por partido", scale=alt.Scale(zero=False)),
    )
    puntos = base.mark_circle(color=COLORES_CONDICION["Local"], stroke="white", strokeWidth=1).encode(
        size=alt.condition("datum.Seleccionado", alt.value(160), alt.value(70)),
        opacity=alt.condition("datum.Seleccionado", alt.value(1.0), alt.value(0.55)),
        tooltip=[alt.Tooltip("Equipo:N"),
                 alt.Tooltip("TirosArcoPorPartido:Q", title="Tiros al arco por partido", format=".2f"),
                 alt.Tooltip("GolesFavorPorPartido:Q", title="Goles por partido", format=".2f")],
    )
    etiquetas = base.transform_filter("datum.Seleccionado").mark_text(
        align="left", dx=9, dy=-7, color=COLOR_TEXTO,
    ).encode(text="Equipo:N")
    tendencia = alt.Chart(recta).mark_line(color=COLOR_TEXTO, strokeWidth=1.5, strokeDash=[5, 3]).encode(
        x="TirosArcoPorPartido:Q", y="GolesFavorPorPartido:Q",
    )
    return (puntos + tendencia + etiquetas).properties(title=titulo, height=420)


def grafico_ranking(datos, nombre_metrica, condicion, titulo):
    """Barras horizontales de una métrica por equipo, de mayor a menor."""
    base = alt.Chart(datos).encode(
        x=alt.X("Valor:Q", title=f"{nombre_metrica} por partido"),
        y=alt.Y("Equipo:N", sort="-x", title=None),
        tooltip=[alt.Tooltip("Equipo:N"), alt.Tooltip("Valor:Q", title=nombre_metrica, format=".2f")],
    )
    barras = base.mark_bar(color=COLORES_CONDICION[condicion], cornerRadiusEnd=4).encode(
        opacity=alt.condition("datum.Seleccionado", alt.value(1.0), alt.value(0.4)),
    )
    etiquetas = base.mark_text(align="left", dx=4, color=COLOR_TEXTO).encode(
        text=alt.Text("Valor:Q", format=".2f"))
    return (barras + etiquetas).properties(title=titulo, height=520)


# ---------------------------------------------------------------------------
# Comparador de equipos y local contra visitante
# ---------------------------------------------------------------------------
COLORES_DOS_EQUIPOS = ["#2a78d6", "#eb6834"]   # azul y naranja (pareja comprobada para daltonismo)


def grafico_reparto(datos, equipo_a, equipo_b, titulo):
    """Barras 100 %: qué parte del total de los dos equipos tiene cada uno en cada estadística."""
    orden_equipos = alt.Order("orden:Q")
    datos = datos.assign(orden=[0 if e == equipo_a else 1 for e in datos["Equipo"]])
    escala = alt.Scale(domain=[equipo_a, equipo_b], range=COLORES_DOS_EQUIPOS)
    base = alt.Chart(datos).encode(
        y=alt.Y("Estadística:N", sort=None, title=None, axis=alt.Axis(labelLimit=200)),
        x=alt.X("Porcentaje:Q", stack="zero", title="Parte del total de los dos equipos (%)",
                scale=alt.Scale(domain=[0, 100])),
        order=orden_equipos,
    )
    barras = base.mark_bar(stroke="white", strokeWidth=2).encode(
        color=alt.Color("Equipo:N", scale=escala, legend=alt.Legend(title=None, orient="top")),
        tooltip=[alt.Tooltip("Estadística:N"), alt.Tooltip("Equipo:N"),
                 alt.Tooltip("Valor:Q", title="Valor real"),
                 alt.Tooltip("Porcentaje:Q", title="% del total", format=".1f")],
    )
    # El valor real se escribe dentro de cada parte de la barra.
    textos = base.mark_text(color="white", fontWeight="bold").encode(
        x=alt.X("centro:Q"), text=alt.Text("Valor:Q"),
    ).transform_window(
        acumulado="sum(Porcentaje)", groupby=["Estadística"], sort=[alt.SortField("orden")],
    ).transform_calculate(centro="datum.acumulado - datum.Porcentaje / 2")
    mitad = alt.Chart(pd.DataFrame({"x": [50]})).mark_rule(color=COLOR_TEXTO, strokeDash=[3, 3]).encode(x="x:Q")
    # Altura fija por fila para que se lean todas las etiquetas de las estadísticas.
    return alt.layer(barras, textos, mitad).properties(title=titulo, height=alt.Step(32))


def grafico_puntos_condicion(datos, equipos, titulo):
    """Puntos por partido de cada equipo como local y como visitante."""
    escala = alt.Scale(domain=equipos, range=COLORES_DOS_EQUIPOS[:len(equipos)])
    base = alt.Chart(datos).encode(
        x=alt.X("Condicion:N", title=None, sort=["Local", "Visitante"], axis=alt.Axis(labelAngle=0)),
        xOffset=alt.XOffset("Equipo:N", sort=equipos),
        y=alt.Y("PuntosPorPartido:Q", title="Puntos por partido", scale=alt.Scale(domain=[0, 3])),
    )
    barras = base.mark_bar(cornerRadiusEnd=4).encode(
        color=alt.Color("Equipo:N", scale=escala, legend=alt.Legend(title=None, orient="top")),
        tooltip=[alt.Tooltip("Equipo:N"), alt.Tooltip("Condicion:N", title="Condición"),
                 alt.Tooltip("PuntosPorPartido:Q", title="Puntos por partido", format=".2f"),
                 alt.Tooltip("Puntos:Q"), alt.Tooltip("V:Q", title="Victorias"),
                 alt.Tooltip("E:Q", title="Empates"), alt.Tooltip("D:Q", title="Derrotas")],
    )
    etiquetas = base.mark_text(dy=-8, color=COLOR_TEXTO).encode(text=alt.Text("PuntosPorPartido:Q", format=".2f"))
    return (barras + etiquetas).properties(title=titulo, height=320)


def grafico_local_visitante_equipo(datos, titulo):
    """Un panel por estadística con el promedio por partido de local y de visitante."""
    # En un gráfico con paneles (facet) los datos van en el gráfico de arriba, no en cada capa.
    base = alt.Chart().encode(
        x=alt.X("Condicion:N", title=None, sort=["Local", "Visitante"], axis=alt.Axis(labelAngle=0)),
        y=alt.Y("Valor:Q", title="Por partido"),
    )
    barras = base.mark_bar(cornerRadiusEnd=4).encode(
        color=alt.Color("Condicion:N", scale=ESCALA_CONDICION, legend=alt.Legend(title=None, orient="top")),
        tooltip=[alt.Tooltip("Estadística:N"), alt.Tooltip("Condicion:N", title="Condición"),
                 alt.Tooltip("Valor:Q", title="Por partido", format=".2f")],
    )
    etiquetas = base.mark_text(dy=-7, color=COLOR_TEXTO, fontSize=10).encode(text=alt.Text("Valor:Q", format=".2f"))
    return alt.layer(barras, etiquetas, data=datos).properties(width=105, height=150).facet(
        facet=alt.Facet("Estadística:N", title=None, sort=list(dict.fromkeys(datos["Estadística"]))), columns=5,
    ).resolve_scale(y="independent").properties(title=titulo)


# ---------------------------------------------------------------------------
# Relaciones y correlaciones
# ---------------------------------------------------------------------------
def grafico_mapa_calor(datos, nombres, titulo):
    """Mapa de calor de la matriz de correlación: naranja negativo, gris cero, morado positivo."""
    # interpolate="lab" mezcla los colores sin pasar por tonos rosados.
    escala = alt.Scale(domain=[-1, 0, 1], range=["#eb6834", "#f1eff4", "#5b21b6"], interpolate="lab")
    base = alt.Chart(datos).encode(
        x=alt.X("Variable 2:N", sort=nombres, title=None, axis=alt.Axis(labelAngle=-40)),
        y=alt.Y("Variable 1:N", sort=nombres, title=None),
    )
    celdas = base.mark_rect(stroke="white", strokeWidth=2).encode(
        color=alt.Color("r:Q", scale=escala, legend=alt.Legend(title="r")),
        tooltip=[alt.Tooltip("Variable 1:N"), alt.Tooltip("Variable 2:N"), alt.Tooltip("r:Q", format=".2f")],
    )
    # Texto blanco sobre los colores fuertes y oscuro sobre los suaves.
    textos = base.mark_text(fontSize=11).encode(
        text=alt.Text("r:Q", format=".2f"),
        color=alt.condition("abs(datum.r) >= 0.6", alt.value("white"), alt.value("#1f1235")),
    )
    lado = max(320, 52 * len(nombres))
    return (celdas + textos).properties(title=titulo, width=lado, height=lado)


def grafico_dispersion_xy(datos, recta, nombre_x, nombre_y, titulo, temporada_resaltada=None):
    """Dispersión de dos variables (un punto por equipo-temporada) con recta de tendencia."""
    datos = datos.assign(Resaltado=(datos["Temporada"] == temporada_resaltada))
    base = alt.Chart(datos).encode(
        x=alt.X("x:Q", title=f"{nombre_x} por partido", scale=alt.Scale(zero=False)),
        y=alt.Y("y:Q", title=f"{nombre_y} por partido", scale=alt.Scale(zero=False)),
    )
    puntos = base.mark_circle(size=70, color=COLORES_CONDICION["Local"], stroke="white", strokeWidth=1).encode(
        opacity=alt.condition("datum.Resaltado", alt.value(1.0), alt.value(0.55)),
        tooltip=[alt.Tooltip("Equipo:N"), alt.Tooltip("Temporada:N"),
                 alt.Tooltip("x:Q", title=nombre_x, format=".2f"), alt.Tooltip("y:Q", title=nombre_y, format=".2f")],
    )
    tendencia = alt.Chart(recta).mark_line(color=COLOR_TEXTO, strokeWidth=1.5, strokeDash=[5, 3]).encode(
        x="x:Q", y="y:Q")
    return (puntos + tendencia).properties(title=titulo, height=400)


# ---------------------------------------------------------------------------
# Récords históricos y ranking personalizado
# ---------------------------------------------------------------------------
def grafico_barras_ordenadas(datos, columna_etiqueta, columna_valor, titulo_eje, titulo,
                             color=COLORES_CONDICION["Total"], formato="", nombre_etiqueta="Equipo"):
    """Barras horizontales en el mismo orden de la tabla (la primera fila arriba).

    Si hay una columna "Resaltado", las filas con True se ven más fuertes.
    """
    orden = datos[columna_etiqueta].tolist()
    # Si no hay columna "Resaltado" o ninguna fila está resaltada, todas se ven normales.
    if "Resaltado" not in datos.columns or not datos["Resaltado"].any():
        datos = datos.assign(Resaltado=True)
    base = alt.Chart(datos).encode(
        y=alt.Y(f"{columna_etiqueta}:N", sort=orden, title=None),
        x=alt.X(f"{columna_valor}:Q", title=titulo_eje),
        tooltip=[alt.Tooltip(f"{columna_etiqueta}:N", title=nombre_etiqueta),
                 alt.Tooltip(f"{columna_valor}:Q", title=titulo_eje, format=formato)],
    )
    barras = base.mark_bar(color=color, cornerRadiusEnd=4).encode(
        opacity=alt.condition("datum.Resaltado", alt.value(1.0), alt.value(0.4)),
    )
    etiquetas = base.mark_text(align="left", dx=4, color=COLOR_TEXTO).encode(
        text=alt.Text(f"{columna_valor}:Q", format=formato))
    altura = max(220, 26 * len(datos))
    return (barras + etiquetas).properties(title=titulo, height=altura)


def grafico_lideres_por_temporada(datos, titulo_eje, titulo):
    """El mejor valor de cada temporada, con el nombre del equipo encima de la barra."""
    base = alt.Chart(datos).encode(
        x=alt.X("Temporada:N", title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("Valor:Q", title=titulo_eje),
        tooltip=[alt.Tooltip("Temporada:N"), alt.Tooltip("Equipo:N"), alt.Tooltip("Valor:Q", title=titulo_eje)],
    )
    barras = base.mark_bar(color=COLORES_CONDICION["Local"], cornerRadiusEnd=4, size=46)
    valores = base.mark_text(dy=-8, color=COLOR_TEXTO, fontWeight="bold").encode(text="Valor:Q")
    equipos = base.mark_text(dy=-22, color=COLOR_TEXTO, fontSize=10).encode(text="Equipo:N")
    return alt.layer(barras, valores, equipos).properties(title=titulo, height=320)
