# Premier League Data Analytics · Más allá de la tabla

Aplicación web para explorar el rendimiento de los equipos de la Premier League entre las
temporadas 2020/21 y 2026/27 (2.380 partidos), estimar probabilidades de los próximos partidos
con un modelo de regresión logística y consultar todo con un chatbot.

Proyecto integrador de primer semestre de Ingeniería de Datos e Inteligencia Artificial
(Lógica Computacional e Introducción a la Ingeniería de Datos e IA).

**Aplicación publicada:** https://masalladelatabla.streamlit.app/

> Proyecto académico universitario e independiente. No es un producto oficial de la Premier
> League ni está afiliado a ella. No usa el logo ni los escudos oficiales: las insignias son
> círculos con la abreviatura de cada equipo, creados para este proyecto. Las probabilidades
> son estimaciones estadísticas, no certezas ni recomendaciones de apuestas.

## Objetivo

Analizar con datos reales qué estadísticas de juego se relacionan con los goles y los puntos
de los equipos, comparar su rendimiento como local y como visitante, y usar esas mismas
estadísticas para estimar, sin usar información del futuro, la probabilidad de cada resultado
de un partido.

## Pregunta guía

¿Cómo se relacionan los tiros, tiros al arco, córners, faltas y tarjetas con los goles y los
puntos obtenidos por los equipos de la Premier League, y qué diferencias existen entre su
rendimiento como local y visitante?

## Datos y temporadas disponibles

| Temporada | Partidos | Estado | Fuente |
|---|---|---|---|
| 2020/21 a 2024/25 | 380 cada una | Terminadas | DataHub, a partir de Football-Data.co.uk (ODC-PDDL-1.0) |
| 2025/26 | 380 | Terminada (campeón: Arsenal, 85 puntos) | DataHub, a partir de Football-Data.co.uk |
| 2026/27 | 100 (hasta el 08/11/2026) | **En curso**, se actualiza sola | Football-Data.co.uk |

- **Calendario de partidos pendientes:** fixturedownload.com, una fuente distinta de la de los
  resultados.
- **Goleadores y asistencias:** ESPN, la web oficial de la Premier League y Wikipedia. Hay una
  fuente por temporada, en `data/jugadores/fuentes.json`. 2020/21 está incompleta y 2026/27 no
  se actualiza sola.

En [`data/README.md`](data/README.md) están las decisiones de limpieza y el diccionario de
variables. También se explica cómo se obtuvo y verificó cada temporada nueva. Las temporadas no
están escritas en el código: se descubren por el nombre de los archivos de `data/raw/`.

## Qué hace la aplicación

En la barra lateral se elige una de las 14 secciones y la temporada (por defecto, la más
reciente). Si la temporada está en curso, la barra lateral lo indica junto con la fecha de los
datos.

| Sección | Qué muestra |
|---|---|
| **Inicio** | Campeón o líder, ventaja de local, máximo goleador, hallazgos principales, método y limitaciones. |
| **Clasificación** | Tabla calculada (total, local o visitante), puntos por equipo y puntos acumulados partido a partido. |
| **Análisis** | Cada estadística frente a los puntos, correlaciones de local y visitante, tiros al arco frente a goles y rankings. |
| **Comparador de equipos** | Dos equipos frente a frente en 13 estadísticas, en total, de local o de visitante. |
| **Local vs. visitante** | Un equipo dentro y fuera de casa, con una conclusión calculada a partir de los datos. |
| **Relaciones y correlaciones** | Correlación de Pearson, gráficos de dispersión y matriz de correlación con mapa de calor. |
| **Ranking personalizado** | Los 20 equipos ordenados por la estadística elegida. |
| **Récords históricos** | Récords de una temporada, acumulados de las temporadas terminadas y récords de partidos. |
| **Goleadores y Asistencias** | Máximos goleadores y asistentes de cada temporada, con sus fuentes. |
| **Partidos** | Búsqueda de partidos y ficha completa de cada uno. |
| **Detector de sorpresas** | Partidos en los que tiros o córners contrastan con el resultado. |
| **Analizador predictivo** | Probabilidad de victoria local, empate y victoria visitante, explicación y calidad del modelo. |
| **Asistente IA** | Chatbot: estadísticas, comparaciones, próximos partidos y probabilidades, con tablas y gráficos. |
| **Curiosidades** | Datos llamativos de la temporada y el botón SORPRÉNDEME. |

## Arquitectura

```
Football-Data.co.uk ──► data/raw/ ──► src/limpieza.py ──► data/processed/ ──┬──► app.py (secciones)
fixturedownload.com ──► data/calendario/                                     │
                                       src/variables_modelo.py ◄─────────────┤
                                       src/modelo.py + src/evaluacion.py     │
                                       src/entrenar_modelo.py ──► data/modelo/
                                       src/chatbot.py ◄── estadísticas, calendario y modelo
GitHub Actions ──► src/actualizar_datos.py (descarga, valida, recalcula y publica)
```

| Parte | Archivos |
|---|---|
| Carga y validación | `src/limpieza.py`, `src/preparar_datos.py` |
| Estadísticas y secciones | `src/estadisticas.py`, `src/analisis.py`, `src/tablero.py`, `src/comparador.py`, `src/correlaciones.py`, `src/ranking.py`, `src/records.py`, `src/sorpresas.py`, `src/curiosidades.py`, `src/partidos.py`, `src/jugadores.py` |
| Variables del modelo | `src/variables_modelo.py` |
| Entrenamiento y predicción | `src/modelo.py` |
| Evaluación | `src/evaluacion.py` |
| Generar evaluación y predicciones | `src/entrenar_modelo.py` |
| Calendario | `src/calendario.py` |
| Interpretación de preguntas | `src/chatbot.py`, `src/asistente.py`, `src/interprete_llm.py` (opcional) |
| Interfaz | `app.py`, `src/secciones.py`, `src/pagina_prediccion.py`, `src/graficos.py`, `src/estilos.py`, `src/equipos.py` |
| Automatización | `src/actualizar_datos.py`, `.github/workflows/actualizar-datos.yml` |

## Modelo predictivo

### Qué es una regresión logística multinomial

El modelo mira partidos anteriores y aprende cómo se relacionan las diferencias entre los dos
equipos con el resultado. Para un partido nuevo calcula tres probabilidades que suman 100 %:
victoria local, empate y victoria visitante. Se llama *multinomial* porque hay tres resultados
posibles en lugar de dos. Las cifras salen de `predict_proba()` de scikit-learn, sin redondeos
ni ajustes manuales.

Se usa un `Pipeline` con tres pasos que se ajustan **solo con los partidos de entrenamiento**:

1. imputación con la mediana (rellena huecos, por ejemplo el dato de tiros que falta);
2. escalado (media 0 y desviación 1);
3. `LogisticRegression(solver="lbfgs", C=0.1, max_iter=1000)`.

El valor de `C` (la regularización) se eligió en la temporada de validación, comparando
0,01, 0,1, 1 y 10 por *log loss*.

### Variables predictoras (todas de antes del partido)

| Variable | Ventana |
|---|---|
| Diferencia de puntos, goles a favor y goles en contra por partido | últimos 5 partidos (forma) |
| Diferencia de puntos, diferencia de goles, tiros, tiros al arco, córners, faltas y tarjetas por partido | últimos 38 partidos (nivel) |
| Puntos por partido del local en casa y del visitante fuera | últimos 10 en esa condición |
| Equipo sin historial (por ejemplo, recién ascendido) | 1 si tiene menos de 5 partidos en el último año |

Son 14 variables. La lista exacta está en `src/variables_modelo.py` y en `data/modelo/evaluacion.json`.

### Medidas contra la fuga de datos

- Las variables de un partido solo usan partidos de **fechas anteriores**. Los CSV no traen una
  hora fiable, así que los partidos del mismo día tampoco se usan.
- Solo cuentan los partidos del último año. Así un equipo que vuelve a Primera tras varias
  temporadas no arrastra datos viejos.
- La imputación y el escalado se ajustan dentro del `Pipeline`, solo con el entrenamiento.
- Las particiones son cronológicas. Nunca son al azar.
- Varias pruebas automáticas lo comprueban. Por ejemplo, si se cambian los resultados de los
  partidos futuros, las variables y las predicciones de un partido pasado siguen idénticas
  (`tests/test_modelo.py`).

### Entrenamiento y validación cronológica

2020/21 solo sirve de historial, porque nadie tiene partidos anteriores en ella.

| Conjunto | Temporadas | Partidos |
|---|---|---|
| Entrenamiento | 2021/22 a 2023/24 | 1.140 |
| Validación (elegir `C`) | 2024/25 | 380 |
| Prueba | 2025/26 y 2026/27 (hasta el 08/11/2026) | 480 |

Para la prueba se entrena con 2021/22 a 2024/25 (1.520 partidos). El modelo que usa la
aplicación se entrena después con los 2.000 partidos jugados. Su versión es
«RL multinomial v1 · 2000 partidos · hasta 08/11/2026». La comparación es con un **baseline
histórico**: las frecuencias de victoria local, empate y victoria visitante del entrenamiento.

### Métricas reales (conjunto de prueba, 480 partidos)

| Métrica | Modelo | Baseline |
|---|---|---|
| Accuracy | 48,1 % | 42,5 % |
| Balanced accuracy | 42,7 % | 33,3 % |
| F1 macro | 0,361 | 0,199 |
| Log loss (menor es mejor) | 1,043 | 1,085 |
| Brier multiclase (menor es mejor) | 0,626 | 0,656 |

Matriz de confusión (filas = resultado real, columnas = predicción):

| Real \ Predicho | Local | Empate | Visitante |
|---|---|---|---|
| Victoria local (204) | 157 | 1 | 46 |
| Empate (131) | 82 | 0 | 49 |
| Victoria visitante (145) | 70 | 1 | 74 |

Backtesting (se entrena con las temporadas anteriores y se prueba en la siguiente):

| Temporada probada | Partidos | Accuracy modelo | Accuracy baseline | Log loss modelo | Log loss baseline |
|---|---|---|---|---|---|
| 2023/24 | 380 | 57,6 % | 46,1 % | 0,945 | 1,054 |
| 2024/25 | 380 | 52,9 % | 40,8 % | 0,990 | 1,083 |
| 2025/26 | 380 | 48,9 % | 42,6 % | 1,035 | 1,085 |
| 2026/27 (100 partidos) | 100 | 44,0 % | 42,0 % | 1,065 | 1,084 |

**Lectura honesta:**

- El modelo es mejor que el baseline en todas las métricas, pero acierta menos de la mitad de los
  partidos de prueba.
- **Casi nunca predice el empate** (2 veces en 480 partidos, ninguna acertada). El empate rara vez es
  el resultado más probable, aunque ocurre en más de un cuarto de los partidos.
- La ventaja sobre el baseline baja en las temporadas más recientes.
- La calibración es razonable: cuando el modelo da entre 60 % y 80 %, ese resultado ocurrió el 64 %
  de las veces. El detalle está en la pestaña «Calidad del modelo».

Las métricas se recalculan solas cuando llegan partidos nuevos, así que pueden cambiar respecto
a esta tabla. La aplicación siempre muestra las vigentes.

## Chatbot (sección Asistente IA)

Es un chatbot **híbrido basado en reglas**:

1. reconoce la intención de la pregunta con palabras clave (ranking, comparación, próximo
   partido, probabilidades, por qué, confiabilidad, clasificación…), y también los equipos y la
   temporada;
2. llama a funciones verificadas de Python que calculan la respuesta con los datos, el
   calendario o el modelo;
3. devuelve un resultado estructurado (texto, tabla, tarjetas, barras de probabilidad, gráfico y
   fuente), que Streamlit dibuja según el tipo de pregunta.

Ejemplos: «¿Quién ganó más partidos en 2025/26?», «Compara Arsenal y Liverpool», «¿Cuál es el
próximo partido del Manchester City?», «¿Qué probabilidades tiene el Chelsea de ganar su
siguiente encuentro?», «¿Por qué el modelo estima esas probabilidades?», «¿Qué tan confiable es
el modelo?».

- **Nunca inventa cifras.** Las probabilidades son las mismas de `predict_proba()`, y una prueba
  lo comprueba. Si falta información, lo dice: por ejemplo, un equipo que no juega la temporada,
  o el final de la temporada, cuando ya no quedan partidos pendientes.
- Recuerda la conversación con `st.session_state`. Por ejemplo, «¿por qué?» se refiere a la
  última predicción.
- **Funciona sin servicios de pago ni internet.** Opcionalmente se puede configurar una clave
  `LLM_API_KEY` en los secretos de Streamlit (nunca en el código). En ese caso, un modelo de
  lenguaje solo traduce a una intención las preguntas que las reglas no entienden. Las cifras
  siguen saliendo de las funciones del proyecto. Sin clave, la aplicación funciona igual.
- El modelo no se entrena con cada mensaje. Se entrena una vez por versión de los datos (caché de
  Streamlit) y se vuelve a entrenar solo cuando cambian los archivos.

## Actualización automática (GitHub Actions)

El workflow `.github/workflows/actualizar-datos.yml` se ejecuta cuatro veces al día (06:17,
12:17, 18:17 y 23:17 UTC). También se puede lanzar a mano desde la pestaña *Actions*
(`workflow_dispatch`). Funciona aunque nadie tenga abierta la aplicación.

1. Descarga el CSV de la temporada en curso y el calendario.
2. Lo convierte al formato del proyecto y lo valida: columnas, fechas, números, resultados y
   partidos repetidos.
3. Lo compara con la versión guardada. Si no hay nada nuevo, termina sin tocar ningún archivo.
   Si cambió el marcador de un partido ya guardado o desapareció un partido, se detiene para que
   alguien lo revise.
4. En una copia de `data/`, recalcula las tablas, la evaluación del modelo y las predicciones.
   Solo si todo sale bien reemplaza los archivos.
5. Ejecuta todas las pruebas. Si alguna falla, no publica nada.
6. Hace un commit con los datos nuevos. Streamlit Community Cloud se vuelve a desplegar con ese
   commit, y la aplicación y el chatbot usan la versión nueva.

Tiene permisos mínimos (`contents: write`), nunca corre dos veces a la vez y deja un resumen en
cada ejecución. Cada actualización queda registrada en `data/actualizacion.json` y en
`data/registro_actualizaciones.csv`. Cuando una temporada termina, el script busca la
siguiente; mientras su archivo no tenga datos válidos, no cambia nada.

La actualización depende de que Football-Data.co.uk publique los resultados (suele hacerlo unas
horas después de cada partido) y de que GitHub ejecute el workflow programado. No es
instantánea.

## Estructura del repositorio

```
premier-league-dashboard/
├── app.py                     aplicación de Streamlit
├── requirements.txt           librerías necesarias
├── .streamlit/config.toml     colores y configuración de la app
├── .github/workflows/         actualización automática
├── data/
│   ├── README.md              fuentes, variables y decisiones de limpieza
│   ├── raw/                   un CSV por temporada
│   ├── processed/             tablas generadas por src/preparar_datos.py
│   ├── calendario/            calendario de la temporada en curso
│   ├── modelo/                evaluación del modelo y predicciones
│   ├── jugadores/             goleadores, asistencias y sus fuentes
│   ├── actualizacion.json     última actualización
│   └── registro_actualizaciones.csv
├── notebooks/                 análisis paso a paso en Google Colab
├── src/                       funciones del proyecto (ver tabla de arquitectura)
├── tests/                     pruebas automáticas
├── instalar.bat               instalación en Windows con doble clic
├── ejecutar_app.bat           abre la aplicación en Windows
└── ejecutar_pruebas.bat       ejecuta las pruebas en Windows
```

## Tecnologías

| Herramienta | Uso en el proyecto |
|---|---|
| Python 3.12 | Lenguaje del proyecto |
| pandas | Leer los CSV, filtrar, agrupar y ordenar tablas |
| NumPy | Correlación de Pearson, recta de tendencia y estadísticas descriptivas |
| scikit-learn | Regresión logística multinomial, `Pipeline` y métricas de evaluación |
| Streamlit | Aplicación web y despliegue en Streamlit Community Cloud |
| Altair | Gráficos interactivos |
| GitHub Actions | Actualización automática de datos y modelo |
| Google Colab | Notebooks del análisis paso a paso |
| pytest | Pruebas automáticas |

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
4. Ejecuta la aplicación: `streamlit run app.py` (se abre en `http://localhost:8501`).

**Otros comandos**, desde la carpeta raíz:

| Comando | Qué hace |
|---|---|
| `python -m src.preparar_datos` | Regenera `data/processed/` desde `data/raw/` |
| `python -m src.entrenar_modelo` | Regenera la evaluación del modelo y las predicciones |
| `python -m src.actualizar_datos` | Descarga y aplica los resultados nuevos (lo mismo que GitHub Actions) |
| `python -m src.actualizar_datos --archivo E0.csv` | Lo mismo, con un CSV ya descargado |

**Despliegue:** en Streamlit Community Cloud, con el archivo principal `app.py` y **Python
3.12** en *Advanced settings*. La versión de Python no se puede cambiar después: hay que borrar
la app y desplegarla de nuevo. La clave `LLM_API_KEY` es opcional y va en *Secrets*.

## Notebooks

Se abren en Google Colab (Archivo → Subir notebook) y se ejecutan en orden: 1. carga y
limpieza; 2. estadísticas por equipo; 3. análisis exploratorio. Muestran paso a paso el análisis
de las cinco primeras temporadas. El modelo predictivo y las temporadas nuevas están en `src/`.

## Pruebas

```
pip install pytest
python -m pytest tests
```

Las pruebas comprueban, entre otras cosas:

- **Datos:** temporadas correctas, fechas válidas, sin partidos repetidos, puntos y goles que
  cuadran partido a partido, y clasificaciones iguales a las oficiales.
- **Modelo:** que no haya fuga de datos, que el entrenamiento sea reproducible y las
  probabilidades válidas, que la evaluación sea cronológica y el manejo de datos insuficientes.
- **Chatbot:** que entienda las preguntas de ejemplo, que muestre las mismas probabilidades que
  `predict_proba()`, las preguntas ambiguas y que funcione sin API externa.
- **Actualización:** que no cambie nada sin novedades, que rechace archivos inválidos, que
  conserve la última versión válida si algo falla y que se pueda ejecutar a mano.
- **Aplicación:** que las 14 secciones abran sin errores en todas las temporadas (con la
  herramienta oficial `AppTest` de Streamlit).

## Resultados principales (temporadas 2020/21 a 2024/25)

- Los tiros al arco son la estadística de juego más relacionada con los puntos (r = 0,86 con
  100 equipo-temporada).
- La relación es parecida de local y de visitante (r = 0,82 y 0,78); lo que cambia es el
  nivel: de local los equipos suman en promedio 0,28 puntos más por partido.
- 2020/21, jugada casi sin público, fue la única de esas temporadas en que los visitantes
  ganaron más partidos que los locales.

## Limitaciones

- Correlación no es causalidad: la calidad de cada equipo influye a la vez en sus estadísticas
  y en sus puntos.
- No hay datos de posesión, calidad de las ocasiones, lesiones, alineaciones ni fichajes, y los
  autogoles no se identifican.
- El modelo acierta menos de la mitad de los partidos de prueba y casi nunca predice el empate.
  Un partido lejano en el calendario se estima con los datos de hoy.
- Los puntos son los ganados en el campo: no incluyen las sanciones de 2023/24, que la
  aplicación muestra aparte.
- Los goleadores y asistentes de la temporada en curso no se actualizan solos.

## Explicación breve para la sustentación

- **Ingeniería de datos:** los CSV se validan (columnas, fechas, resultados, partidos
  repetidos) y se transforman en tres niveles: partido, equipo en un partido y equipo en una
  temporada. Un proceso automático incorpora los resultados nuevos y nunca publica datos que no
  pasen las comprobaciones.
- **Estadística:** promedios por partido, correlación de Pearson y comparación entre local y
  visitante.
- **Aprendizaje automático supervisado:** cada partido jugado es un ejemplo. Las variables son
  lo que se sabía de los equipos antes del partido, y la etiqueta es el resultado. Se evalúa
  entrenando con el pasado y probando con el futuro, como pasaría en la realidad.
- **Software:** el código está separado en módulos, hay 160 pruebas automáticas, se usa
  caché y la integración continúa con GitHub Actions.
- **Qué no es:** el chatbot no es inteligencia artificial generativa. Usa reglas, consultas a
  los datos y un modelo de aprendizaje supervisado. El modelo de lenguaje es opcional y solo
  interpreta preguntas.

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
- FixtureDownload. (s. f.). *English Premier League 2026/27 fixtures*. https://fixturedownload.com/
- ESPN. (s. f.). *English Premier League stats* (temporadas 2021/22 a 2026/27). https://www.espn.co.uk/football/stats/_/league/ENG.1
- Premier League. (s. f.). Premios oficiales de goleador y asistente. https://www.premierleague.com/news/2154211, https://www.premierleague.com/en/news/4021251 y https://www.premierleague.com/en/news/4668605
- Wikipedia. (s. f.). *2020–21 Premier League*. https://en.wikipedia.org/wiki/2020%E2%80%9321_Premier_League
- Pedregosa, F. et al. (2011). Scikit-learn: Machine Learning in Python. *Journal of Machine Learning Research, 12*, 2825–2830.
- Documentación de [Streamlit](https://docs.streamlit.io/), [pandas](https://pandas.pydata.org/docs/), [NumPy](https://numpy.org/doc/), [scikit-learn](https://scikit-learn.org/stable/), [Altair](https://altair-viz.github.io/) y [GitHub Actions](https://docs.github.com/actions).
