# Premier League Data Analytics · Más allá de la tabla

Aplicación web para explorar el rendimiento de los equipos de la Premier League entre las
temporadas 2020/21 y 2024/25, a partir de 1.900 partidos.

Proyecto integrador de primer semestre de Ingeniería de Datos e Inteligencia Artificial
(Lógica Computacional e Introducción a la Ingeniería de Datos e IA).

**Aplicación publicada:** https://masalladelatabla.streamlit.app/

> Proyecto académico universitario e independiente. No es un producto oficial de la Premier
> League ni está afiliado a ella. No usa el logo ni los escudos oficiales: las insignias son
> círculos con la abreviatura de cada equipo, creados para este proyecto.

## Objetivo

Analizar con datos reales qué estadísticas de juego se relacionan con los goles y los puntos
de los equipos, y comparar su rendimiento como local y como visitante, usando Python para
limpiar los datos, calcular estadísticas y presentarlas en una aplicación interactiva.

## Pregunta guía

¿Cómo se relacionan los tiros, tiros al arco, córners, faltas y tarjetas con los goles y los
puntos obtenidos por los equipos de la Premier League, y qué diferencias existen entre su
rendimiento como local y visitante?

## Datos

- **Partidos:** conjunto de datos *English Premier League* publicado en DataHub a partir de
  Football-Data.co.uk, con licencia de dominio público (ODC-PDDL-1.0). Son cinco archivos CSV,
  uno por temporada, con 380 partidos cada uno: fecha, equipos, goles, tiros, tiros al arco,
  córners, faltas y tarjetas de cada equipo.
- **Goleadores y asistencias:** tablas copiadas de ESPN, la web oficial de la Premier League y
  Wikipedia, con la fuente de cada temporada en `data/jugadores/fuentes.json`. La temporada
  2020/21 está incompleta (10 goleadores y 3 asistentes).

Las decisiones de limpieza (por ejemplo, el dato imposible de tiros del West Ham en agosto
de 2021 y las sanciones de puntos de 2023/24) y el diccionario de variables están en
[`data/README.md`](data/README.md).

## Qué hace la aplicación

En la barra lateral se elige una de las 13 secciones y la temporada, que se aplica a todas.

| Sección | Qué muestra |
|---|---|
| **Inicio** | Campeón, ventaja de local, máximo goleador, hallazgos principales, método y limitaciones. |
| **Clasificación** | Tabla calculada (total, local o visitante), puntos por equipo y puntos acumulados partido a partido. |
| **Análisis** | Cada estadística frente a los puntos, correlaciones de local y visitante, tiros al arco frente a goles y rankings. |
| **Comparador de equipos** | Dos equipos frente a frente en 13 estadísticas, en total, de local o de visitante. |
| **Local vs. visitante** | Un equipo dentro y fuera de casa, con una conclusión calculada a partir de los datos. |
| **Relaciones y correlaciones** | Correlación de Pearson, gráficos de dispersión y matriz de correlación con mapa de calor. |
| **Ranking personalizado** | Los 20 equipos ordenados por la estadística elegida, en orden ascendente o descendente. |
| **Récords históricos** | Récords de una temporada, acumulados de las cinco temporadas y récords de partidos. |
| **Goleadores y Asistencias** | Máximos goleadores y asistentes de cada temporada, con sus fuentes. |
| **Partidos** | Búsqueda de partidos y ficha completa de cada uno. |
| **Detector de sorpresas** | Partidos en los que tiros o córners contrastan con el resultado. |
| **Asistente IA** | Responde preguntas escritas sobre los partidos con reglas y palabras clave; no usa un modelo de lenguaje ni internet. |
| **Curiosidades** | Datos llamativos de la temporada y el botón SORPRÉNDEME. |

## Tecnologías

| Herramienta | Uso en el proyecto |
|---|---|
| Python 3.12 | Lenguaje del proyecto |
| pandas | Leer los CSV, filtrar, agrupar y ordenar tablas |
| NumPy | Correlación de Pearson, recta de tendencia y estadísticas descriptivas |
| Streamlit | Aplicación web y despliegue en Streamlit Community Cloud |
| Altair | Gráficos interactivos |
| Google Colab | Notebooks del análisis paso a paso |
| pytest | Pruebas automáticas |

Las versiones están en `requirements.txt`.

## Estructura del repositorio

```
premier-league-dashboard/
├── app.py                  aplicación de Streamlit
├── requirements.txt        librerías necesarias
├── .streamlit/config.toml  colores y configuración de la app
├── data/
│   ├── README.md           fuente, variables y decisiones de limpieza
│   ├── raw/                CSV originales (uno por temporada)
│   ├── processed/          tablas generadas por src/preparar_datos.py
│   └── jugadores/          goleadores, asistencias y sus fuentes
├── notebooks/              análisis en Google Colab, en orden:
│   ├── 01_carga_y_limpieza.ipynb
│   ├── 02_estadisticas_por_equipo.ipynb
│   └── 03_analisis_exploratorio.ipynb
├── src/                    funciones del proyecto (las mismas de los notebooks)
│   ├── limpieza.py         carga, validación y limpieza
│   ├── estadisticas.py     estadísticas por equipo y clasificación
│   ├── analisis.py         estadísticas descriptivas y correlaciones
│   ├── preparar_datos.py   genera data/processed/ a partir de data/raw/
│   ├── tablero.py          datos de los gráficos según los filtros
│   ├── graficos.py         gráficos (Altair)
│   ├── estilos.py          colores, encabezado y tarjetas
│   ├── equipos.py          nombres, abreviaturas e insignias de los 27 equipos
│   ├── jugadores.py        goleadores y asistentes
│   ├── partidos.py         búsqueda y ficha de partidos
│   ├── asistente.py        asistente basado en reglas
│   ├── curiosidades.py     curiosidades de cada temporada
│   ├── secciones.py        páginas de comparador, correlaciones, ranking, récords y sorpresas
│   ├── comparador.py       comparador de equipos y local contra visitante
│   ├── correlaciones.py    matriz de correlación y explicaciones
│   ├── records.py          récords de las cinco temporadas
│   ├── ranking.py          ranking personalizado
│   └── sorpresas.py        detector de sorpresas
├── tests/                  pruebas automáticas
├── instalar.bat            instalación en Windows con doble clic
├── ejecutar_app.bat        abre la aplicación en Windows
└── ejecutar_pruebas.bat    ejecuta las pruebas en Windows
```

## Instalación y ejecución

Se recomienda **Python 3.12**, la versión con la que se probó y se publicó la aplicación.

**En Windows, con doble clic:** `instalar.bat` instala Python 3.12 si hace falta, crea el
entorno virtual `.venv`, instala las librerías y ejecuta las pruebas. Después,
`ejecutar_app.bat` abre la aplicación y `ejecutar_pruebas.bat` vuelve a correr las pruebas.

**Paso a paso (cualquier sistema):**

1. Descarga o clona el repositorio y abre una terminal en su carpeta.
2. Crea y activa un entorno virtual:
   - Windows: `py -3.12 -m venv .venv` y luego `.venv\Scripts\Activate.ps1`
   - macOS o Linux: `python3 -m venv .venv` y luego `source .venv/bin/activate`
3. Instala las librerías: `pip install -r requirements.txt`
4. Ejecuta la aplicación:

```
streamlit run app.py
```

Se abre en el navegador en `http://localhost:8501`.

Los archivos de `data/processed/` ya vienen incluidos. Para generarlos otra vez desde los CSV
originales: `python -m src.preparar_datos`. Si faltan, la aplicación los genera al iniciarse.

## Notebooks

Se abren en Google Colab (Archivo → Subir notebook) y se ejecutan en orden. Cada uno indica
qué archivos subir y qué archivos genera:

1. **Carga y limpieza:** valida las cinco temporadas y produce `partidos_limpios.csv`.
2. **Estadísticas por equipo:** convierte cada partido en dos registros (local y visitante) y
   calcula las estadísticas por equipo y temporada y la clasificación.
3. **Análisis exploratorio:** estadísticas descriptivas, correlaciones, comparación entre local
   y visitante, matriz de correlación y gráficos.

## Pruebas

```
pip install pytest
python -m pytest tests
```

Las 106 pruebas comprueban, entre otras cosas, que los puntos y goles cuadran partido a
partido, que local más visitante da el total, que la clasificación coincide con las tablas
oficiales de 2023/24 y 2024/25, que los líderes de goles y asistencias coinciden con los premios
oficiales y que las 13 secciones de la aplicación abren sin errores en las cinco temporadas.

## Resultados principales

- Los tiros al arco son la estadística de juego más relacionada con los puntos (r = 0,86 con
  100 equipo-temporada).
- La relación es parecida de local y de visitante (r = 0,82 y 0,78); lo que cambia es el
  nivel: de local los equipos suman en promedio 0,28 puntos más por partido.
- 2020/21, jugada casi sin público, fue la única temporada en que los visitantes ganaron más
  partidos que los locales.

## Limitaciones

- Correlación no es causalidad: la calidad de cada equipo influye a la vez en sus estadísticas
  y en sus puntos.
- Los mismos equipos aparecen en varias temporadas, así que los resultados son descriptivos.
- No hay datos de posesión ni de calidad de las ocasiones, y los autogoles no se identifican.
- Los puntos son los ganados en el campo: no incluyen las sanciones de 2023/24, que la
  aplicación muestra aparte.

## Uso de herramientas de inteligencia artificial

En el desarrollo se usó Claude (Anthropic) como apoyo para programar, revisar el código y
redactar la documentación. El equipo revisó, probó y entiende el código y los resultados
entregados.

## Equipo

- Sergio Tinjaca
- Santiago Sánchez
- Simón Chacón
- Santiago Fonseca

## Créditos y referencias

- DataHub. (s. f.). *English Premier League* [Conjunto de datos]. https://datahub.io/football/english-premier-league
- Football-Data.co.uk. (s. f.). *England football results* [Conjunto de datos]. https://www.football-data.co.uk/
- ESPN. (s. f.). *English Premier League stats* (temporadas 2021/22 a 2024/25). https://www.espn.co.uk/football/stats/_/league/ENG.1
- Premier League. (s. f.). Premios oficiales de goleador y asistente. https://www.premierleague.com/news/2154211 y https://www.premierleague.com/en/news/4021251
- Wikipedia. (s. f.). *2020–21 Premier League*. https://en.wikipedia.org/wiki/2020%E2%80%9321_Premier_League
- Documentación de [Streamlit](https://docs.streamlit.io/), [pandas](https://pandas.pydata.org/docs/), [NumPy](https://numpy.org/doc/) y [Altair](https://altair-viz.github.io/).
