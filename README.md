# Premier League Data Analytics · Más allá de la tabla

**Exploración interactiva del rendimiento de los equipos de la Premier League (2020/21 a 2024/25)**

Proyecto integrador de primer semestre de Ingeniería de Datos e Inteligencia Artificial
(Lógica Computacional e Introducción a la Ingeniería de Datos e IA).

**Aplicación publicada:** _pendiente de despliegue_

> Proyecto académico universitario e independiente. No es un producto oficial de la Premier
> League ni está afiliado a ella. No usa el logo ni los escudos oficiales: las insignias son
> círculos con la abreviatura de cada equipo, creados para este proyecto.

## Pregunta guía

¿Cómo se relacionan los tiros, tiros al arco, córners, faltas y tarjetas con los goles y los
puntos obtenidos por los equipos de la Premier League, y qué diferencias existen entre su
rendimiento como local y visitante?

## Qué hace la aplicación

Una aplicación en Streamlit para explorar 1.900 partidos de cinco temporadas. En la barra
lateral se elige una de las **13 secciones** y la **temporada**, que se aplica a todas. Las
secciones que comparan temporadas (Récords históricos y, si se elige, Relaciones y
correlaciones) usan las cinco sin cambiar la temporada elegida.

| Sección | Qué muestra |
|---|---|
| **Inicio** | Campeón, partidos ganados por el local, ventaja de local, máximo goleador, hallazgos principales, datos, método y limitaciones. |
| **Clasificación** | Tabla calculada (total, local o visitante) con insignias, puntos por equipo, puntos acumulados por número de partido y aviso de las sanciones de 2023/24. |
| **Análisis** | Indicadores; una estadística frente a los puntos; correlaciones de local y de visitante; tiros al arco frente a goles; ranking de la estadística elegida (tiros, córners, faltas, tarjetas...); local contra visitante por equipo y por temporada. |
| **Comparador de equipos** | Dos equipos frente a frente en 13 estadísticas (goles, recibidos, victorias, empates, derrotas, puntos, goles por partido, tiros, tiros al arco, córners, faltas, amarillas y rojas), en total, de local o de visitante. Tarjetas, gráfico de reparto, tabla, en qué tiene más cada equipo y puntos por partido de local y de visitante. Avisa si se elige el mismo equipo dos veces. |
| **Local vs. visitante** | Un equipo dentro y fuera de casa: puntos y porcentaje de los puntos posibles, goles, recibidos, resultados, tiros, córners, faltas y tarjetas. Gráfico por estadística y una conclusión calculada con los datos (incluida la comparación con la media de la liga). |
| **Relaciones y correlaciones** | Las siete relaciones del proyecto con su r de Pearson, dispersión con recta de tendencia y explicación sencilla, y matriz de correlación con mapa de calor. Se eligen las variables, las temporadas (cinco o una) y los partidos (total, local o visitante). |
| **Ranking personalizado** | Ordena los 20 equipos por una de 12 estadísticas, en orden ascendente o descendente (por defecto, primero el mejor: en goles recibidos, el que menos recibió). Líder, gráfico y tabla. |
| **Récords históricos** | Récords de una sola temporada (entre los 100 equipo-temporada), acumulados de las cinco temporadas y de partidos (más goles, mayor diferencia, resultado más repetido, más goles de un equipo). Filtros por temporada y equipo, y el mejor de cada temporada. |
| **Goleadores y Asistencias** | Máximos goleadores y asistentes de la temporada, con sus fuentes. 2020/21 está marcada como incompleta. |
| **Partidos** | Busca los partidos de un equipo o un enfrentamiento entre dos y muestra la ficha completa de un partido. |
| **Detector de sorpresas** | Partidos en los que las estadísticas contrastan con el resultado: perdió con más tiros o más tiros al arco, ganó con menos tiros, no ganó con más córners, o empató con más tiros, tiros al arco y córners. Explica exactamente qué estadísticas fueron mayores, sin decir que un equipo «fue mejor». |
| **Asistente IA** | Responde preguntas escritas como «¿Cuánto quedó el Man City contra Liverpool?» usando los datos del proyecto (ver abajo). |
| **Curiosidades** | Quince datos llamativos de la temporada calculados con los partidos y el botón **SORPRÉNDEME**, que muestra uno al azar sin repetir hasta verlos todos. |

En Clasificación y Análisis aparecen además los filtros de equipos (hasta 6), partidos
(total, local o visitante), estadística de juego y alcance de la correlación.

### Cómo funciona el asistente

El asistente **no usa un modelo de lenguaje ni internet**: es un programa basado en reglas
(`src/asistente.py`).

1. Normaliza la pregunta (minúsculas, sin tildes).
2. Busca los equipos por su nombre o apodo («Spurs», «Forest», «Man City»...) y tolera pequeños
   errores de escritura («Liverpol»). Si solo dice «Manchester», pregunta cuál de los dos.
3. Detecta qué se pregunta por palabras clave (resultado, victorias, goles, tiros, tiros al
   arco, córners, faltas, tarjetas, último partido, mayor goleada, campeón...).
4. Busca la respuesta en los partidos de la temporada elegida.

Conectarlo a un modelo de lenguaje externo queda como mejora futura.

## Estructura del proyecto

```
premier-league-dashboard/
├── app.py                  aplicación de Streamlit
├── requirements.txt        dependencias
├── data/
│   ├── README.md           fuente, variables y decisiones de limpieza
│   ├── raw/                CSV originales (uno por temporada)
│   └── processed/          tablas generadas por src/preparar_datos.py
├── notebooks/              análisis en Google Colab, en este orden:
│   ├── 01_carga_y_limpieza.ipynb
│   ├── 02_estadisticas_por_equipo.ipynb
│   └── 03_analisis_exploratorio.ipynb
├── src/                    funciones del procesamiento (las mismas de los notebooks)
│   ├── limpieza.py         carga, validación y limpieza
│   ├── estadisticas.py     estadísticas por equipo y clasificación
│   ├── analisis.py         estadísticas descriptivas y correlaciones
│   ├── preparar_datos.py   genera data/processed/ a partir de data/raw/
│   ├── tablero.py          prepara los datos de cada parte del dashboard
│   ├── graficos.py         gráficos del dashboard (Altair)
│   ├── estilos.py          colores, encabezado y tarjetas
│   ├── equipos.py          nombres, abreviaturas, apodos e insignias de los 27 equipos
│   ├── jugadores.py        goleadores y asistentes
│   ├── partidos.py         búsqueda y ficha de partidos
│   ├── asistente.py        asistente basado en reglas
│   ├── curiosidades.py     curiosidades de cada temporada
│   ├── secciones.py        las seis secciones de análisis de la versión 3
│   ├── comparador.py       comparador de equipos y local contra visitante
│   ├── correlaciones.py    matriz de correlación y explicaciones
│   ├── records.py          récords de las cinco temporadas
│   ├── ranking.py          ranking personalizado
│   └── sorpresas.py        detector de sorpresas
├── data/jugadores/         goleadores, asistencias y sus fuentes
└── tests/                  pruebas automáticas
```

## Librerías

| Librería | Para qué se usa |
|---|---|
| **pandas** | Leer los CSV, filtrar, agrupar y ordenar las tablas. |
| **NumPy** | Correlación de Pearson (`np.corrcoef`), recta de tendencia (`np.polyfit`) y estadísticas descriptivas. |
| **Streamlit** | La aplicación web: menú, filtros, tarjetas, tablas y chat. |
| **Altair** | Los gráficos interactivos (se instala junto con Streamlit). |
| **pytest** | Las pruebas automáticas (solo para desarrollo). |

Las versiones están en `requirements.txt`. La versión 3 no agregó librerías nuevas.

## Instalación rápida en Windows (un clic)

Haz doble clic en **`instalar.bat`**. El instalador:

1. busca Python 3.12 (si no lo encuentra, lo instala solo para tu usuario con `winget`);
2. crea el entorno virtual `.venv` e instala las librerías;
3. ejecuta las pruebas;
4. abre la carpeta en Visual Studio Code y la aplicación en el navegador.

Todo queda anotado en `instalacion_log.txt`. Después:

- para abrir la app, doble clic en **`ejecutar_app.bat`**;
- para correr las pruebas, doble clic en **`ejecutar_pruebas.bat`** (el resultado queda en
  `pruebas_log.txt`).

En VS Code, la carpeta `.vscode/` ya trae:

- el intérprete de Python del proyecto (`.venv`) seleccionado;
- las pruebas configuradas en la pestaña **Testing** (el matraz de la barra lateral);
- las tareas *Instalar todo*, *Ejecutar la app*, *Ejecutar las pruebas* y *Regenerar los datos
  procesados* (menú **Terminal → Run Task…**);
- la opción **Run and Debug → «Ejecutar la app (Streamlit)»**, que también se lanza con `F5`;
- las extensiones recomendadas de Python y Jupyter (VS Code ofrece instalarlas al abrir la carpeta).

## Cómo ejecutarla en tu computador (paso a paso)

Usa **Python 3.12**, la misma versión con la que se publica la app. Versiones muy nuevas (por
ejemplo 3.15) pueden no tener todavía disponibles todas las librerías del proyecto. Si tienes
varias versiones instaladas en Windows, crea el entorno con `py -3.12 -m venv .venv`.

**1. Descarga el proyecto** y abre una terminal en la carpeta `premier-league-dashboard`.

**2. Crea y activa un entorno virtual** (instala las librerías solo para este proyecto):

En Windows (PowerShell):
```
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
```

En macOS o Linux:
```
python3 -m venv .venv
source .venv/bin/activate
```

**3. Instala las dependencias:**
```
pip install -r requirements.txt
```

**4. Inicia la aplicación:**
```
streamlit run app.py
```
Se abrirá en el navegador, en `http://localhost:8501`. Para detenerla, pulsa `Ctrl + C` en la terminal.

## Regenerar los datos procesados

Los archivos de `data/processed/` ya vienen incluidos. Para generarlos de nuevo desde los CSV
originales:
```
python -m src.preparar_datos
```
Si faltan, la aplicación los genera automáticamente al iniciarse.

## Pruebas

```
pip install pytest
python -m pytest tests
```

Las pruebas comprueban, entre otras cosas, que:

- los puntos de cada partido suman 3 con ganador y 2 con empate;
- los goles de un equipo coinciden con los recibidos por su rival;
- local + visitante = total en todas las estadísticas;
- la clasificación aplica los criterios en orden (puntos, diferencia de goles, goles a favor);
- la clasificación calculada coincide con las tablas oficiales de 2023/24 y 2024/25;
- cada filtro del dashboard cambia los datos que se muestran;
- el asistente reconoce los equipos (sin confundir, por ejemplo, Leicester City con Man City)
  y responde con los resultados reales;
- las curiosidades y el botón SORPRÉNDEME no repiten hasta mostrarlas todas;
- los líderes de goles y asistencias coinciden con los premios oficiales y cada jugador es de
  un equipo que jugó esa temporada;
- el comparador y la sección local contra visitante coinciden con los partidos, y local +
  visitante = total para los 100 equipo-temporada;
- la matriz de correlación coincide con la de pandas y las explicaciones no afirman causas;
- los récords coinciden con los datos (por ejemplo, Man City 93 puntos en 2021/22 y los 9-0 del
  Man United y del Liverpool);
- cada ranking tiene los 20 equipos en el orden pedido;
- cada partido del detector de sorpresas cumple su criterio y el partido sin dato de tiros
  queda fuera;
- las trece secciones abren sin errores en las cinco temporadas y responden a los filtros, al
  chat y a los botones (`tests/test_app.py`, con la herramienta oficial AppTest de Streamlit).

## Notebooks

Se abren en Google Colab (Archivo → Subir notebook) y se ejecutan en orden. Cada uno indica
qué archivos subir al panel de archivos de Colab y qué archivos genera. El notebook 3 incluye
la matriz de correlación entre todas las estadísticas (5.1) y un análisis de cuántas veces gana
el equipo que más tira (5.2).

## Datos

English Premier League, DataHub, a partir de Football-Data.co.uk. Licencia de dominio público
(ODC-PDDL-1.0). https://datahub.io/football/english-premier-league

Goleadores y asistencias: ESPN, la web oficial de la Premier League y Wikipedia (fuente de
cada temporada en la app y en `data/jugadores/fuentes.json`).

Detalles, diccionario de variables y decisiones de limpieza en [`data/README.md`](data/README.md).

## Limitaciones

- Correlación no es causalidad: la calidad de cada equipo influye a la vez en sus estadísticas
  y en sus puntos.
- Los mismos equipos aparecen en varias temporadas, así que las observaciones no son
  independientes. Los resultados son descriptivos.
- No hay datos de posesión ni de calidad de las ocasiones, y los autogoles no se identifican.
- Los puntos son los ganados en el campo: no incluyen las sanciones de 2023/24.
- Los goleadores y asistentes de 2020/21 están incompletos (10 goleadores y 3 asistentes).
- El asistente solo entiende las preguntas que siguen sus reglas.

## Uso de herramientas de inteligencia artificial

_Completar si la universidad pide declararlo._ Ejemplo: «En el desarrollo se usó Claude
(Anthropic) como apoyo para programar, revisar el código y redactar la documentación. El equipo
revisó, probó y entiende todo el código entregado.»

## Equipo

_Nombres de los integrantes._
