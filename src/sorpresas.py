"""Detector de sorpresas: partidos en los que algunas estadísticas contrastan con el resultado.

El detector solo describe qué estadísticas fueron mayores y cuál fue el resultado.
No dice que un equipo "fue mejor": tener más tiros o córners no significa eso.
"""

import pandas as pd

from src.partidos import fecha_texto, marcador

# Estadísticas del partido: nombre -> (columna del local, columna del visitante).
COLUMNAS = {
    "tiros": ("HS", "AS"),
    "tiros al arco": ("HST", "AST"),
    "córners": ("HC", "AC"),
}

CRITERIOS = {
    "Perdió con más tiros": "Un equipo hizo más tiros que su rival y perdió.",
    "Perdió con más tiros al arco": "Un equipo hizo más tiros al arco que su rival y perdió.",
    "Ganó con menos tiros": "Un equipo hizo menos tiros que su rival y ganó.",
    "No ganó con más córners": "Un equipo sacó más córners que su rival y perdió o empató.",
    "Empató con más tiros, tiros al arco y córners": (
        "Un equipo tuvo más tiros, más tiros al arco y más córners que su rival y el partido terminó empatado."),
}


def valores(fila, estadistica):
    """(valor del local, valor del visitante) de una estadística en un partido."""
    local, visitante = COLUMNAS[estadistica]
    return int(fila[local]), int(fila[visitante])


def lado_con_mas(fila, estadistica):
    """'local', 'visitante' o None (si tuvieron lo mismo)."""
    local, visitante = valores(fila, estadistica)
    if local > visitante:
        return "local"
    elif visitante > local:
        return "visitante"
    return None


def resultado_de(fila, lado):
    """'ganó', 'empató' o 'perdió' para el lado indicado."""
    if fila["FTHG"] == fila["FTAG"]:
        return "empató"
    gano_local = fila["FTHG"] > fila["FTAG"]
    if (lado == "local") == gano_local:
        return "ganó"
    return "perdió"


def otro_lado(lado):
    return "visitante" if lado == "local" else "local"


def equipo_de(fila, lado):
    return fila["HomeTeam"] if lado == "local" else fila["AwayTeam"]


def revisar_partido(fila, criterio):
    """Si el partido cumple el criterio devuelve (protagonista, diferencia); si no, None.

    El protagonista es el lado del que habla la explicación. La diferencia sirve para
    ordenar: cuanto mayor, más llamativo es el contraste.
    """
    if criterio == "Perdió con más tiros":
        lado = lado_con_mas(fila, "tiros")
        if lado and resultado_de(fila, lado) == "perdió":
            return lado, abs(valores(fila, "tiros")[0] - valores(fila, "tiros")[1])
    elif criterio == "Perdió con más tiros al arco":
        lado = lado_con_mas(fila, "tiros al arco")
        if lado and resultado_de(fila, lado) == "perdió":
            return lado, abs(valores(fila, "tiros al arco")[0] - valores(fila, "tiros al arco")[1])
    elif criterio == "Ganó con menos tiros":
        lado_mas = lado_con_mas(fila, "tiros")
        if lado_mas and resultado_de(fila, lado_mas) == "perdió":
            return otro_lado(lado_mas), abs(valores(fila, "tiros")[0] - valores(fila, "tiros")[1])
    elif criterio == "No ganó con más córners":
        lado = lado_con_mas(fila, "córners")
        if lado and resultado_de(fila, lado) != "ganó":
            return lado, abs(valores(fila, "córners")[0] - valores(fila, "córners")[1])
    elif criterio == "Empató con más tiros, tiros al arco y córners":
        lados = [lado_con_mas(fila, estadistica) for estadistica in COLUMNAS]
        if fila["FTHG"] == fila["FTAG"] and lados[0] is not None and lados.count(lados[0]) == 3:
            diferencia = sum(abs(valores(fila, e)[0] - valores(fila, e)[1]) for e in COLUMNAS)
            return lados[0], diferencia
    return None


def comparacion_texto(fila, lado, estadistica):
    """Por ejemplo: '25 tiros frente a 6'."""
    local, visitante = valores(fila, estadistica)
    propio, rival = (local, visitante) if lado == "local" else (visitante, local)
    return f"{propio} {estadistica} frente a {rival}"


def explicar(fila, criterio, lado):
    """Explicación exacta: qué estadísticas fueron mayores o menores y cuál fue el resultado."""
    equipo = equipo_de(fila, lado)
    rival = equipo_de(fila, otro_lado(lado))
    final = f"{marcador(fila)}"
    if criterio == "Perdió con más tiros":
        return f"{equipo} hizo {comparacion_texto(fila, lado, 'tiros')} de {rival}, pero perdió: {final}."
    if criterio == "Perdió con más tiros al arco":
        return f"{equipo} hizo {comparacion_texto(fila, lado, 'tiros al arco')} de {rival}, pero perdió: {final}."
    if criterio == "Ganó con menos tiros":
        return f"{equipo} hizo {comparacion_texto(fila, lado, 'tiros')} de {rival}, y aun así ganó: {final}."
    if criterio == "No ganó con más córners":
        verbo = "empató" if resultado_de(fila, lado) == "empató" else "perdió"
        return f"{equipo} sacó {comparacion_texto(fila, lado, 'córners')} de {rival}, pero {verbo}: {final}."
    partes = []
    for estadistica in COLUMNAS:
        local, visitante = valores(fila, estadistica)
        propio, ajeno = (local, visitante) if lado == "local" else (visitante, local)
        partes.append(f"más {estadistica} ({propio} contra {ajeno})")
    lista = ", ".join(partes[:-1]) + " y " + partes[-1]
    return f"{equipo} tuvo {lista} que {rival}, y el partido terminó empatado: {final}."


def texto_pareja(fila, columna_local, columna_visitante):
    return f"{int(fila[columna_local])} - {int(fila[columna_visitante])}"


def buscar_sorpresas(partidos_temporada, criterio, equipo=None, diferencia_minima=1):
    """Partidos que cumplen el criterio, del más llamativo al menos llamativo.

    Los partidos sin dato de tiros se dejan fuera (no se puede saber quién tiró más).
    Devuelve la tabla y cuántos partidos se dejaron fuera por falta de datos.
    """
    tabla = partidos_temporada
    if equipo:
        tabla = tabla[(tabla["HomeTeam"] == equipo) | (tabla["AwayTeam"] == equipo)]
    columnas_necesarias = ["HS", "AS", "HST", "AST", "HC", "AC"]
    sin_datos = int(tabla[columnas_necesarias].isna().any(axis=1).sum())
    tabla = tabla.dropna(subset=columnas_necesarias)

    filas = []
    for _, fila in tabla.iterrows():
        encontrado = revisar_partido(fila, criterio)
        if encontrado is None:
            continue
        lado, diferencia = encontrado
        if diferencia < diferencia_minima:
            continue
        filas.append({
            "Fecha": fecha_texto(fila["Date"]),
            "Local": fila["HomeTeam"],
            "Resultado": f"{int(fila['FTHG'])} - {int(fila['FTAG'])}",
            "Visitante": fila["AwayTeam"],
            "Tiros": texto_pareja(fila, "HS", "AS"),
            "Tiros al arco": texto_pareja(fila, "HST", "AST"),
            "Córners": texto_pareja(fila, "HC", "AC"),
            "Faltas": texto_pareja(fila, "HF", "AF"),
            "Amarillas": texto_pareja(fila, "HY", "AY"),
            "Rojas": texto_pareja(fila, "HR", "AR"),
            "Diferencia": diferencia,
            "Por qué": explicar(fila, criterio, lado),
            "_fecha": fila["Date"],
        })
    resultado = pd.DataFrame(filas)
    if resultado.empty:
        return resultado, sin_datos
    resultado = resultado.sort_values(["Diferencia", "_fecha"], ascending=[False, True])
    return resultado.drop(columns="_fecha").reset_index(drop=True), sin_datos


def resumen_criterios(partidos_temporada):
    """Cuántos partidos de la temporada cumplen cada criterio."""
    filas = []
    for criterio in CRITERIOS:
        tabla, _ = buscar_sorpresas(partidos_temporada, criterio)
        filas.append({"Criterio": criterio, "Partidos": len(tabla)})
    return pd.DataFrame(filas)
