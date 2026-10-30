"""Datos de los 27 equipos de las cinco temporadas: nombres, abreviaturas e insignias."""

import base64
import unicodedata

# Nombre usado en los CSV -> nombre completo, abreviatura y otras formas de escribirlo.
EQUIPOS = {
    "Arsenal": {"nombre": "Arsenal", "abreviatura": "ARS", "alias": ["arsenal", "gunners"]},
    "Aston Villa": {"nombre": "Aston Villa", "abreviatura": "AVL", "alias": ["aston villa", "villa"]},
    "Bournemouth": {"nombre": "AFC Bournemouth", "abreviatura": "BOU",
                    "alias": ["bournemouth", "afc bournemouth"]},
    "Brentford": {"nombre": "Brentford", "abreviatura": "BRE", "alias": ["brentford"]},
    "Brighton": {"nombre": "Brighton & Hove Albion", "abreviatura": "BHA",
                 "alias": ["brighton", "brighton and hove albion", "brighton & hove albion"]},
    "Burnley": {"nombre": "Burnley", "abreviatura": "BUR", "alias": ["burnley"]},
    "Chelsea": {"nombre": "Chelsea", "abreviatura": "CHE", "alias": ["chelsea"]},
    "Crystal Palace": {"nombre": "Crystal Palace", "abreviatura": "CRY",
                       "alias": ["crystal palace", "palace"]},
    "Everton": {"nombre": "Everton", "abreviatura": "EVE", "alias": ["everton"]},
    "Fulham": {"nombre": "Fulham", "abreviatura": "FUL", "alias": ["fulham"]},
    "Ipswich": {"nombre": "Ipswich Town", "abreviatura": "IPS", "alias": ["ipswich", "ipswich town"]},
    "Leeds": {"nombre": "Leeds United", "abreviatura": "LEE", "alias": ["leeds", "leeds united"]},
    "Leicester": {"nombre": "Leicester City", "abreviatura": "LEI",
                  "alias": ["leicester", "leicester city"]},
    "Liverpool": {"nombre": "Liverpool", "abreviatura": "LIV", "alias": ["liverpool"]},
    "Luton": {"nombre": "Luton Town", "abreviatura": "LUT", "alias": ["luton", "luton town"]},
    "Man City": {"nombre": "Manchester City", "abreviatura": "MCI",
                 "alias": ["manchester city", "man city", "city"]},
    "Man United": {"nombre": "Manchester United", "abreviatura": "MUN",
                   "alias": ["manchester united", "man united", "man utd", "united"]},
    "Newcastle": {"nombre": "Newcastle United", "abreviatura": "NEW",
                  "alias": ["newcastle", "newcastle united"]},
    "Norwich": {"nombre": "Norwich City", "abreviatura": "NOR", "alias": ["norwich", "norwich city"]},
    "Nott'm Forest": {"nombre": "Nottingham Forest", "abreviatura": "NFO",
                      "alias": ["nottingham forest", "nottingham", "nottm forest", "forest"]},
    "Sheffield United": {"nombre": "Sheffield United", "abreviatura": "SHU",
                         "alias": ["sheffield united", "sheffield"]},
    "Southampton": {"nombre": "Southampton", "abreviatura": "SOU", "alias": ["southampton"]},
    "Tottenham": {"nombre": "Tottenham Hotspur", "abreviatura": "TOT",
                  "alias": ["tottenham", "tottenham hotspur", "spurs"]},
    "Watford": {"nombre": "Watford", "abreviatura": "WAT", "alias": ["watford"]},
    "West Brom": {"nombre": "West Bromwich Albion", "abreviatura": "WBA",
                  "alias": ["west brom", "west bromwich", "west bromwich albion"]},
    "West Ham": {"nombre": "West Ham United", "abreviatura": "WHU",
                 "alias": ["west ham", "west ham united"]},
    "Wolves": {"nombre": "Wolverhampton Wanderers", "abreviatura": "WOL",
               "alias": ["wolves", "wolverhampton", "wolverhampton wanderers"]},
}


def normalizar(texto):
    """Pasa el texto a minúsculas y le quita tildes y apóstrofos para poder compararlo."""
    texto = unicodedata.normalize("NFKD", str(texto).lower())
    texto = "".join(letra for letra in texto if not unicodedata.combining(letra))
    return texto.replace("'", "").replace("’", "")


def nombre_completo(equipo):
    """Nombre completo del equipo, por ejemplo 'Man City' -> 'Manchester City'."""
    return EQUIPOS.get(equipo, {}).get("nombre", equipo)


def abreviatura(equipo):
    """Abreviatura de tres letras del equipo."""
    return EQUIPOS.get(equipo, {}).get("abreviatura", str(equipo)[:3].upper())


def equipo_desde_nombre_completo(nombre):
    """Convierte un nombre completo (como lo escribe ESPN) al nombre corto de los CSV."""
    buscado = normalizar(nombre)
    for equipo, datos in EQUIPOS.items():
        if normalizar(datos["nombre"]) == buscado or normalizar(equipo) == buscado:
            return equipo
    return None


def insignia(equipo):
    """Insignia propia del equipo (círculo con su abreviatura) como imagen SVG para tablas.

    No es el escudo oficial: los escudos son marcas registradas de cada club.
    """
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">'
        '<circle cx="32" cy="32" r="30" fill="#38003c" stroke="#963cff" stroke-width="3"/>'
        '<text x="32" y="39" font-family="Arial, sans-serif" font-size="19" font-weight="bold" '
        f'fill="#ffffff" text-anchor="middle">{abreviatura(equipo)}</text></svg>'
    )
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")
