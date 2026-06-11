# Plan API-Football para estadisticas de contexto

## Objetivo

Usar API-Football para enriquecer el predictor con estadisticas reales de estilo de juego por seleccion:

- corners promedio
- faltas promedio
- tarjetas amarillas promedio
- tarjetas rojas promedio
- tiros al arco promedio
- tiros totales promedio
- posesion promedio

Estas variables no sustituyen Elo, ranking FIFA, forma reciente ni el modelo principal. Funcionan como contexto historico reciente para entender mejor el perfil de cada seleccion.

---

## Restricciones del plan gratis

El plan gratis permite:

- 100 requests por dia
- 10 requests por minuto
- acceso a temporadas historicas disponibles, actualmente 2022 a 2024 para fixtures

Limitacion importante:

```text
No permite fixtures de temporada 2026 en el plan gratis.
```

Por eso estas estadisticas se usaran como informacion historica de estilo, no como datos en vivo del Mundial 2026.

---

## Estrategia de sincronizacion

La sincronizacion debe ser:

```text
offline
incremental
cacheada
con presupuesto diario
```

No se deben hacer llamadas en vivo desde FastAPI ni desde el frontend.

Script:

```bash
.venv/bin/python scripts/sync_api_football.py --daily-budget 80 --season 2024 --from-date 2024-01-01 --to-date 2024-12-31
```

El script guarda respuestas crudas en:

```text
data/api_cache/api_football/
```

Y genera CSVs procesados en:

```text
data/processed/api_football_team_mapping.csv
data/processed/api_football_fixtures.csv
data/processed/api_football_fixture_statistics.csv
data/processed/api_football_team_match_stats.csv
data/processed/api_football_coverage.csv
```

---

## Endpoints usados

### 1. Buscar seleccion

```http
GET /teams?search={team_name}
```

Uso:

- obtener `team_id`
- mapear nombres del proyecto con nombres de API-Football
- guardar logo si esta disponible

### 2. Fixtures historicos por seleccion

```http
GET /fixtures?team={team_id}&season=2024&from=2024-01-01&to=2024-12-31
```

Uso:

- obtener partidos jugados por seleccion
- identificar `fixture_id`
- filtrar partidos terminados

### 3. Estadisticas por partido

```http
GET /fixtures/statistics?fixture={fixture_id}
```

Uso:

- corners
- faltas
- tarjetas
- tiros
- posesion

---

## Variables procesadas

Archivo final principal:

```text
data/processed/api_football_team_match_stats.csv
```

Columnas:

```text
team
fixtures_with_stats
avg_shots_on_goal
avg_total_shots
avg_fouls
avg_corners
avg_yellow_cards
avg_red_cards
avg_possession
```

Estas metricas se calculan solo con fixtures que tienen estadisticas disponibles.

---

## Uso en frontend

En la vista `Predecir`, dentro del detalle del partido, mostrar:

- goles esperados del modelo
- goles recientes disponibles
- corners promedio
- tiros al arco promedio
- posesion promedio
- tarjetas amarillas promedio
- tarjetas rojas promedio
- faltas promedio

Regla visual:

```text
Si una seleccion no tiene dato disponible, mostrar "Sin dato".
```

Texto metodologico sugerido:

```text
Corners, tarjetas, faltas, tiros y posesion usan estadisticas historicas disponibles de API-Football 2024 cuando existen.
```

---

## Uso en modelo

No meter estas variables al modelo principal hasta tener cobertura suficiente.

Condicion minima recomendada:

```text
al menos 35 de 48 selecciones con estadisticas
al menos 3 fixtures con stats por seleccion
```

Cuando haya cobertura suficiente, probar como features secundarias:

```text
avg_corners_diff
avg_fouls_diff
avg_yellow_cards_diff
avg_shots_on_goal_diff
avg_possession_diff
```

Estas variables deben tener menor peso conceptual que:

- Elo
- ranking FIFA
- forma dinamica calculada sin leakage
- calidad de rivales
- valor y profundidad de plantilla

---

## Estado actual

Primera tanda completada:

```text
requests_used = 60
fixtures = 71
stat_rows = 2320
teams_with_stats = 11
```

Selecciones con estadisticas disponibles:

```text
Algeria
Argentina
Australia
Austria
Belgium
Bosnia and Herzegovina
Brazil
Canada
South Africa
Spain
Switzerland
```

Pendiente:

- continuar sync por tandas diarias
- priorizar selecciones que aparecen con "Sin dato" en partidos importantes
- no usar como feature de entrenamiento hasta mejorar cobertura

---

## Recomendacion operativa

Correr una tanda diaria:

```bash
.venv/bin/python scripts/sync_api_football.py --daily-budget 80 --season 2024 --from-date 2024-01-01 --to-date 2024-12-31
```

Despues revisar:

```text
data/processed/api_football_coverage.csv
```

Cuando `teams_with_stats` suba, el frontend lo reflejara automaticamente.

---

## Datos adicionales que conviene pedir

API-Football puede aportar mas contexto, pero no todo debe ir directo al modelo. La prioridad debe ser separar:

- datos para mejorar el predictor
- datos para mejorar el analisis visual
- datos que solo sirven si hay cobertura suficiente

### Prioridad alta: estadisticas de fixtures

Endpoint:

```http
GET /fixtures/statistics?fixture={fixture_id}
```

Uso principal:

- corners promedio por seleccion
- faltas promedio por seleccion
- amarillas promedio
- rojas promedio
- tiros al arco promedio
- tiros totales promedio
- posesion promedio

Decision:

```text
Seguir pidiendo esto primero hasta cubrir al menos 35 de 48 selecciones.
```

Estas son las variables mas utiles porque describen estilo de juego y pueden convertirse en diferencias entre equipos.

### Prioridad media: eventos de partido

Endpoint:

```http
GET /fixtures/events?fixture={fixture_id}
```

Uso posible:

- goleadores recientes
- tarjetas por jugador
- minutos de goles
- sustituciones
- jugadores con participacion ofensiva reciente

Uso recomendado:

```text
Primero usarlo para analisis y frontend, no para entrenamiento.
```

Puede alimentar secciones como:

- jugador destacado
- riesgo disciplinario
- seleccion que suele marcar temprano o tarde
- jugadores que aparecen seguido en eventos importantes

### Prioridad media: alineaciones

Endpoint:

```http
GET /fixtures/lineups?fixture={fixture_id}
```

Uso posible:

- titulares recientes
- formaciones frecuentes
- jugadores usados con mas frecuencia
- alineaciones probables para el frontend

Uso recomendado:

```text
Usarlo para enriquecer la vista de partido y analisis de selecciones.
```

No deberia entrar al modelo hasta que tengamos una forma clara de convertirlo en variables numericas confiables.

### Prioridad baja: head to head

Endpoint posible:

```http
GET /fixtures/headtohead?h2h={team_id_a}-{team_id_b}
```

Uso posible:

- ultimos enfrentamientos directos
- promedio de goles entre ambos
- historial visual del partido

Decision:

```text
Usarlo solo como contexto visual o ajuste pequeno.
```

No debe pesar mas que Elo, ranking FIFA, forma reciente o calidad de rival, porque el head to head puede ser enganoso si los partidos son muy antiguos o con plantillas diferentes.

---

## Plan por dia

El limite es 100 requests por dia. Para evitar bloqueo, el presupuesto recomendado es 60 a 80 requests por tanda.

### Dia 1: completar cobertura base

Objetivo:

```text
Subir teams_with_stats lo mas posible.
```

Pedir:

- busqueda/mapping de selecciones faltantes si no estan cacheadas
- fixtures 2024 para selecciones faltantes
- estadisticas de fixtures terminados

Comando sugerido:

```bash
.venv/bin/python scripts/sync_api_football.py --daily-budget 80 --season 2024 --from-date 2024-01-01 --to-date 2024-12-31
```

Validar:

```text
data/processed/api_football_coverage.csv
```

Meta:

```text
teams_with_stats >= 20
```

### Dia 2: segunda tanda de estadisticas

Objetivo:

```text
Completar mas selecciones sin dato.
```

Pedir:

- fixtures 2024 restantes
- estadisticas de fixtures que falten

Meta:

```text
teams_with_stats >= 30
```

Si una seleccion no tiene fixtures utiles en 2024, probar una tanda historica alternativa:

```bash
.venv/bin/python scripts/sync_api_football.py --daily-budget 60 --season 2023 --from-date 2023-01-01 --to-date 2023-12-31
```

### Dia 3: cerrar cobertura minima

Objetivo:

```text
Llegar a la cobertura minima para evaluar si estas estadisticas entran al modelo.
```

Meta:

```text
teams_with_stats >= 35
fixtures_with_stats >= 3 por seleccion importante
```

Despues de este punto, evaluar features:

```text
avg_corners_diff
avg_fouls_diff
avg_yellow_cards_diff
avg_red_cards_diff
avg_shots_on_goal_diff
avg_total_shots_diff
avg_possession_diff
```

### Dia 4: eventos para jugadores destacados

Objetivo:

```text
Mejorar el analisis visual sin tocar aun el modelo.
```

Pedir:

- eventos de fixtures ya cacheados
- solo partidos terminados
- priorizar selecciones clasificadas y partidos con estadisticas disponibles

Salida deseada:

```text
data/processed/api_football_fixture_events.csv
data/processed/api_football_player_event_summary.csv
```

Variables visuales posibles:

```text
recent_goal_scorers
recent_card_risk_players
goal_minutes_profile
```

### Dia 5: lineups recientes

Objetivo:

```text
Mejorar alineaciones probables.
```

Pedir:

- lineups de fixtures recientes con buena cobertura
- titulares por seleccion
- formacion usada

Salida deseada:

```text
data/processed/api_football_lineups.csv
data/processed/api_football_probable_lineups.csv
```

Variables visuales posibles:

```text
common_formation
probable_starters
starter_frequency
```

### Dia 6: revisar si entra al modelo

Objetivo:

```text
No meter ruido al predictor.
```

Checklist:

- cobertura suficiente
- valores no vacios en la mayoria de selecciones
- no mezclar datos posteriores al partido que se predice en entrenamiento historico
- crear diferencias entre equipos, no solo valores absolutos
- probar metricas contra el modelo actual

Decision:

```text
Si mejora validacion temporal, se agregan como features.
Si no mejora, quedan solo como contexto del frontend.
```

---

## Regla para Vercel

En Vercel no se deben consultar estas APIs en vivo desde el frontend. La aplicacion debe leer CSVs procesados y cacheados.

Flujo correcto:

```text
sync local o GitHub Action
actualizar data/processed
commit
push
Vercel redeploy automatico
frontend consume backend con CSVs nuevos
```

Esto evita:

- gastar requests cada vez que un usuario abre la pagina
- errores por rate limit
- respuestas lentas
- exponer llaves de API en frontend
