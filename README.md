# Predictor Inteligente del Mundial 2026

Proyecto para construir datasets, entrenar modelos y generar predicciones de partidos del Mundial 2026.

## Preparar datos

```bash
python3 scripts/prepare_datasets.py
.venv/bin/python scripts/prepare_transfermarkt_data.py
```

Genera:

- `data/processed/final_training_dataset.csv`
- `data/processed/training_matches_model_ready.csv`
- `data/processed/world_cup_2026_fixtures.csv`
- `data/processed/transfermarkt_national_team_values.csv`

## Instalar dependencias

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Entrenar modelos

```bash
.venv/bin/python scripts/train_classification_model.py
.venv/bin/python scripts/train_score_model.py
```

El entrenamiento de clasificacion compara:

- Logistic Regression
- Random Forest
- Extra Trees
- Hist Gradient Boosting

Artefactos:

- `models/artifacts/classification_model.pkl`
- `models/artifacts/poisson_score_model.pkl`

Reportes:

- `models/reports/classification_model_comparison.json`
- `models/reports/poisson_score_model_metrics.json`

## Predecir un partido

```bash
.venv/bin/python scripts/predict_match.py Mexico "South Africa" --date 2026-06-11 --neutral 0 --team-a-home 1
```

La salida incluye:

- probabilidades de victoria, empate y derrota
- goles esperados
- marcadores mas probables

## Predecir fixtures del Mundial 2026

```bash
.venv/bin/python scripts/predict_world_cup_fixtures.py
```

Genera:

- `data/processed/world_cup_2026_predictions.csv`

## Ejecutar backend FastAPI

```bash
.venv/bin/uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

URLs locales:

- API: `http://127.0.0.1:8000`
- Docs interactivas: `http://127.0.0.1:8000/docs`

Endpoints principales:

- `GET /health`
- `GET /teams`
- `POST /predict`
- `POST /scores`
- `GET /world-cup-2026/fixtures`
- `GET /world-cup-2026/predictions`
- `GET /world-cup-2026/monte-carlo?simulations=500`
- `GET /football-data/world-cup-2026/matches`
- `GET /football-data/world-cup-2026/teams`
- `GET /football-data/world-cup-2026/standings`
- `GET /transfermarkt/national-team-values`

Ejemplo:

```bash
curl -X POST http://127.0.0.1:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"team_a":"Mexico","team_b":"South Africa","match_date":"2026-06-11","neutral":false,"team_a_is_home":true}'
```

## Sincronizar football-data.org

Crear un archivo local `.env` con:

```bash
FOOTBALL_DATA_API_TOKEN=your_token_here
THESPORTSDB_API_KEY=123
THESPORTSDB_BASE_URL=https://www.thesportsdb.com/api/v1/json
```

Luego ejecutar:

```bash
.venv/bin/python scripts/sync_football_data.py --season 2026
```

Genera CSVs en `data/processed/`:

- `football_data_wc_2026_matches.csv`
- `football_data_wc_2026_teams.csv`
- `football_data_wc_2026_standings.csv`

Tambien guarda respuestas crudas en `data/api_cache/football_data/`, carpeta ignorada por Git.

El cliente usa el header `X-Auth-Token` y revisa respuestas `429` para respetar throttling con `Retry-After`.

## Sincronizar TheSportsDB V1

TheSportsDB se usa como fuente complementaria offline para forma reciente, plantillas, metadata visual y, opcionalmente, estadisticas de partidos recientes. No reemplaza Elo, FIFA, football-data.org ni Transfermarkt.

Sync basico recomendado:

```bash
.venv/bin/python scripts/sync_thesportsdb.py
```

Genera:

- `data/processed/thesportsdb_team_mapping.csv`
- `data/processed/thesportsdb_players.csv`
- `data/processed/thesportsdb_events.csv`
- `data/processed/thesportsdb_recent_form.csv`
- `data/processed/thesportsdb_coverage.csv`

Tambien guarda respuestas crudas en `data/api_cache/thesportsdb/`, carpeta ignorada por Git.

Para intentar enriquecer eventos recientes con stats, alineaciones y timeline:

```bash
.venv/bin/python scripts/sync_thesportsdb.py --include-event-enrichment --max-events-per-team 5
```

Esto puede hacer bastantes requests. Conviene revisar `thesportsdb_coverage.csv` antes de usar estas variables en entrenamiento.

## Sincronizar API-Football

API-Football se usa para obtener estadisticas reales de partidos: tiros, corners, faltas, tarjetas y posesion. En el plan gratis hay dos limites importantes:

- 100 requests por dia.
- 10 requests por minuto.
- Fixtures disponibles en temporadas 2022 a 2024 en el plan gratis.

Por eso el sync es incremental y cacheado. Cada corrida completa algunos equipos sin repetir requests ya guardados.

Variables en `.env`:

```bash
API_FOOTBALL_API_KEY=your_api_football_key_here
API_FOOTBALL_BASE_URL=https://v3.football.api-sports.io
```

Sync recomendado:

```bash
.venv/bin/python scripts/sync_api_football.py --daily-budget 80 --season 2024 --from-date 2024-01-01 --to-date 2024-12-31
```

Genera:

- `data/processed/api_football_team_mapping.csv`
- `data/processed/api_football_fixtures.csv`
- `data/processed/api_football_fixture_statistics.csv`
- `data/processed/api_football_team_match_stats.csv`
- `data/processed/api_football_coverage.csv`

Tambien guarda cache crudo en `data/api_cache/api_football/`.

## Sincronizar FBref con soccerdata

FBref/soccerdata es una fuente opcional offline para metricas avanzadas como xG, tiros, tiros al arco, faltas, tarjetas, centros, intercepciones y otras senales de rendimiento. No se ejecuta en Vercel ni desde el frontend.

Instalar dependencias solo para sync local:

```bash
.venv/bin/pip install -r requirements-offline.txt
```

Sync recomendado:

```bash
.venv/bin/python scripts/sync_fbref_stats.py --league "INT-World Cup" --seasons 2022 2026 --stat-types schedule --delay 4
```

Para intentar metricas avanzadas de match logs, correrlo de forma separada porque FBref puede tardar bastante:

```bash
.venv/bin/python scripts/sync_fbref_stats.py --league "INT-World Cup" --seasons 2022 --stat-types shooting misc --delay 6
```

Si soccerdata/FBref no reconoce esa liga en tu entorno, revisar ligas disponibles con Python local y cambiar `--league`.

Genera:

- `data/processed/fbref_team_match_stats.csv`
- `data/processed/fbref_team_form_features.csv`
- `data/processed/fbref_coverage.csv`

Tambien usa cache local en:

```text
data/api_cache/soccerdata/FBref/
```

Endpoints para revisar cuando existan los CSVs:

- `GET /fbref/team-match-stats`
- `GET /fbref/team-form-features`
- `GET /fbref/coverage`

Estas variables no entran al entrenamiento automaticamente. Primero hay que revisar cobertura y luego probar si mejoran validacion temporal sin data leakage.

## Frontend

El frontend esta en `frontend/` y consume esta API FastAPI.

```bash
cd frontend
npm install
npm run dev -- --port 5173
```

URL local:

- `http://127.0.0.1:5173`

Antes de abrir el frontend, mantener corriendo el backend:

```bash
.venv/bin/uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

La interfaz muestra:

- predictor de partido individual
- probabilidades de victoria, empate y derrota
- goles esperados y marcadores probables
- predicciones de los 72 partidos de fase de grupos, separadas por grupo
- simulacion Monte Carlo de grupos, mejores terceros, eliminatorias y campeon

La simulacion Monte Carlo usa las probabilidades del modelo para simular fase de grupos, mejores terceros y eliminatorias. El bracket es aproximado y sembrado por rendimiento simulado hasta que se conecten reglas oficiales exactas de cruces.

## Deploy en Vercel

El proyecto esta preparado para desplegar frontend y backend en Vercel desde el mismo repositorio.

Estructura de deploy:

```text
frontend/        React + Vite
api/index.py     entrada serverless para FastAPI
backend/         aplicacion FastAPI
data/processed/  CSVs que usa la API
models/artifacts/ modelos entrenados
```

Archivos de configuracion:

```text
vercel.json
.vercelignore
.python-version
api/index.py
```

En Vercel:

1. Importar el repo:

```text
jaq23369/Predictor_WC2026
```

2. Usar la configuracion del repo. `vercel.json` define:

```text
buildCommand = cd frontend && npm install && npm run build
outputDirectory = frontend/dist
```

3. Agregar variables de entorno en Vercel:

```bash
FOOTBALL_DATA_API_TOKEN=your_token_here
THESPORTSDB_API_KEY=123
THESPORTSDB_BASE_URL=https://www.thesportsdb.com/api/v1/json
API_FOOTBALL_API_KEY=your_api_football_key_here
API_FOOTBALL_BASE_URL=https://v3.football.api-sports.io
CORS_ORIGINS=https://tu-proyecto.vercel.app
```

4. En produccion el frontend usa automaticamente:

```text
/api
```

Por eso no necesitas definir `VITE_API_BASE_URL` si frontend y backend viven en el mismo deploy de Vercel.

5. Verificar:

```text
https://tu-proyecto.vercel.app/api/health
https://tu-proyecto.vercel.app
```

Nota: Vercel Functions para Python incluyen archivos usados por el backend. `vercel.json` excluye `data/raw`, `data/api_cache`, `.venv`, `frontend` y scripts para mantener el bundle bajo los limites. Los datos usados en produccion deben estar en `data/processed/` y los modelos en `models/artifacts/`.

## Nota metodologica

El dataset final evita usar goles reales como features para prevenir fuga de informacion.
Las variables de forma reciente, Elo y ranking FIFA se calculan con informacion disponible antes del partido.
