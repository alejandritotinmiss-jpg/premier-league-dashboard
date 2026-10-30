"""Curiosidades de cada temporada calculadas con los datos reales."""

import random

from src.partidos import fecha_texto, marcador


def lista_bonita(nombres):
    """Une nombres en español: ['A', 'B', 'C'] -> 'A, B y C'."""
    nombres = list(nombres)
    if len(nombres) == 1:
        return nombres[0]
    return ", ".join(nombres[:-1]) + " y " + nombres[-1]


def partido_maximo(partidos_temporada, columna_local, columna_visitante):
    """Partidos con el máximo de una estadística sumando los dos equipos."""
    total = partidos_temporada[columna_local] + partidos_temporada[columna_visitante]
    maximo = total.max()
    return partidos_temporada[total == maximo], int(maximo)


def describir_partidos(tabla):
    """Texto con uno o varios partidos: 'Arsenal 5-0 Wolves (17/08/2024)'."""
    textos = [f"{marcador(fila)} ({fecha_texto(fila['Date'])})" for _, fila in tabla.iterrows()]
    if len(textos) > 3:
        resto = len(textos) - 3
        return f"{', '.join(textos[:3])} y {resto} {'partido' if resto == 1 else 'partidos'} más"
    return lista_bonita(textos)


def equipos_maximo(totales, columna):
    """Equipos con el valor más alto de una columna y ese valor."""
    maximo = totales[columna].max()
    return list(totales.index[totales[columna] == maximo]), int(maximo)


def curiosidades_temporada(partidos_temporada, equipo_partido_temporada):
    """Lista de curiosidades de una temporada: cada una con título y texto."""
    curiosidades = []

    def agregar(titulo, texto):
        curiosidades.append({"titulo": titulo, "texto": texto})

    tabla, goles = partido_maximo(partidos_temporada, "FTHG", "FTAG")
    agregar("Partido con más goles",
            f"El partido con más goles fue {describir_partidos(tabla)}, con {goles} goles en total.")

    diferencia = (partidos_temporada["FTHG"] - partidos_temporada["FTAG"]).abs()
    goleadas = partidos_temporada[diferencia == diferencia.max()]
    agregar("Mayor goleada",
            f"La mayor goleada fue {describir_partidos(goleadas)}: "
            f"{int(diferencia.max())} goles de diferencia.")

    marcadores = [f"{max(a, b)}-{min(a, b)}" for a, b in
                  zip(partidos_temporada["FTHG"], partidos_temporada["FTAG"])]
    conteo = {}
    for resultado in marcadores:
        conteo[resultado] = conteo.get(resultado, 0) + 1
    mas_repetido = max(conteo, key=conteo.get)
    agregar("Resultado más repetido",
            f"El resultado más repetido fue {mas_repetido} (sin importar quién ganó): "
            f"se dio en {conteo[mas_repetido]} de los {len(partidos_temporada)} partidos.")

    for titulo, local, visitante, unidad in [
        ("Partido con más tiros", "HS", "AS", "tiros"),
        ("Partido con más tiros al arco", "HST", "AST", "tiros al arco"),
        ("Partido con más córners", "HC", "AC", "córners"),
    ]:
        # Los partidos sin dato de tiros quedan por fuera (la suma da vacío).
        tabla, maximo = partido_maximo(partidos_temporada.dropna(subset=[local, visitante]),
                                       local, visitante)
        agregar(titulo, f"El partido con más {unidad} fue {describir_partidos(tabla)}, "
                        f"con {maximo} {unidad} entre los dos equipos.")

    registros = equipo_partido_temporada.copy()
    registros["Tarjetas"] = registros["Amarillas"] + registros["Rojas"]
    registros["PorteriaCero"] = (registros["GolesContra"] == 0).astype(int)
    totales = registros.groupby("Equipo")[["Victoria", "Derrota", "Empate", "Amarillas", "Rojas",
                                            "Tarjetas", "Corners", "PorteriaCero"]].sum()

    for titulo, columna, frase in [
        ("Equipo con más victorias", "Victoria", "ganó {} partidos"),
        ("Equipo con más derrotas", "Derrota", "perdió {} partidos"),
        ("Equipo con más empates", "Empate", "empató {} partidos"),
        ("Equipo con más tarjetas amarillas", "Amarillas", "recibió {} tarjetas amarillas"),
        ("Equipo con más tarjetas rojas", "Rojas", "recibió {} tarjetas rojas"),
        ("Equipo con más córners", "Corners", "sacó {} córners"),
        ("Equipo con más porterías a cero", "PorteriaCero", "terminó {} partidos sin recibir goles"),
    ]:
        equipos, valor = equipos_maximo(totales, columna)
        if len(equipos) == 1:
            sujeto = f"El {titulo.lower()} fue {equipos[0]}"
        else:
            sujeto = f"Los equipos con más {titulo.split('más ')[1]} fueron {lista_bonita(equipos)}"
            frase = frase.replace("ganó", "ganaron").replace("perdió", "perdieron") \
                .replace("empató", "empataron").replace("recibió", "recibieron") \
                .replace("sacó", "sacaron").replace("terminó", "terminaron")
        agregar(titulo, f"{sujeto}: {frase.format(valor)}.")

    for titulo, condicion, lugar in [
        ("Más goles como local", "Local", "en casa"),
        ("Más goles como visitante", "Visitante", "fuera de casa"),
    ]:
        goles_condicion = registros[registros["Condicion"] == condicion].groupby("Equipo")[["GolesFavor"]].sum()
        equipos, valor = equipos_maximo(goles_condicion, "GolesFavor")
        verbo = "marcó" if len(equipos) == 1 else "marcaron"
        agregar(titulo, f"{lista_bonita(equipos)} {verbo} {valor} goles {lugar}, "
                        "más que cualquier otro equipo.")

    return curiosidades


def elegir_curiosidad(curiosidades, ya_vistas):
    """Elige al azar una curiosidad que no se haya mostrado; si ya se vieron todas, empieza de nuevo.

    Devuelve la curiosidad y la lista actualizada de títulos vistos.
    """
    disponibles = [c for c in curiosidades if c["titulo"] not in ya_vistas]
    if not disponibles:
        ya_vistas = []
        disponibles = curiosidades
    elegida = random.choice(disponibles)
    return elegida, ya_vistas + [elegida["titulo"]]
