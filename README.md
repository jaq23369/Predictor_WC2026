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
- estado de fases futuras

Por ahora solo hay datos concretos para fase de grupos. Octavos, cuartos, semifinales y final quedan marcados como pendientes hasta implementar simulacion Monte Carlo para clasificados y bracket.

## Nota metodologica

El dataset final evita usar goles reales como features para prevenir fuga de informacion.
Las variables de forma reciente, Elo y ranking FIFA se calculan con informacion disponible antes del partido.
