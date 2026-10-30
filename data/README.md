# Datos del proyecto

## Fuente

English Premier League, publicado en DataHub a partir de Football-Data.co.uk.
Licencia: Open Data Commons Public Domain Dedication and License (ODC-PDDL-1.0).

- Página del dataset: https://datahub.io/football/english-premier-league
- Fuente original: https://www.football-data.co.uk/

## Archivos originales (`raw/`)

Descargados sin modificar, uno por temporada (380 partidos cada uno):

| Temporada | Archivo | Enlace de descarga |
|---|---|---|
| 2020/21 | `season-2021.csv` | https://datahub.io/football/english-premier-league/_r/-/season-2021.csv |
| 2021/22 | `season-2122.csv` | https://datahub.io/football/english-premier-league/_r/-/season-2122.csv |
| 2022/23 | `season-2223.csv` | https://datahub.io/football/english-premier-league/_r/-/season-2223.csv |
| 2023/24 | `season-2324.csv` | https://datahub.io/football/english-premier-league/_r/-/season-2324.csv |
| 2024/25 | `season-2425.csv` | https://datahub.io/football/english-premier-league/_r/-/season-2425.csv |

## Diccionario de variables originales

| Columna | Significado |
|---|---|
| `Date` | Fecha del partido (AAAA-MM-DD) |
| `HomeTeam`, `AwayTeam` | Equipo local y equipo visitante |
| `FTHG`, `FTAG` | Goles al final del partido: local y visitante |
| `FTR` | Resultado final: `H` gana el local, `D` empate, `A` gana el visitante |
| `HTHG`, `HTAG`, `HTR` | Goles y resultado al medio tiempo |
| `Referee` | Árbitro (excluida en la limpieza) |
| `HS`, `AS` | Tiros: local y visitante |
| `HST`, `AST` | Tiros al arco: local y visitante |
| `HF`, `AF` | Faltas cometidas: local y visitante |
| `HC`, `AC` | Córners: local y visitante |
| `HY`, `AY` | Tarjetas amarillas: local y visitante |
| `HR`, `AR` | Tarjetas rojas: local y visitante |

## Comprobaciones (cinco temporadas)

- 380 partidos y 20 equipos por temporada; cada equipo juega 19 como local y 19 como visitante.
- Las mismas 22 columnas, con el mismo nombre y orden en todas las temporadas.
- Ningún valor vacío, ninguna fecha fuera de su temporada, ningún partido repetido.
- El resultado `FTR` coincide siempre con los goles.

## Decisiones de limpieza aprobadas por el equipo

1. **Se agrega la columna `Temporada`** antes de unir los archivos.
2. **Se excluye `Referee`.** No se usa en la pregunta guía y sus nombres no son consistentes entre temporadas (por ejemplo, "C Kavanagh" y "K Kavanagh").
3. **Tiros imposibles (opción A).** En Newcastle 2-4 West Ham (15/08/2021), el West Ham tiene 9 tiros al arco y solo 8 tiros. Se vacían solo esos dos valores del West Ham. El marcador no cambia y cuenta para la clasificación. Al calcular sus promedios de tiros, se divide entre los partidos con dato (37 en total y 18 de visitante).
4. **Más goles que tiros al arco** (10 partidos). No se tratan como error: un autogol cuenta para el rival aunque no haya rematado. Se conservan sin cambios.
5. **Puntos ganados en el campo.** En 2023/24, Everton (−8) y Nottingham Forest (−4) tuvieron sanciones de puntos que no dependen de los partidos. La clasificación calculada usa los puntos ganados en el campo; el dashboard muestra también los oficiales.

## Datos procesados (`processed/`)

Se regeneran con `python -m src.preparar_datos` desde la carpeta raíz del proyecto.

| Archivo | Una fila es… | Filas |
|---|---|---|
| `partidos_limpios.csv` | un partido | 1.900 |
| `equipo_partido.csv` | lo que hizo un equipo en un partido | 3.800 |
| `estadisticas_equipo_temporada.csv` | un equipo en una temporada, para Total, Local o Visitante | 300 |
| `clasificacion.csv` | un equipo en la clasificación total de una temporada | 100 |
| `reporte_limpieza.json` | validaciones por temporada y cambios realizados | — |

## Goleadores y asistencias (`jugadores/`)

Estas tablas no vienen en los CSV de partidos. Se copiaron a mano de las fuentes indicadas
(consulta: 29/10/2026) y se comprobó que los líderes coinciden con los premios oficiales de la
Premier League (Bota de Oro y Playmaker).

| Archivo | Contenido |
|---|---|
| `goleadores.csv` | Temporada, jugador, equipo, partidos jugados, goles y fuente |
| `asistencias.csv` | Temporada, jugador, equipo, partidos jugados, asistencias y fuente |
| `fuentes.json` | Fuente, enlace y notas de cada temporada; indica si la temporada está completa |

| Temporada | Goles | Asistencias | Notas |
|---|---|---|---|
| 2020/21 | Wikipedia (cita a premierleague.com), 10 primeros | Premier League (oficial), 3 primeros | **Incompleta**, sin partidos jugados. ESPN no tiene esta temporada. |
| 2021/22 | ESPN | ESPN | Primeros puestos con empates completos. |
| 2022/23 | ESPN | ESPN | Primeros puestos con empates completos. |
| 2023/24 | ESPN | Premier League (oficial); partidos de ESPN | ESPN cuenta algunas asistencias distinto (le da 14 a Watkins frente a las 13 oficiales); se usan las oficiales. |
| 2024/25 | ESPN | ESPN | Primeros puestos con empates completos. |

Los nombres de los equipos aparecen completos (por ejemplo, «Tottenham Hotspur»); `src/equipos.py`
los relaciona con los nombres cortos de los CSV de partidos («Tottenham»).
