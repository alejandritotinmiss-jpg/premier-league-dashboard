"""Ranking personalizado: el usuario elige una estadística y se ordenan los 20 equipos."""

from src.tablero import filtrar

# Nombre visible -> datos de la opción:
#   columna: columna de estadisticas_equipo_temporada.csv
#   condicion: Total, Local o Visitante
#   menor_es_mejor: True si un valor más bajo es mejor (por ejemplo, goles recibidos)
OPCIONES_RANKING = {
    "Más goles anotados": {"columna": "GolesFavor", "condicion": "Total", "menor_es_mejor": False},
    "Menos goles recibidos": {"columna": "GolesContra", "condicion": "Total", "menor_es_mejor": True},
    "Más victorias": {"columna": "V", "condicion": "Total", "menor_es_mejor": False},
    "Más puntos": {"columna": "Puntos", "condicion": "Total", "menor_es_mejor": False},
    "Más tiros": {"columna": "Tiros", "condicion": "Total", "menor_es_mejor": False},
    "Más tiros al arco": {"columna": "TirosArco", "condicion": "Total", "menor_es_mejor": False},
    "Más córners": {"columna": "Corners", "condicion": "Total", "menor_es_mejor": False},
    "Más tarjetas amarillas": {"columna": "Amarillas", "condicion": "Total", "menor_es_mejor": False},
    "Más tarjetas rojas": {"columna": "Rojas", "condicion": "Total", "menor_es_mejor": False},
    "Mejor rendimiento como local": {"columna": "Puntos", "condicion": "Local", "menor_es_mejor": False},
    "Mejor rendimiento como visitante": {"columna": "Puntos", "condicion": "Visitante", "menor_es_mejor": False},
    "Mayor promedio de goles por partido": {"columna": "GolesFavorPorPartido", "condicion": "Total",
                                            "menor_es_mejor": False},
}

ORDEN_DESCENDENTE = "Descendente (de mayor a menor)"
ORDEN_ASCENDENTE = "Ascendente (de menor a mayor)"


def orden_recomendado(opcion):
    """El orden que deja primero al mejor: ascendente si un valor menor es mejor."""
    if OPCIONES_RANKING[opcion]["menor_es_mejor"]:
        return ORDEN_ASCENDENTE
    return ORDEN_DESCENDENTE


def ranking_personalizado(estadisticas, temporada, opcion, orden):
    """Los 20 equipos ordenados por la estadística elegida.

    La posición sigue el orden elegido (1 = primero de la lista) y los empatados la comparten.
    Para los rankings de local y visitante se muestran además PJ, V, E y D.
    """
    datos = OPCIONES_RANKING[opcion]
    columna = datos["columna"]
    filas = filtrar(estadisticas, temporada, datos["condicion"])
    tabla = filas[["Equipo", "PJ", "V", "E", "D"]].copy()
    tabla["Valor"] = filas[columna]
    ascendente = orden == ORDEN_ASCENDENTE
    tabla = tabla.sort_values(["Valor", "Equipo"], ascending=[ascendente, True]).reset_index(drop=True)
    tabla.insert(0, "Pos", tabla["Valor"].rank(method="min", ascending=ascendente).astype(int))
    if columna.endswith("PorPartido"):
        tabla["Valor"] = tabla["Valor"].round(2)
    else:
        tabla["Valor"] = tabla["Valor"].astype(int)
    return tabla


def lider(estadisticas, temporada, opcion):
    """Equipo(s) con el mejor valor de la categoría, sin importar el orden elegido."""
    tabla = ranking_personalizado(estadisticas, temporada, opcion, orden_recomendado(opcion))
    primeros = tabla[tabla["Pos"] == 1]
    valor = primeros["Valor"].iloc[0]
    return primeros["Equipo"].tolist(), (float(valor) if isinstance(valor, float) else int(valor))
