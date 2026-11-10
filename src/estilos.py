"""Estilo visual de la app: colores, encabezado y tarjetas.

El diseño se inspira en los colores de la Premier League, pero no usa su logo ni
los escudos oficiales: es un proyecto académico independiente.
"""

from html import escape

import streamlit as st

from src.equipos import insignia, nombre_completo

MORADO_OSCURO = "#37003c"
MORADO = "#7c3aed"
LAVANDA = "#f3edfb"

CSS = f"""
<style>
.encabezado {{
    background: linear-gradient(120deg, {MORADO_OSCURO} 0%, #5b1a8a 60%, {MORADO} 100%);
    color: #ffffff;
    padding: 1.4rem 1.6rem;
    border-radius: 14px;
    margin-bottom: 1rem;
}}
.encabezado .marca {{
    font-size: 0.8rem;
    letter-spacing: 0.18em;
    font-weight: 700;
    opacity: 0.85;
}}
.encabezado h1 {{
    color: #ffffff;
    font-size: 1.9rem;
    margin: 0.2rem 0 0.3rem 0;
    padding: 0;
}}
.encabezado p {{
    margin: 0;
    opacity: 0.92;
}}
.nota-no-oficial {{
    font-size: 0.78rem;
    color: #5f5670;
    margin: -0.4rem 0 1rem 0.2rem;
}}
.tarjeta {{
    background: {LAVANDA};
    border-left: 5px solid {MORADO};
    border-radius: 10px;
    padding: 0.9rem 1rem;
    margin-bottom: 0.8rem;
    height: 100%;
}}
.tarjeta .titulo {{
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: {MORADO_OSCURO};
}}
.tarjeta .valor {{
    font-size: 1.35rem;
    font-weight: 700;
    color: #1f1235;
    margin: 0.2rem 0;
}}
.tarjeta .detalle {{
    font-size: 0.9rem;
    color: #3d3450;
}}
.tarjeta.destacada {{
    background: {MORADO_OSCURO};
    border-left-color: #00d27a;
}}
.tarjeta.destacada .titulo, .tarjeta.destacada .valor, .tarjeta.destacada .detalle {{
    color: #ffffff;
}}
.partido {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.6rem;
    background: linear-gradient(120deg, {MORADO_OSCURO} 0%, #5b1a8a 60%, {MORADO} 100%);
    color: #ffffff;
    border-radius: 14px;
    padding: 1.2rem 1rem;
    margin-bottom: 1rem;
}}
.partido .equipo {{
    flex: 1;
    text-align: center;
}}
.partido .equipo img {{
    width: 76px;
    height: 76px;
}}
.partido .equipo .nombre {{
    font-weight: 700;
    font-size: 1.15rem;
    margin-top: 0.3rem;
}}
.partido .equipo .rol {{
    font-size: 0.75rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    opacity: 0.85;
}}
.partido .centro {{
    text-align: center;
    min-width: 7rem;
}}
.partido .centro .vs {{
    font-size: 1.9rem;
    font-weight: 800;
}}
.partido .centro .fecha {{
    font-size: 0.9rem;
}}
.partido .centro .estado {{
    display: inline-block;
    margin-top: 0.35rem;
    padding: 0.15rem 0.6rem;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.18);
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}}
@media (max-width: 640px) {{
    .partido .equipo img {{ width: 52px; height: 52px; }}
    .partido .equipo .nombre {{ font-size: 0.95rem; }}
    .partido .centro {{ min-width: 5rem; }}
    .partido .centro .vs {{ font-size: 1.4rem; }}
}}
section[data-testid="stSidebar"] .marca-lateral {{
    font-weight: 800;
    color: {MORADO_OSCURO};
    letter-spacing: 0.08em;
    font-size: 0.95rem;
}}
</style>
"""

NOTA_NO_OFICIAL = ("Proyecto académico universitario e independiente. No es un producto oficial "
                   "de la Premier League ni está afiliado a ella; las insignias son abreviaturas "
                   "creadas para este proyecto, no los escudos de los clubes.")


def encabezado(titulo, subtitulo):
    """HTML del encabezado morado de cada sección."""
    return (f'<div class="encabezado"><div class="marca">PREMIER LEAGUE DATA ANALYTICS</div>'
            f'<h1>{escape(titulo)}</h1><p>{escape(subtitulo)}</p></div>'
            f'<div class="nota-no-oficial">{escape(NOTA_NO_OFICIAL)}</div>')


def tarjeta(titulo, valor, detalle="", destacada=False):
    """HTML de una tarjeta con título, valor grande y detalle. Todo el texto se escapa."""
    clase = "tarjeta destacada" if destacada else "tarjeta"
    return (f'<div class="{clase}"><div class="titulo">{escape(str(titulo))}</div>'
            f'<div class="valor">{escape(str(valor))}</div>'
            f'<div class="detalle">{escape(str(detalle))}</div></div>')


def tarjeta_partido(local, visitante, fecha, estado):
    """HTML de la tarjeta de un partido: insignias, nombres, VS, fecha y estado."""
    def bloque(equipo, rol):
        return (f'<div class="equipo"><img src="{insignia(equipo)}" alt="Insignia de {escape(equipo)}">'
                f'<div class="nombre">{escape(nombre_completo(equipo))}</div>'
                f'<div class="rol">{rol}</div></div>')
    return (f'<div class="partido">{bloque(local, "Local")}'
            f'<div class="centro"><div class="vs">VS</div><div class="fecha">{escape(fecha)}</div>'
            f'<div class="estado">{escape(estado)}</div></div>{bloque(visitante, "Visitante")}</div>')


def con_insignia(tabla, columna_equipo="Equipo"):
    """Agrega al inicio una columna con la insignia (abreviatura) de cada equipo."""
    tabla = tabla.copy()
    tabla.insert(0, "Insignia", [insignia(equipo) for equipo in tabla[columna_equipo]])
    return tabla


# Configuración de st.dataframe para que la columna "Insignia" se vea como imagen.
CONFIG_INSIGNIA = {"Insignia": st.column_config.ImageColumn(" ", width="small")}
