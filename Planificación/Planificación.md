# Proyecto: Predictor Inteligente del Mundial 2026

## Objetivo

Construir una plataforma web capaz de:

* Predecir resultados de partidos del Mundial.
* Estimar probabilidades de victoria, empate y derrota.
* Generar marcadores probables.
* Simular fases de grupos.
* Simular eliminatorias.
* Calcular probabilidades de campeón mediante Monte Carlo.
* Permitir a los usuarios consultar predicciones mediante una interfaz web.

---

# FASE 1 - Investigación y Definición del Proyecto

## Objetivos

Definir:

* Alcance inicial.
* Variables a utilizar.
* Fuentes de datos.
* Arquitectura general.

## Entregables

Documento con:

* Objetivos.
* Fuentes de datos.
* Tecnologías seleccionadas.
* Cronograma.

---

# FASE 2 - Recolección de Datos

## Objetivo

Conseguir toda la información histórica necesaria para entrenar los modelos.

---

## Fuente 1: Resultados Históricos Internacionales

Fuente:

https://www.kaggle.com/datasets/martj42/international-football-results-from-1872-to-2017

Variables importantes:

```text
date
home_team
away_team
home_score
away_score
tournament
country
neutral
```

---

## Fuente 2: Elo Ratings

Fuente:

https://eloratings.net

Variables:

```text
team
elo
rank
date
```

Idealmente obtener:

* Elo actual.
* Elo histórico.

---

## Fuente 3: Ranking FIFA

Fuente:

https://inside.fifa.com/fifa-world-ranking/men

Variables:

```text
team
ranking
points
date
```

---

## Fuente 4: Estadísticas Avanzadas

Fuente:

https://github.com/statsbomb/open-data

Variables:

```text
xG
shots
passes
possession
assists
```

---

## Fuente 5: Valor de Mercado

Fuente:

https://www.transfermarkt.com

Variables:

```text
squad_value
average_age
market_value
```

---

## Resultado Esperado

Carpeta:

```text
data/raw/

results.csv
elo.csv
fifa_rankings.csv
statsbomb.csv
market_values.csv
```

---

# FASE 3 - Limpieza y Normalización

## Objetivo

Unificar todas las fuentes en un formato consistente.

---

## Problemas Esperados

Nombres distintos:

```text
USA
United States

Korea Republic
South Korea

IR Iran
Iran
```

---

## Solución

Crear:

```python
country_mapping.py
```

Ejemplo:

```python
country_map = {
    "USA": "United States",
    "IR Iran": "Iran",
    "Korea Republic": "South Korea"
}
```

---

## Estandarización

Convertir:

```text
Fechas
Nombres
Torneos
```

a un formato único.

---

## Resultado Esperado

```text
data/processed/

matches_clean.csv
```

---

# FASE 4 - Ingeniería de Características

## Objetivo

Crear variables predictivas.

---

## Variables Históricas

```text
wins_last_5
wins_last_10
draws_last_10
losses_last_10
```

---

## Variables Ofensivas

```text
avg_goals_scored
avg_goals_last_10
```

---

## Variables Defensivas

```text
avg_goals_conceded
clean_sheets
```

---

## Variables de Fuerza

```text
elo_team
elo_opponent
elo_difference

fifa_rank_team
fifa_rank_opponent

rank_difference
```

---

## Variables de Mercado

```text
market_value_team
market_value_opponent

market_value_difference
```

---

## Dataset Final

```text
match_date
team_a
team_b

elo_diff
rank_diff

goals_scored_avg
goals_conceded_avg

market_value_diff

target
```

Donde:

```text
target

0 = derrota
1 = empate
2 = victoria
```

---

# FASE 5 - Modelo de Clasificación

## Objetivo

Predecir:

```text
Victoria
Empate
Derrota
```

---

## Modelos a Evaluar

### Modelo 1

```python
LogisticRegression
```

---

### Modelo 2

```python
RandomForestClassifier
```

---

### Modelo 3

```python
XGBoost
```

---

## Métricas

```text
Accuracy
Precision
Recall
F1
```

---

## Resultado Esperado

Archivo:

```text
models/classification_model.pkl
```

---

# FASE 6 - Modelo de Marcadores

## Objetivo

Estimar goles esperados.

---

## Opción Recomendada

Distribución Poisson.

Variables:

```text
attack_strength
defense_strength
elo_difference
```

---

## Resultado

```text
Argentina vs España

Probabilidades:

0-0
1-0
2-0
2-1
1-1
```

---

## Entregable

```text
models/poisson_model.pkl
```

---

# FASE 7 - Simulación Monte Carlo

## Objetivo

Simular torneos completos.

---

## Proceso

Para cada partido:

1. Obtener probabilidades.
2. Generar resultado aleatorio.
3. Actualizar clasificación.
4. Continuar torneo.

---

## Cantidad de Simulaciones

```text
1000
5000
10000
```

---

## Resultado

```text
Argentina campeón: 21.8%
España campeón: 18.4%
Brasil campeón: 16.1%
```

---

# FASE 8 - Backend con FastAPI

## Objetivo

Exponer los modelos mediante API REST.

---

## Tecnologías

```text
Python
FastAPI
Uvicorn
Pydantic
```

---

## Endpoints

### Predicción

```http
POST /predict
```

Entrada:

```json
{
  "team_a": "Argentina",
  "team_b": "Spain"
}
```

Salida:

```json
{
  "winner":"Argentina",
  "win_probability":62.1,
  "draw_probability":20.3,
  "loss_probability":17.6
}
```

---

### Marcadores

```http
POST /scores
```

---

### Simulación

```http
POST /simulate
```

---

# FASE 9 - Base de Datos

## Tecnologías

```text
PostgreSQL
```

---

## Tablas

### Teams

```text
id
name
elo
ranking
market_value
```

---

### Predictions

```text
id
team_a
team_b
prediction
created_at
```

---

# FASE 10 - Frontend con React

## Tecnologías

```text
React
Vite
Tailwind
Axios
```

---

## Pantallas

### Inicio

Descripción del proyecto.

---

### Predictor

Seleccionar:

```text
Equipo A
Equipo B
```

Mostrar:

```text
Probabilidad de victoria
Probabilidad de empate
Probabilidad de derrota
```

---

### Predicción de Marcador

Mostrar:

```text
2-1
1-0
1-1
```

con porcentajes.

---

### Simulación Mundial

Mostrar:

```text
Tabla de grupos
Clasificados
Llaves eliminatorias
Campeón
```

---

# FASE 11 - Visualizaciones

## Librerías

```text
Chart.js
Recharts
```

---

## Gráficos

### Probabilidades

```text
Argentina 55%
Empate 25%
España 20%
```

---

### Probabilidades de Campeón

```text
Argentina
España
Brasil
Francia
```

---

# FASE 12 - Testing

## Backend

```text
Pytest
```

---

## Frontend

```text
Vitest
```

---

## Casos

* Equipos válidos.
* Equipos inexistentes.
* Empates.
* Simulaciones masivas.

---

# FASE 13 - Despliegue

## Backend

Opciones:

* Render
* Railway
* VPS

---

## Frontend

Opciones:

* Vercel
* Netlify

---

# FASE 15 - Mejoras Futuras

## IA Avanzada

* LightGBM
* CatBoost
* Redes Neuronales

---

## Nuevas Variables

* Lesiones.
* Suspensiones.
* Forma reciente.
* Convocatorias oficiales.

---

## Predicciones en Tiempo Real

Consumir APIs deportivas antes de cada partido.

---

# Estructura Final del Proyecto

```text
world-cup-predictor/

data/
 ├── raw/
 └── processed/

models/
 ├── classification_model.pkl
 └── poisson_model.pkl

backend/
 ├── app.py
 ├── routes/
 ├── services/
 └── database/

frontend/
 ├── src/
 ├── components/
 ├── pages/
 └── services/

notebooks/
 ├── exploration.ipynb
 ├── training.ipynb
 └── simulation.ipynb

docker/

README.md
```
