"""Asistente basado en reglas: responde preguntas sobre los partidos de una temporada.

No usa un modelo de lenguaje. Reconoce los equipos y el tipo de pregunta por palabras
clave y busca la respuesta en los datos de la temporada elegida.
"""

import difflib
import re

from src.curiosidades import describir_partidos
from src.equipos import EQUIPOS, normalizar
from src.partidos import (enfrentamientos, fecha_texto, ganador, goles_de, marcador,
                          partidos_de_equipo, tabla_resumen, valor_de)

# Palabra clave -> (nombre de la estadística, columna local, columna visitante).
# El orden importa: "tiros al arco" debe revisarse antes que "tiros".
ESTADISTICAS = [
    ("tiros al arco", ("Tiros al arco", "HST", "AST")),
    ("tiros a puerta", ("Tiros al arco", "HST", "AST")),
    ("remates al arco", ("Tiros al arco", "HST", "AST")),
    ("tiros", ("Tiros", "HS", "AS")),
    ("remates", ("Tiros", "HS", "AS")),
    ("corner", ("Córners", "HC", "AC")),
    ("tiros de esquina", ("Córners", "HC", "AC")),
    ("faltas", ("Faltas", "HF", "AF")),
    ("amarillas", ("Tarjetas amarillas", "HY", "AY")),
    ("rojas", ("Tarjetas rojas", "HR", "AR")),
    ("expulsion", ("Tarjetas rojas", "HR", "AR")),
    ("tarjetas", ("Tarjetas", None, None)),
    ("goles", ("Goles", "FTHG", "FTAG")),
]

EJEMPLOS = [
    "¿Cuánto quedó el Man City contra Liverpool?",
    "¿Cuántos partidos ganó el Chelsea?",
    "¿Cuál fue el partido con más goles?",
    "¿Qué equipo recibió más tarjetas?",
    "¿Cuántos tiros al arco tuvo el Arsenal contra el Tottenham?",
]


def respuesta(texto, tabla=None, tipo="respuesta"):
    """Empaqueta la respuesta del asistente."""
    return {"tipo": tipo, "texto": texto, "tabla": tabla}


def encontrar_equipos(texto):
    """Equipos mencionados en el texto (ya normalizado), en el orden en que aparecen."""
    encontrados = []  # (inicio, fin, equipo)
    for equipo, datos in EQUIPOS.items():
        for alias in datos["alias"]:
            patron = r"\b" + re.escape(normalizar(alias)) + r"\b"
            for coincidencia in re.finditer(patron, texto):
                encontrados.append((coincidencia.start(), coincidencia.end(), equipo))

    # Si un alias corto queda dentro de uno más largo se descarta
    # (por ejemplo, "city" dentro de "leicester city").
    validos = []
    for inicio, fin, equipo in encontrados:
        dentro_de_otro = any(i <= inicio and fin <= f and (f - i) > (fin - inicio)
                             for i, f, _ in encontrados)
        if not dentro_de_otro:
            validos.append((inicio, equipo))

    equipos = []
    for _, equipo in sorted(validos):
        if equipo not in equipos:
            equipos.append(equipo)
    if equipos:
        return equipos
    return equipos_parecidos(texto)


def equipos_parecidos(texto):
    """Busca equipos escritos con pequeños errores, por ejemplo 'liverpol' o 'arsenl'."""
    todos_los_alias = {}
    for equipo, datos in EQUIPOS.items():
        for alias in datos["alias"]:
            if len(alias) >= 5:
                todos_los_alias[normalizar(alias)] = equipo
    palabras = re.findall(r"[a-z]+", texto)
    candidatos = palabras + [f"{a} {b}" for a, b in zip(palabras, palabras[1:])]
    equipos = []
    for candidato in candidatos:
        if len(candidato) < 5:
            continue
        parecido = difflib.get_close_matches(candidato, list(todos_los_alias), n=1, cutoff=0.82)
        if parecido and todos_los_alias[parecido[0]] not in equipos:
            equipos.append(todos_los_alias[parecido[0]])
    return equipos


def estadistica_pedida(texto):
    """Estadística mencionada en la pregunta, o None."""
    for palabra, datos in ESTADISTICAS:
        if palabra in texto:
            return datos
    return None


def partidos_con_mas(tabla, estadistica):
    """Partidos con el valor más alto de una estadística sumando los dos equipos."""
    nombre, local, visitante = estadistica or ("Goles", "FTHG", "FTAG")
    if local is None:  # tarjetas = amarillas + rojas
        total = tabla["HY"] + tabla["HR"] + tabla["AY"] + tabla["AR"]
    else:
        tabla = tabla.dropna(subset=[local, visitante])
        total = tabla[local] + tabla[visitante]
    return nombre, tabla[total == total.max()], int(total.max())


def hay_superlativo(texto):
    return "mas " in texto or "mayor" in texto or "maximo" in texto


def responder(pregunta, partidos_temporada, temporada):
    """Responde una pregunta usando solo los partidos de la temporada elegida."""
    texto = normalizar(pregunta)
    texto = re.sub(r"[¿?¡!.,;:]", " ", texto)
    if not texto.strip():
        return respuesta("Escribe una pregunta sobre los partidos de la temporada.", tipo="ayuda")

    if "manchester" in texto and not re.search(r"manchester (city|united|utd)", texto):
        return respuesta("¿Te refieres al **Manchester City** o al **Manchester United**? "
                         "Escribe el nombre completo para buscar el partido correcto.", tipo="aclaracion")

    equipos = encontrar_equipos(texto)
    equipos_temporada = set(partidos_temporada["HomeTeam"])
    fuera = [e for e in equipos if e not in equipos_temporada]
    if fuera:
        verbo = "no jugó" if len(fuera) == 1 else "no jugaron"
        return respuesta(f"{' y '.join(fuera)} {verbo} la Premier League en {temporada}. "
                         "Elige otra temporada en la barra lateral o pregunta por otro equipo.",
                         tipo="sin_datos")

    estadistica = estadistica_pedida(texto)

    if len(equipos) >= 3:
        return respuesta("Mencionaste más de dos equipos. Pregunta por uno o por un enfrentamiento "
                         "entre dos equipos.", tipo="aclaracion")
    if len(equipos) == 2:
        return responder_enfrentamiento(texto, partidos_temporada, temporada, equipos, estadistica)
    if len(equipos) == 1:
        return responder_equipo(texto, partidos_temporada, temporada, equipos[0], estadistica)
    if hay_superlativo(texto) or "goleada" in texto or "campeon" in texto:
        return responder_temporada(texto, partidos_temporada, temporada, estadistica)

    return respuesta("No entendí la pregunta. Prueba con algo como:\n\n" +
                     "\n".join(f"- {ejemplo}" for ejemplo in EJEMPLOS), tipo="ayuda")


def responder_enfrentamiento(texto, partidos_temporada, temporada, equipos, estadistica):
    """Preguntas sobre los partidos entre dos equipos."""
    equipo_a, equipo_b = equipos
    tabla = enfrentamientos(partidos_temporada, equipo_a, equipo_b)
    if tabla.empty:
        return respuesta(f"No encontré partidos entre {equipo_a} y {equipo_b} en {temporada}.",
                         tipo="sin_datos")

    if "ultimo" in texto:
        fila = tabla.iloc[-1]
        return respuesta(f"El último enfrentamiento de {temporada} entre {equipo_a} y {equipo_b} "
                         f"fue el {fecha_texto(fila['Date'])}: **{marcador(fila)}**.",
                         tabla_resumen(tabla.tail(1)), tipo="partidos")

    lineas = []
    for _, fila in tabla.iterrows():
        if estadistica and estadistica[0] != "Goles":
            detalle = detalle_estadistica(fila, equipos, estadistica)
        elif estadistica:
            detalle = f"{equipo_a} marcó {goles_de(fila, equipo_a)} y {equipo_b} marcó {goles_de(fila, equipo_b)}"
        else:
            quien = ganador(fila)
            detalle = f"ganó {quien}" if quien else "empataron"
        lineas.append(f"- {fecha_texto(fila['Date'])}: **{marcador(fila)}** ({detalle}).")

    texto_respuesta = (f"En {temporada}, {equipo_a} y {equipo_b} se enfrentaron "
                       f"{len(tabla)} {'vez' if len(tabla) == 1 else 'veces'}:\n\n" + "\n".join(lineas))
    return respuesta(texto_respuesta, tabla_resumen(tabla), tipo="partidos")


def detalle_estadistica(fila, equipos, estadistica):
    """Texto con una estadística de los dos equipos en un partido."""
    nombre = estadistica[0]
    partes = []
    for equipo in equipos:
        if nombre == "Tarjetas":
            amarillas = valor_de(fila, equipo, "Tarjetas amarillas")
            rojas = valor_de(fila, equipo, "Tarjetas rojas")
            partes.append(f"{equipo}: {amarillas} amarillas y {rojas} rojas")
        else:
            valor = valor_de(fila, equipo, nombre)
            partes.append(f"{equipo}: {'sin dato' if valor is None else valor} {nombre.lower()}")
    return "; ".join(partes)


def resumen_equipo(partidos_equipo, equipo):
    """Victorias, empates, derrotas, goles y estadísticas totales de un equipo."""
    resumen = {"V": 0, "E": 0, "D": 0, "GF": 0, "GC": 0, "Tiros": 0, "Tiros al arco": 0,
               "Córners": 0, "Faltas": 0, "Tarjetas amarillas": 0, "Tarjetas rojas": 0}
    for _, fila in partidos_equipo.iterrows():
        goles_favor = goles_de(fila, equipo)
        goles_contra = int(fila["FTHG"] + fila["FTAG"]) - goles_favor
        resumen["GF"] += goles_favor
        resumen["GC"] += goles_contra
        if goles_favor > goles_contra:
            resumen["V"] += 1
        elif goles_favor == goles_contra:
            resumen["E"] += 1
        else:
            resumen["D"] += 1
        for nombre in ["Tiros", "Tiros al arco", "Córners", "Faltas", "Tarjetas amarillas", "Tarjetas rojas"]:
            valor = valor_de(fila, equipo, nombre)
            if valor is not None:
                resumen[nombre] += valor
    resumen["Puntos"] = resumen["V"] * 3 + resumen["E"]
    return resumen


def responder_equipo(texto, partidos_temporada, temporada, equipo, estadistica):
    """Preguntas sobre un solo equipo."""
    tabla = partidos_de_equipo(partidos_temporada, equipo)
    r = resumen_equipo(tabla, equipo)

    if "ultimo" in texto:
        fila = tabla.iloc[-1]
        return respuesta(f"El último partido de {equipo} en {temporada} fue el {fecha_texto(fila['Date'])}: "
                         f"**{marcador(fila)}**.", tabla_resumen(tabla.tail(1)), tipo="partidos")

    if hay_superlativo(texto) and "partido" in texto:
        nombre, mejores, maximo = partidos_con_mas(tabla, estadistica)
        return respuesta(f"El partido de {equipo} con más {nombre.lower()} en {temporada} fue "
                         f"{describir_partidos(mejores)}, con {maximo} {nombre.lower()} entre los dos equipos.",
                         tabla_resumen(mejores), tipo="partidos")

    if any(palabra in texto for palabra in ["gano", "victoria", "empat", "perdi", "derrota", "puntos"]):
        return respuesta(f"En {temporada}, {equipo} ganó **{r['V']}** partidos, empató **{r['E']}** "
                         f"y perdió **{r['D']}**, para un total de **{r['Puntos']} puntos** "
                         "ganados en el campo.", tipo="equipo")

    if estadistica:
        nombre = estadistica[0]
        if nombre == "Goles":
            return respuesta(f"En {temporada}, {equipo} marcó **{r['GF']} goles** y recibió "
                             f"**{r['GC']}** en sus {len(tabla)} partidos.", tipo="equipo")
        if nombre == "Tarjetas":
            return respuesta(f"En {temporada}, {equipo} recibió **{r['Tarjetas amarillas']} tarjetas "
                             f"amarillas** y **{r['Tarjetas rojas']} rojas**.", tipo="equipo")
        nota = ""
        if nombre in ["Tiros", "Tiros al arco"] and tabla[["HS", "AS"]].isna().any().any():
            nota = " (a uno de sus partidos le falta el dato de tiros)"
        return respuesta(f"En {temporada}, {equipo} sumó **{r[nombre]} {nombre.lower()}** en "
                         f"{len(tabla)} partidos{nota}.", tipo="equipo")

    return respuesta(f"Resumen de {equipo} en {temporada}: {r['V']} victorias, {r['E']} empates y "
                     f"{r['D']} derrotas ({r['Puntos']} puntos), con {r['GF']} goles a favor y "
                     f"{r['GC']} en contra. Estos fueron sus partidos:", tabla_resumen(tabla), tipo="equipo")


def responder_temporada(texto, partidos_temporada, temporada, estadistica):
    """Preguntas sobre toda la temporada (el máximo de algo)."""
    if "goleada" in texto or "diferencia" in texto:
        diferencia = (partidos_temporada["FTHG"] - partidos_temporada["FTAG"]).abs()
        tabla = partidos_temporada[diferencia == diferencia.max()]
        return respuesta(f"La mayor goleada de {temporada} fue de {int(diferencia.max())} goles: "
                         f"{describir_partidos(tabla)}.", tabla_resumen(tabla), tipo="partidos")

    if "campeon" in texto:
        totales = totales_por_equipo(partidos_temporada)
        orden = sorted(totales.items(), key=lambda par: (par[1]["Puntos"], par[1]["GF"] - par[1]["GC"],
                                                        par[1]["GF"]), reverse=True)
        equipo, datos = orden[0]
        return respuesta(f"El campeón de {temporada} fue **{equipo}**, con {datos['Puntos']} puntos.",
                         tipo="temporada")

    nombre = (estadistica or ("Goles",))[0]
    pregunta_por_equipo = "equipo" in texto or "quien" in texto or "recibio" in texto

    if pregunta_por_equipo:
        totales = totales_por_equipo(partidos_temporada)
        clave = {"Goles": "GF", "Tarjetas": "Tarjetas"}.get(nombre, nombre)
        maximo = max(datos[clave] for datos in totales.values())
        lideres = [equipo for equipo, datos in totales.items() if datos[clave] == maximo]
        verbo = "fue" if len(lideres) == 1 else "fueron"
        return respuesta(f"El equipo con más {nombre.lower()} en {temporada} {verbo} "
                         f"**{' y '.join(lideres)}**, con {maximo}.", tipo="temporada")

    nombre, tabla, maximo = partidos_con_mas(partidos_temporada, estadistica)
    return respuesta(f"El partido con más {nombre.lower()} de {temporada} fue {describir_partidos(tabla)}, "
                     f"con {maximo} {nombre.lower()} entre los dos equipos.", tabla_resumen(tabla), tipo="partidos")


def totales_por_equipo(partidos_temporada):
    """Resumen de todos los equipos de la temporada."""
    totales = {}
    for equipo in sorted(set(partidos_temporada["HomeTeam"])):
        r = resumen_equipo(partidos_de_equipo(partidos_temporada, equipo), equipo)
        r["Tarjetas"] = r["Tarjetas amarillas"] + r["Tarjetas rojas"]
        totales[equipo] = r
    return totales
