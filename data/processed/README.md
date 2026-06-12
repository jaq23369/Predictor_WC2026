# Processed Data

Archivos generados por:

```bash
python3 scripts/prepare_datasets.py
```

## matches_clean.csv

Partidos historicos con marcador disponible. No incluye fixtures sin resultado.

## world_cup_2026_fixtures.csv

Partidos del Mundial 2026 sin marcador. Este archivo queda separado para prediccion y simulacion, no para entrenamiento.

## elo_clean.csv

Ratings Elo normalizados con fechas en formato `YYYY-MM-DD` y nombres de equipos limpios.

## fifa_rankings_clean.csv

Ranking FIFA normalizado. El campo `ranking_date` aproxima cada semestre como:

- semestre 1: `YYYY-06-30`
- semestre 2: `YYYY-12-31`

## training_matches.csv

Dataset historico completo para modelado. Cada partido genera dos filas:

- una desde la perspectiva del local
- otra desde la perspectiva del visitante

La variable objetivo es `target`:

- `0`: derrota de `team_a`
- `1`: empate
- `2`: victoria de `team_a`

## training_matches_modern.csv

Subconjunto desde `1993-01-01`, pensado para entrenamientos mas comparables con el futbol moderno y con cobertura FIFA.

## training_matches_model_ready.csv

Subconjunto moderno con features clave completas:

- `elo_diff`
- `fifa_rank_diff`
- `fifa_points_diff`
- `wins_last_10`
- `opponent_wins_last_10`

## final_training_dataset.csv

Dataset oficial para entrenar el primer modelo de clasificacion.

Parte de `training_matches_model_ready.csv`, pero excluye `goals_for` y `goals_against`
para evitar que el entrenamiento use informacion que solo se conoce despues del partido.

Incluye variables dinamicas calculadas solo con partidos anteriores a cada fecha:

- puntos recientes
- goles recientes
- clean sheets
- forma ponderada
- calidad promedio de rivales por Elo
- rendimiento contra rivales top 30 y top 50
- tendencia Elo reciente
- diferencias de forma entre `team_a` y `team_b`

## fbref_team_match_stats.csv

Archivo opcional generado por:

```bash
.venv/bin/python scripts/sync_fbref_stats.py
```

Contiene estadisticas avanzadas descargadas offline con `soccerdata` desde FBref, cuando la liga/temporada solicitada esta disponible.

Campos esperados:

- xG y xGA
- tiros y tiros al arco
- tarjetas
- faltas
- centros
- intercepciones

## fbref_team_form_features.csv

Resumen por seleccion calculado desde `fbref_team_match_stats.csv`.

Estas variables se usan primero como contexto exploratorio. Antes de agregarlas al dataset de entrenamiento se debe validar:

- cobertura suficiente de selecciones
- suficientes partidos por seleccion
- que cada feature use solo informacion disponible antes del partido
- mejora real en validacion temporal

## fbref_coverage.csv

Resumen de cobertura y errores de la sincronizacion FBref/soccerdata.

## world_cup_2026_manual_match_stats.csv

Estadisticas curadas manualmente de partidos ya jugados del Mundial 2026, una fila por partido.

Este archivo sirve como fuente post-partido para:

- validar predicciones realizadas antes del partido
- enriquecer analisis del partido terminado
- crear features futuras de rendimiento real del torneo

No debe mezclarse con features pre-partido sin transformar, porque incluye informacion que solo se conoce despues del partido.

## world_cup_2026_manual_team_match_stats.csv

Version por seleccion de `world_cup_2026_manual_match_stats.csv`, con una fila por equipo-partido.

Este es el formato mas util para modelado futuro porque permite calcular ventanas dinamicas por seleccion:

- goles recientes en el torneo
- tiros, tiros al arco y corners recientes
- faltas, amarillas y rojas recientes
- posesion y pases recientes
- diferencial contra el rival

Antes de usarlo para entrenar modelos de eliminatorias, las variables deben agregarse como historico previo al partido objetivo. Es decir, para predecir octavos no se debe usar informacion de octavos, solo grupos y partidos anteriores.

## world_cup_2026_manual_goal_events.csv

Eventos de gol curados manualmente, una fila por gol. Permite analizar goleadores, asistencias y momentos de gol.

## world_cup_2026_manual_h2h.csv

Historial directo curado para cruces relevantes. Se mantiene separado porque puede incluir partidos de torneos o amistosos fuera del dataset principal.

## world_cup_2026_manual_h2h_summary.csv

Resumen del historial directo por par de selecciones. Sirve como contexto exploratorio y posible feature si se calcula sin data leakage.

## world_cup_2026_manual_recent_results.csv

Resultados recientes curados manualmente cuando la fuente del partido aporta contexto pre-partido adicional.

Se mantiene separado del dataset principal porque puede contener partidos externos al Mundial 2026. Para modelado, debe usarse solo si la fecha del resultado es anterior al partido que se quiere predecir.

## world_cup_2026_manual_recent_form_coverage.csv

Control de cobertura de forma reciente por seleccion en los partidos curados manualmente.

Permite ver si una seleccion tiene:

- forma compacta (`form_last_5`)
- resultados recientes detallados
- estadisticas agregadas recientes

Esto evita asumir que todas las selecciones tienen la misma calidad de contexto pre-partido.

## world_cup_2026_manual_top_players_pre_match.csv

Jugadores destacados antes del partido: goleador, asistidor y portero con mas clean sheets segun la fuente disponible.

Sirve para analisis visual y como posible feature agregada de fortaleza ofensiva/defensiva, pero primero debe validarse cobertura suficiente para todas las selecciones.
