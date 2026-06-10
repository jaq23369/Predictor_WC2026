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
