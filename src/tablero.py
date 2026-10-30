"""Prepara los datos de cada parte del dashboard según los filtros elegidos."""

import numpy as np
import pandas as pd

from src.analisis import VARIABLES_JUEGO, correlacion
from src.estadisticas import calcular_clasificacion

# Métricas que se pueden elegir: nombre visible -> columna.
METRICAS = {nombre: columna for columna, nombre in VARIABLES_JUEGO.items()}
METRICAS["Goles a favor (referencia)"] = "GolesFavorPorPartido"

CONDICIONES = ["Total", "Local", "Visitante"]

# Sanciones de puntos de 2023/24 (fuente: tabla final de NBC Sports).
SANCIONES = {
    ("2023/24", "Everton"): 8,
    ("2023/24", "Nott'm Forest"): 4,
}


def temporadas_disponibles(estadisticas):
    """Lista de temporadas ordenada."""
    return sorted(estadisticas["Temporada"].unique())


def equipos_de_temporada(estadisticas, temporada):
    """Los 20 equipos de una temporada en orden alfabético."""
    tabla = estadisticas[estadisticas["Temporada"] == temporada]
    return sorted(tabla["Equipo"].unique())


def filtrar(estadisticas, temporada, condicion):
    """Filas de una temporada y una condición (20 filas)."""
    filtro = (estadisticas["Temporada"] == temporada) & (estadisticas["Condicion"] == condicion)
    return estadisticas[filtro]


def equipos_por_defecto(estadisticas, temporada, cantidad=3):
    """Los primeros equipos de la clasificación total de la temporada."""
    tabla = calcular_clasificacion(filtrar(estadisticas, temporada, "Total"))
    return tabla["Equipo"].head(cantidad).tolist()


def tabla_clasificacion(estadisticas, temporada, condicion):
    """Clasificación de la temporada; si hubo sanciones agrega la columna Pts oficiales."""
    tabla = calcular_clasificacion(filtrar(estadisticas, temporada, condicion))
    tabla = tabla[["Posicion", "Equipo", "PJ", "V", "E", "D", "GolesFavor",
                   "GolesContra", "DG", "Puntos"]]
    tabla = tabla.rename(columns={"Posicion": "Pos", "GolesFavor": "GF",
                                  "GolesContra": "GC", "Puntos": "Pts"})

    sanciones_temporada = {equipo: puntos for (t, equipo), puntos in SANCIONES.items()
                           if t == temporada}
    if condicion == "Total" and sanciones_temporada:
        oficiales = []
        for equipo, puntos in zip(tabla["Equipo"], tabla["Pts"]):
            oficiales.append(puntos - sanciones_temporada.get(equipo, 0))
        tabla["Pts oficiales"] = oficiales
    return tabla.reset_index(drop=True)


def puntos_por_equipo(estadisticas, temporada, condicion, seleccionados):
    """Datos del gráfico de puntos por equipo, marcando los equipos elegidos."""
    tabla = calcular_clasificacion(filtrar(estadisticas, temporada, condicion))
    tabla = tabla[["Posicion", "Equipo", "Puntos"]].copy()
    tabla["Seleccionado"] = tabla["Equipo"].isin(seleccionados)
    return tabla


def evolucion_puntos(equipo_partido, temporada, equipos):
    """Puntos acumulados por número de partido de los equipos elegidos."""
    filtro = (equipo_partido["Temporada"] == temporada) & (equipo_partido["Equipo"].isin(equipos))
    columnas = ["Equipo", "NumeroPartido", "PuntosAcumulados", "Rival", "Condicion",
                "GolesFavor", "GolesContra", "Resultado"]
    tabla = equipo_partido.loc[filtro, columnas].copy()
    tabla["Marcador"] = tabla["GolesFavor"].astype(int).astype(str) + "-" + \
        tabla["GolesContra"].astype(int).astype(str)
    return tabla.sort_values(["Equipo", "NumeroPartido"]).reset_index(drop=True)


def datos_dispersion(estadisticas, temporada, condicion, columna_metrica,
                     todas_las_temporadas, seleccionados):
    """Datos del gráfico de una métrica frente a los puntos por partido."""
    tabla = estadisticas[estadisticas["Condicion"] == condicion]
    if not todas_las_temporadas:
        tabla = tabla[tabla["Temporada"] == temporada]
    tabla = tabla[["Equipo", "Temporada", columna_metrica, "PuntosPorPartido"]].copy()
    tabla = tabla.rename(columns={columna_metrica: "Valor"})
    tabla["Seleccionado"] = (tabla["Temporada"] == temporada) & tabla["Equipo"].isin(seleccionados)
    tabla["Etiqueta"] = tabla["Equipo"] + " " + tabla["Temporada"]
    return tabla.reset_index(drop=True)


def recta_tendencia(x, y):
    """Dos puntos de la recta de mínimos cuadrados (np.polyfit) para dibujar la tendencia."""
    pendiente, intercepto = np.polyfit(np.asarray(x, dtype=float), np.asarray(y, dtype=float), 1)
    extremos = np.array([np.min(x), np.max(x)], dtype=float)
    return pd.DataFrame({"Valor": extremos, "PuntosPorPartido": pendiente * extremos + intercepto})


def comparacion_local_visitante(estadisticas, temporada, equipos, columna_metrica):
    """Una métrica de local y de visitante para cada equipo elegido."""
    filtro = ((estadisticas["Temporada"] == temporada)
              & (estadisticas["Equipo"].isin(equipos))
              & (estadisticas["Condicion"].isin(["Local", "Visitante"])))
    tabla = estadisticas.loc[filtro, ["Equipo", "Condicion", columna_metrica]]
    return tabla.rename(columns={columna_metrica: "Valor"}).reset_index(drop=True)


def ventaja_local_por_temporada(estadisticas):
    """Puntos por partido de local y de visitante en cada temporada (media de los 20 equipos)."""
    tabla = estadisticas[estadisticas["Condicion"].isin(["Local", "Visitante"])]
    resumen = tabla.groupby(["Temporada", "Condicion"])["PuntosPorPartido"].mean()
    return resumen.reset_index()


def resultados_temporada(equipo_partido, temporada):
    """Cuenta victorias locales, empates y victorias visitantes de una temporada."""
    filtro = (equipo_partido["Temporada"] == temporada) & (equipo_partido["Condicion"] == "Local")
    conteo = equipo_partido.loc[filtro, "Resultado"].value_counts()
    return {
        "Gana el local": int(conteo.get("V", 0)),
        "Empate": int(conteo.get("E", 0)),
        "Gana el visitante": int(conteo.get("D", 0)),
    }


def equipos_mejor_de_local(estadisticas):
    """Cuántos equipo-temporada sumaron más puntos de local, el total y la diferencia media."""
    indice = ["Temporada", "Equipo"]
    local = estadisticas[estadisticas["Condicion"] == "Local"].set_index(indice)["PuntosPorPartido"]
    visitante = estadisticas[estadisticas["Condicion"] == "Visitante"].set_index(indice)["PuntosPorPartido"]
    diferencia = local - visitante
    return int((diferencia > 0).sum()), int(len(diferencia)), float(diferencia.mean())


def correlacion_con_puntos(estadisticas, temporada, condicion, columna_metrica,
                           todas_las_temporadas):
    """Correlación de una métrica con los puntos por partido. Devuelve (r, n)."""
    tabla = estadisticas[estadisticas["Condicion"] == condicion]
    if not todas_las_temporadas:
        tabla = tabla[tabla["Temporada"] == temporada]
    return correlacion(tabla[columna_metrica], tabla["PuntosPorPartido"]), len(tabla)


def datos_tiros_arco_goles(estadisticas, temporada, condicion, seleccionados):
    """Tiros al arco y goles a favor por partido de los 20 equipos de una temporada."""
    tabla = filtrar(estadisticas, temporada, condicion)
    tabla = tabla[["Equipo", "TirosArcoPorPartido", "GolesFavorPorPartido"]].copy()
    tabla["Seleccionado"] = tabla["Equipo"].isin(seleccionados)
    return tabla.reset_index(drop=True)


def ranking_metrica(estadisticas, temporada, condicion, columna_metrica, seleccionados):
    """Valor de una métrica por equipo, de mayor a menor, marcando los equipos elegidos."""
    tabla = filtrar(estadisticas, temporada, condicion)
    tabla = tabla[["Equipo", columna_metrica]].rename(columns={columna_metrica: "Valor"})
    tabla = tabla.sort_values("Valor", ascending=False).reset_index(drop=True)
    tabla["Seleccionado"] = tabla["Equipo"].isin(seleccionados)
    return tabla
