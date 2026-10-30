"""Comparador de dos equipos y análisis de un equipo como local y como visitante.

Todo sale de estadisticas_equipo_temporada.csv, que ya tiene una fila por equipo,
temporada y condición (Total, Local o Visitante). Así cada partido se cuenta una
sola vez por equipo.
"""

import pandas as pd

from src.tablero import filtrar

# Estadísticas que se comparan: nombre visible -> columna de la tabla.
ESTADISTICAS_EQUIPO = {
    "Goles anotados": "GolesFavor",
    "Goles recibidos": "GolesContra",
    "Partidos ganados": "V",
    "Partidos empatados": "E",
    "Partidos perdidos": "D",
    "Puntos": "Puntos",
    "Goles por partido": "GolesFavorPorPartido",
    "Tiros": "Tiros",
    "Tiros al arco": "TirosArco",
    "Córners": "Corners",
    "Faltas cometidas": "Faltas",
    "Tarjetas amarillas": "Amarillas",
    "Tarjetas rojas": "Rojas",
}

# Las mismas estadísticas expresadas por partido, para comparar local y visitante.
ESTADISTICAS_POR_PARTIDO = {
    "Goles anotados": "GolesFavorPorPartido",
    "Goles recibidos": "GolesContraPorPartido",
    "Puntos": "PuntosPorPartido",
    "Tiros": "TirosPorPartido",
    "Tiros al arco": "TirosArcoPorPartido",
    "Córners": "CornersPorPartido",
    "Faltas cometidas": "FaltasPorPartido",
    "Tarjetas amarillas": "AmarillasPorPartido",
    "Tarjetas rojas": "RojasPorPartido",
}


def fila_equipo(estadisticas, temporada, equipo, condicion="Total"):
    """Fila de un equipo en una temporada y condición, o None si no jugó esa temporada."""
    tabla = filtrar(estadisticas, temporada, condicion)
    tabla = tabla[tabla["Equipo"] == equipo]
    if tabla.empty:
        return None
    return tabla.iloc[0]


def falta_dato_de_tiros(fila):
    """True si al equipo le falta el dato de tiros de algún partido."""
    return fila["PartidosConTiros"] < fila["PJ"]


def redondear(valor, columna):
    """Los promedios se muestran con 2 decimales y los totales como números enteros."""
    if columna.endswith("PorPartido"):
        return round(float(valor), 2)
    return int(valor)


def tabla_comparacion(estadisticas, temporada, equipo_a, equipo_b, condicion="Total"):
    """Una fila por estadística con el valor de cada equipo y cuál tiene el valor más alto."""
    fila_a = fila_equipo(estadisticas, temporada, equipo_a, condicion)
    fila_b = fila_equipo(estadisticas, temporada, equipo_b, condicion)
    filas = []
    for nombre, columna in ESTADISTICAS_EQUIPO.items():
        valor_a = redondear(fila_a[columna], columna)
        valor_b = redondear(fila_b[columna], columna)
        if valor_a > valor_b:
            mas_alto = equipo_a
        elif valor_b > valor_a:
            mas_alto = equipo_b
        else:
            mas_alto = "Igual"
        filas.append({"Estadística": nombre, equipo_a: valor_a, equipo_b: valor_b, "Más alto": mas_alto})
    return pd.DataFrame(filas)


def reparto_por_estadistica(comparacion, equipo_a, equipo_b):
    """Qué parte del total de los dos equipos tiene cada uno en cada estadística (en %).

    Sirve para dibujar en un mismo gráfico estadísticas de tamaños muy distintos
    (por ejemplo 500 tiros y 3 tarjetas rojas). Si los dos tienen 0, la fila no se dibuja.
    """
    filas = []
    for _, fila in comparacion.iterrows():
        suma = fila[equipo_a] + fila[equipo_b]
        if suma == 0:
            continue
        for equipo in [equipo_a, equipo_b]:
            filas.append({"Estadística": fila["Estadística"], "Equipo": equipo,
                          "Valor": fila[equipo], "Porcentaje": 100 * fila[equipo] / suma})
    return pd.DataFrame(filas)


def puntos_por_condicion(estadisticas, temporada, equipos):
    """Puntos por partido de varios equipos como local y como visitante."""
    filas = []
    for equipo in equipos:
        for condicion in ["Local", "Visitante"]:
            fila = fila_equipo(estadisticas, temporada, equipo, condicion)
            filas.append({"Equipo": equipo, "Condicion": condicion,
                          "PuntosPorPartido": round(float(fila["PuntosPorPartido"]), 2),
                          "Puntos": int(fila["Puntos"]), "V": int(fila["V"]), "E": int(fila["E"]),
                          "D": int(fila["D"]), "GF": int(fila["GolesFavor"]), "GC": int(fila["GolesContra"])})
    return pd.DataFrame(filas)


# ---------------------------------------------------------------------------
# Un equipo como local y como visitante
# ---------------------------------------------------------------------------
def tabla_local_visitante(estadisticas, temporada, equipo):
    """Totales de un equipo en casa y fuera, con la diferencia (local - visitante)."""
    local = fila_equipo(estadisticas, temporada, equipo, "Local")
    visitante = fila_equipo(estadisticas, temporada, equipo, "Visitante")
    filas = []
    for nombre, columna in ESTADISTICAS_EQUIPO.items():
        valor_local = redondear(local[columna], columna)
        valor_visitante = redondear(visitante[columna], columna)
        filas.append({"Estadística": nombre, "Local": valor_local, "Visitante": valor_visitante,
                      "Diferencia": round(valor_local - valor_visitante, 2)})
    return pd.DataFrame(filas)


def datos_por_partido(estadisticas, temporada, equipo):
    """Promedios por partido de local y de visitante (formato largo para el gráfico)."""
    filas = []
    for condicion in ["Local", "Visitante"]:
        fila = fila_equipo(estadisticas, temporada, equipo, condicion)
        for nombre, columna in ESTADISTICAS_POR_PARTIDO.items():
            filas.append({"Estadística": nombre, "Condicion": condicion,
                          "Valor": round(float(fila[columna]), 2)})
    return pd.DataFrame(filas)


def porcentaje_de_puntos(fila):
    """Porcentaje de los puntos posibles que consiguió (3 por partido)."""
    return 100 * fila["Puntos"] / (3 * fila["PJ"])


def ventaja_media_de_la_liga(estadisticas, temporada):
    """Diferencia media de puntos por partido entre local y visitante de los 20 equipos."""
    local = filtrar(estadisticas, temporada, "Local")["PuntosPorPartido"].mean()
    visitante = filtrar(estadisticas, temporada, "Visitante")["PuntosPorPartido"].mean()
    return local - visitante


def comparar_texto(valor_local, valor_visitante, mas, menos, igual):
    """Elige la frase correcta según qué valor es mayor."""
    if valor_local > valor_visitante:
        return mas
    elif valor_local < valor_visitante:
        return menos
    return igual


def conclusiones_local_visitante(estadisticas, temporada, equipo):
    """Frases calculadas con los datos reales: nunca afirman algo que los números no digan."""
    local = fila_equipo(estadisticas, temporada, equipo, "Local")
    visitante = fila_equipo(estadisticas, temporada, equipo, "Visitante")
    frases = []

    puntos_l, puntos_v = int(local["Puntos"]), int(visitante["Puntos"])
    frases.append(comparar_texto(
        puntos_l, puntos_v,
        f"{equipo} obtuvo más puntos como local ({puntos_l}) que como visitante ({puntos_v}) en {temporada}.",
        f"{equipo} obtuvo más puntos como visitante ({puntos_v}) que como local ({puntos_l}) en {temporada}.",
        f"{equipo} obtuvo los mismos puntos como local y como visitante ({puntos_l}) en {temporada}."))

    gf_l, gf_v = int(local["GolesFavor"]), int(visitante["GolesFavor"])
    frases.append(comparar_texto(
        gf_l, gf_v,
        f"Marcó más goles en casa ({gf_l}) que fuera ({gf_v}).",
        f"Marcó más goles fuera ({gf_v}) que en casa ({gf_l}).",
        f"Marcó los mismos goles en casa y fuera ({gf_l})."))

    gc_l, gc_v = int(local["GolesContra"]), int(visitante["GolesContra"])
    frases.append(comparar_texto(
        gc_l, gc_v,
        f"Recibió más goles en casa ({gc_l}) que fuera ({gc_v}).",
        f"Recibió más goles fuera ({gc_v}) que en casa ({gc_l}).",
        f"Recibió los mismos goles en casa y fuera ({gc_l})."))

    # Ventaja de local = puntos por partido en casa - puntos por partido fuera.
    ventaja_equipo = round(float(local["PuntosPorPartido"] - visitante["PuntosPorPartido"]), 2)
    ventaja_liga = round(ventaja_media_de_la_liga(estadisticas, temporada), 2)
    frases.append(frase_ventaja(f"{equipo} sumó", ventaja_equipo))
    frases.append(frase_ventaja("En promedio, los equipos de la liga sumaron", ventaja_liga))
    if ventaja_equipo > ventaja_liga:
        frases.append(f"Por eso, la ventaja de jugar en casa de {equipo} fue mayor que la media de la liga.")
    elif ventaja_equipo < ventaja_liga:
        frases.append(f"Por eso, la ventaja de jugar en casa de {equipo} fue menor que la media de la liga.")
    else:
        frases.append(f"La ventaja de jugar en casa de {equipo} fue igual a la media de la liga.")
    return frases


def frase_ventaja(sujeto, ventaja):
    """Describe una diferencia de puntos por partido entre local y visitante según su signo."""
    texto = f"{abs(ventaja):.2f}".replace(".", ",")
    if ventaja > 0:
        return f"{sujeto} {texto} puntos por partido más en casa que fuera."
    elif ventaja < 0:
        return f"{sujeto} {texto} puntos por partido más fuera que en casa."
    return f"{sujeto} los mismos puntos por partido en casa y fuera."


def formatear_numero(valor):
    """Totales sin decimales y promedios con dos decimales y coma: 86 o 2,26."""
    if float(valor).is_integer():
        return f"{int(valor)}"
    return f"{valor:.2f}".replace(".", ",")


def para_mostrar(tabla, columnas):
    """Copia de la tabla con los números de esas columnas escritos como texto."""
    tabla = tabla.copy()
    for columna in columnas:
        tabla[columna] = [formatear_numero(valor) for valor in tabla[columna]]
    return tabla
