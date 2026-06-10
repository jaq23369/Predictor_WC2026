# Ventajas de usar football-data.org para mejorar el predictor del Mundial

## Objetivo del documento

Este documento explica cómo la API de `football-data.org` puede aportar información útil al predictor de partidos del Mundial.

La idea no es usar esta API únicamente como calendario, sino aprovechar sus datos para mejorar el análisis del modelo y ayudar a estimar:

- Ganador más probable.
- Probabilidad de empate.
- Probabilidad de derrota.
- Marcador más realista.
- Comparación entre predicción y resultado real.
- Actualización automática del sistema conforme avance el torneo.

Esta API debe verse como una **fuente operativa y contextual** para el predictor. Es decir, sirve para mantener actualizado el torneo real: partidos, fechas, equipos, fases, grupos, resultados, estados y datos relacionados. Para entrenar el modelo también se deben usar datasets históricos, rankings FIFA, Elo ratings y resultados internacionales.

---

## Uso general dentro del predictor

La API puede alimentar el sistema de esta forma:

```text
football-data.org
        ↓
Calendario, equipos, grupos, fases y resultados
        ↓
Base de datos propia del proyecto
        ↓
Normalización de nombres y equipos
        ↓
Generación de variables para el modelo
        ↓
Modelo predictivo
        ↓
Probabilidad de victoria, empate o derrota
        ↓
Marcador más realista
        ↓
Frontend con calendario + predicción + resultado real
```

El predictor no debería depender solamente de esta API, pero sí puede usarla para que las predicciones estén alineadas con el calendario real del Mundial.

---

## 1. Calendario actualizado del Mundial

La ventaja más directa es que la API permite obtener los partidos del Mundial desde el endpoint de competencia:

```http
GET https://api.football-data.org/v4/competitions/WC/matches
```

Esto ayuda a que el sistema tenga partidos reales y actualizados.

Datos útiles:

```text
fecha del partido
hora UTC
equipo local
equipo visitante
fase
grupo
sede
estado del partido
marcador
ganador
```

Aporte al predictor:

```text
El modelo sabe exactamente qué partidos debe predecir.
El sistema no depende de cargar manualmente el calendario.
Si cambia una fecha, sede o estado, el backend puede actualizarlo.
El frontend puede mostrar partidos reales y no datos estáticos.
```

Esto es importante porque el Mundial puede tener cambios de horarios, equipos todavía no definidos en fases eliminatorias y actualizaciones conforme se juegan los partidos.

---

## 2. Estados reales del partido

La API puede devolver estados como:

```text
SCHEDULED
TIMED
IN_PLAY
PAUSED
FINISHED
POSTPONED
SUSPENDED
CANCELLED
```

Esto le permite al sistema saber en qué momento se encuentra cada partido.

Aporte al predictor:

```text
Si el partido todavía no empieza, se muestra la predicción.
Si el partido está en vivo, se puede mostrar estado actualizado.
Si el partido terminó, se muestra el resultado real.
Si el partido se pospone, se evita hacer una predicción incorrecta con fecha vieja.
```

También permite separar claramente:

```text
partidos pendientes
partidos en vivo
partidos finalizados
partidos cancelados o pospuestos
```

Esto mejora la experiencia del usuario y evita mostrar predicciones como si fueran resultados reales.

---

## 3. Resultados reales para evaluar el modelo

Cuando un partido termina, la API puede proporcionar el marcador final:

```json
{
  "score": {
    "winner": "HOME_TEAM",
    "fullTime": {
      "home": 2,
      "away": 1
    }
  }
}
```

Aporte al predictor:

```text
Permite comparar la predicción con el resultado real.
Permite medir si se acertó el ganador.
Permite medir si se acertó el empate.
Permite medir qué tan cerca estuvo el marcador predicho.
Permite mejorar o recalibrar el modelo durante el torneo.
```

Métricas que pueden calcularse:

```text
accuracy de ganador
accuracy de empate
error promedio de goles
error absoluto por equipo
diferencia entre marcador predicho y marcador real
aciertos por fase
aciertos por grupo
aciertos por selección
```

Ejemplo:

```text
Predicción:
Francia 2 - 1 Alemania

Resultado real:
Francia 1 - 1 Alemania

Evaluación:
Ganador acertado: No
Empate acertado: No
Error goles Francia: 1
Error goles Alemania: 0
Error total de marcador: 1
```

Esto es clave porque el predictor no solo debe generar resultados, también debe poder medir su propio rendimiento.

---

## 4. Fases del torneo como variable predictiva

La API puede devolver el campo `stage`, por ejemplo:

```text
GROUP_STAGE
LAST_32
LAST_16
QUARTER_FINALS
SEMI_FINALS
THIRD_PLACE
FINAL
```

Aporte al predictor:

```text
La fase del torneo puede cambiar el comportamiento de los equipos.
Un partido de fase de grupos no se juega igual que una final.
Un equipo puede arriesgar menos en una eliminatoria.
Los partidos de eliminación directa pueden ser más cerrados.
En fase de grupos puede haber rotaciones si un equipo ya clasificó.
```

Feature sugerida:

```text
stage_encoded
```

Ejemplo:

```text
GROUP_STAGE = 0
LAST_32 = 1
LAST_16 = 2
QUARTER_FINALS = 3
SEMI_FINALS = 4
FINAL = 5
```

Esto ayuda al modelo a aprender que el contexto competitivo importa.

---

## 5. Grupos y posición dentro del grupo

La API puede proporcionar información del grupo del partido:

```text
GROUP_A
GROUP_B
GROUP_C
...
```

Además, mediante standings de la competencia, puede obtenerse información de la tabla.

Endpoint relacionado:

```http
GET https://api.football-data.org/v4/competitions/WC/standings
```

Datos útiles:

```text
puntos
partidos jugados
victorias
empates
derrotas
goles a favor
goles en contra
diferencia de goles
posición en el grupo
```

Aporte al predictor:

```text
El contexto del grupo afecta la estrategia.
Un equipo que necesita ganar puede atacar más.
Un equipo que solo necesita empatar puede jugar más conservador.
Un equipo eliminado puede jugar con menos presión.
Un equipo ya clasificado puede rotar jugadores.
```

Features sugeridas:

```text
home_group_position
away_group_position
home_points
away_points
home_goal_difference
away_goal_difference
home_needs_win
away_needs_win
home_already_qualified
away_already_qualified
```

Esto puede mejorar bastante las predicciones en la tercera jornada de fase de grupos.

---

## 6. Información de equipos participantes

La API puede listar los equipos de una competencia:

```http
GET https://api.football-data.org/v4/competitions/WC/teams
```

Datos útiles:

```text
id del equipo
nombre
nombre corto
abreviatura
escudo
país o área
```

Aporte al predictor:

```text
Permite tener una lista oficial de selecciones.
Ayuda a normalizar nombres entre distintas fuentes.
Evita errores por nombres escritos diferente.
Permite relacionar equipos con ranking FIFA y Elo ratings.
Permite mostrar escudos en el frontend.
```

Ejemplo de problema que resuelve:

```text
USA
United States
United States of America
Estados Unidos
```

Todos esos nombres pueden referirse al mismo equipo. La API ayuda a crear una tabla de equivalencias.

Tabla sugerida:

```text
api_team_id
api_team_name
api_team_tla
fifa_ranking_name
elo_name
historical_dataset_name
display_name
```

Esto es importante porque un predictor puede fallar si no logra unir correctamente los datos de varias fuentes.

---

## 7. Head-to-head entre selecciones

La API incluye un endpoint de enfrentamientos directos:

```http
GET https://api.football-data.org/v4/matches/{id}/head2head
```

Este endpoint puede devolver partidos previos entre los equipos de un partido específico.

Aporte al predictor:

```text
Permite analizar historial directo entre dos selecciones.
Puede aportar contexto adicional en partidos cerrados.
Puede ayudar a calcular goles promedio entre ambos.
Puede mostrar si históricamente hay muchos empates entre esos equipos.
```

Features sugeridas:

```text
h2h_home_wins
h2h_away_wins
h2h_draws
h2h_home_goals_avg
h2h_away_goals_avg
h2h_total_goals_avg
h2h_last_winner
h2h_matches_count
```

Ejemplo:

```text
Francia vs Alemania

Últimos enfrentamientos:
Francia ganó 3
Alemania ganó 2
Empates 1
Promedio de goles: 2.5
```

Este dato no debe pesar más que forma reciente, Elo o ranking, pero puede sumar contexto.

---

## 8. Partidos por equipo para calcular forma reciente

La API permite consultar partidos de un equipo:

```http
GET https://api.football-data.org/v4/teams/{id}/matches
```

Aporte al predictor:

```text
Permite calcular forma reciente de cada selección.
Permite revisar últimos partidos antes o durante el Mundial.
Permite calcular goles recientes a favor y en contra.
Permite detectar rachas positivas o negativas.
```

Features sugeridas:

```text
home_last_5_wins
home_last_5_draws
home_last_5_losses
home_last_5_goals_for
home_last_5_goals_against
home_last_5_goal_difference

away_last_5_wins
away_last_5_draws
away_last_5_losses
away_last_5_goals_for
away_last_5_goals_against
away_last_5_goal_difference
```

Ejemplo:

```text
Francia últimos 5 partidos:
W - W - D - L - W

Variables:
wins = 3
draws = 1
losses = 1
goals_for = 9
goals_against = 4
goal_difference = +5
```

Esto ayuda a que el predictor no se base solo en reputación histórica, sino también en rendimiento reciente.

---

## 9. Goleadores y rendimiento ofensivo durante el torneo

La API puede incluir endpoint de goleadores por competencia:

```http
GET https://api.football-data.org/v4/competitions/WC/scorers
```

Aporte al predictor:

```text
Permite detectar selecciones con jugadores en buena forma.
Permite medir dependencia ofensiva de un jugador.
Puede aportar contexto para estimar goles esperados.
```

Features sugeridas:

```text
home_has_top_scorer
away_has_top_scorer
home_top_scorer_goals
away_top_scorer_goals
home_total_players_in_top_scorers
away_total_players_in_top_scorers
```

Ejemplo:

```text
Si una selección tiene 2 jugadores entre los máximos goleadores,
puede ser una señal de buen rendimiento ofensivo durante el torneo.
```

Este dato debe usarse con cuidado, porque aparece conforme avanza el torneo, no antes de iniciar.

---

## 10. Información de alineaciones, banca, técnicos, árbitros y formaciones

En algunos partidos, la API puede incluir campos como:

```text
lineup
bench
coach
formation
referees
statistics
```

No siempre estarán disponibles en todos los partidos o planes, pero cuando existan pueden aportar información avanzada.

Aporte al predictor:

```text
Permite analizar si juega un titular importante.
Permite detectar rotaciones.
Permite revisar formación táctica.
Permite considerar al entrenador.
Permite analizar árbitros o tarjetas en análisis posterior.
```

Features posibles:

```text
home_formation
away_formation
home_coach
away_coach
home_lineup_strength
away_lineup_strength
home_key_players_starting
away_key_players_starting
referee_avg_cards
```

Para predicción antes del partido, estos datos solo sirven si están disponibles antes del inicio. Si aparecen después, pueden usarse para análisis post-partido o para entrenar modelos futuros.

---

## 11. Estadísticas de partido para mejorar modelos futuros

En algunos datos de partido pueden aparecer estadísticas como:

```text
posesión
tiros
tiros al arco
corners
faltas
offsides
tarjetas
atajadas
saques de banda
```

Aporte al predictor:

```text
Sirven para análisis posterior.
Sirven para evaluar si un equipo ganó con dominio real o con poca generación.
Sirven para entrenar modelos más avanzados.
Sirven para calcular rendimiento más allá del marcador.
```

Ejemplo:

```text
Un equipo puede ganar 1-0, pero con pocos tiros y poca posesión.
Otro puede empatar 1-1, pero generar muchas oportunidades.
```

Esto ayuda a construir variables más inteligentes para futuros partidos.

Features sugeridas:

```text
shots_for_avg
shots_against_avg
shots_on_goal_for_avg
shots_on_goal_against_avg
possession_avg
corners_avg
cards_avg
```

---

## 12. IDs consistentes para unir fuentes externas

Una de las ventajas más importantes de la API es que usa IDs para entidades como:

```text
partidos
equipos
competencias
temporadas
jugadores/personas
```

Aporte al predictor:

```text
Permite unir datos de distintas fuentes con menos errores.
Ayuda a construir una base de datos limpia.
Facilita relacionar calendario con rankings, Elo y datasets históricos.
Evita duplicados.
Evita problemas por nombres distintos.
```

Fuentes externas que se pueden unir:

```text
football-data.org
FIFA Ranking
Elo Ratings
International football results
StatsBomb Open Data
Kaggle datasets
```

Ejemplo de tabla de unión:

```text
team_master_id
football_data_team_id
football_data_name
fifa_ranking_name
elo_name
results_dataset_name
statsbomb_name
country_code
```

Esto es clave para que el predictor pueda tomar datos de varias fuentes y generar una predicción coherente.

---

## 13. Actualización automática durante el Mundial

La API permite que el sistema se mantenga actualizado automáticamente.

Aporte al predictor:

```text
El calendario cambia sin editar manualmente.
Los resultados se actualizan conforme terminan los partidos.
Las tablas de grupo pueden actualizarse.
Las predicciones pueden recalcularse cuando cambia el contexto.
El sistema puede comparar predicción vs resultado real.
```

Ejemplo de actualización:

```text
Antes del partido:
Mostrar predicción.

Durante el partido:
Mostrar estado actualizado.

Después del partido:
Guardar resultado real.
Calcular error del modelo.
Actualizar standings.
Recalcular predicciones de partidos futuros.
```

Esto vuelve al predictor una aplicación dinámica, no solo un modelo estático.

---

## 14. Cómo ayuda a predecir victoria, empate o derrota

La API no predice directamente, pero aporta variables que ayudan al modelo.

Variables posibles:

```text
stage
group
matchday
status
home_team_id
away_team_id
home_recent_form
away_recent_form
home_goals_for_recent
away_goals_for_recent
home_goals_against_recent
away_goals_against_recent
h2h_home_wins
h2h_away_wins
h2h_draws
group_position_difference
points_difference
goal_difference_difference
```

Salida esperada del modelo:

```text
probabilidad_victoria_home
probabilidad_empate
probabilidad_victoria_away
```

Ejemplo:

```json
{
  "home_team": "France",
  "away_team": "Germany",
  "probabilities": {
    "home_win": 0.43,
    "draw": 0.27,
    "away_win": 0.30
  }
}
```

Interpretación:

```text
El resultado más probable sería victoria de Francia.
Pero si la probabilidad de empate está cerca, el sistema debe indicarlo.
```

---

## 15. Cómo ayuda a estimar el marcador más realista

Para estimar marcador, el modelo necesita más que saber quién gana. Debe estimar goles esperados para cada equipo.

La API puede aportar contexto para calcular o ajustar:

```text
goles recientes a favor
goles recientes en contra
promedio de goles en enfrentamientos directos
fase del torneo
necesidad de ganar
estado del grupo
rendimiento durante el torneo
marcadores reales anteriores
```

Salida esperada:

```json
{
  "predicted_score": {
    "home": 2,
    "away": 1
  },
  "most_likely_result": "HOME_WIN"
}
```

También se pueden generar varios marcadores probables:

```json
{
  "score_probabilities": [
    {
      "score": "1-1",
      "probability": 0.14
    },
    {
      "score": "2-1",
      "probability": 0.12
    },
    {
      "score": "1-0",
      "probability": 0.10
    }
  ]
}
```

Esto es mejor que dar un solo marcador sin contexto. El frontend podría mostrar:

```text
Marcador más probable: 1-1
Otras opciones realistas: 2-1, 1-0, 2-2
```

---

## 16. Variables recomendadas para el modelo usando esta API

Tabla sugerida de variables:

| Variable | Fuente API | Utilidad |
|---|---|---|
| `stage` | Match | Contexto de fase |
| `group` | Match | Contexto de grupo |
| `matchday` | Match | Jornada |
| `home_team_id` | Match/Team | Identificación del equipo |
| `away_team_id` | Match/Team | Identificación del equipo |
| `home_team_name` | Match/Team | Unión con otras fuentes |
| `away_team_name` | Match/Team | Unión con otras fuentes |
| `status` | Match | Saber si se predice o se evalúa |
| `home_recent_wins` | Team matches | Forma reciente |
| `away_recent_wins` | Team matches | Forma reciente |
| `home_recent_goals_for` | Team matches | Ataque reciente |
| `away_recent_goals_for` | Team matches | Ataque reciente |
| `home_recent_goals_against` | Team matches | Defensa reciente |
| `away_recent_goals_against` | Team matches | Defensa reciente |
| `h2h_home_wins` | Head-to-head | Historial directo |
| `h2h_away_wins` | Head-to-head | Historial directo |
| `h2h_draws` | Head-to-head | Tendencia a empate |
| `home_group_points` | Standings | Contexto competitivo |
| `away_group_points` | Standings | Contexto competitivo |
| `home_goal_difference` | Standings | Rendimiento en grupo |
| `away_goal_difference` | Standings | Rendimiento en grupo |
| `home_has_top_scorer` | Scorers | Forma ofensiva |
| `away_has_top_scorer` | Scorers | Forma ofensiva |

---

## 17. Qué datos externos deben complementar esta API

Para que el predictor sea más realista, football-data.org debe combinarse con:

```text
International football results
FIFA Men's World Ranking
World Football Elo Ratings
historial mundialista
resultados recientes de selecciones
StatsBomb Open Data si se quiere análisis avanzado
```

Motivo:

```text
football-data.org mantiene actualizado el torneo.
Los datasets históricos entrenan el modelo.
Ranking FIFA aporta fuerza oficial.
Elo aporta fuerza dinámica.
Resultados históricos aportan patrones de goles.
StatsBomb puede aportar análisis táctico y eventos.
```

La API aporta el contexto actual; los datasets externos aportan profundidad histórica.

---

## 18. Uso recomendado en el predictor

La API debe usarse para:

```text
1. Cargar calendario del Mundial.
2. Mantener partidos actualizados.
3. Guardar resultados reales.
4. Actualizar estados del partido.
5. Actualizar grupos y fases.
6. Obtener equipos oficiales.
7. Calcular forma reciente.
8. Calcular head-to-head si está disponible.
9. Obtener standings durante fase de grupos.
10. Obtener goleadores durante el torneo.
11. Evaluar la precisión del modelo.
12. Recalcular predicciones conforme avanza el torneo.
```

No debe usarse para:

```text
Entrenar todo el modelo por sí sola.
Reemplazar datos históricos.
Reemplazar Elo ratings.
Reemplazar ranking FIFA.
Consumirse directamente desde React exponiendo la API key.
```

---

## 19. Resultado esperado para el usuario final

El usuario final debería ver algo como:

```text
Francia vs Alemania
Fase: Cuartos de final
Fecha: 2026-07-10
Estado: Programado

Predicción:
Francia gana: 43%
Empate: 27%
Alemania gana: 30%

Marcador más realista:
Francia 2 - 1 Alemania

Otros marcadores probables:
1 - 1
1 - 0
2 - 2
```

Después del partido:

```text
Resultado real:
Francia 1 - 1 Alemania

Evaluación del modelo:
Ganador acertado: No
Empate acertado: Sí
Error total de goles: 1
```

Esto ayuda a que el sistema no solo prediga, sino que aprenda y mida qué tan cerca estuvo.

---

## 20. Resumen para Codex

Codex debe entender que `football-data.org` no solo sirve para mostrar el calendario.

También puede aportar datos para mejorar el predictor mediante:

```text
calendario real
estado del partido
resultado real
fase del torneo
grupo
standings
equipos oficiales
forma reciente
head-to-head
goleadores
alineaciones si están disponibles
estadísticas si están disponibles
IDs consistentes
actualización automática
evaluación del modelo
```

La meta principal del predictor es estimar:

```text
probabilidad de victoria del equipo A
probabilidad de empate
probabilidad de victoria del equipo B
marcador más realista
```

La API ayuda a que esas predicciones estén conectadas con el contexto real del Mundial y no sean datos aislados.

---

## Prompt sugerido para Codex

```text
Usa este documento para integrar football-data.org como fuente de datos contextual para el predictor del Mundial.

No la uses solamente como calendario. Aprovecha sus datos para generar variables que ayuden al modelo a estimar victoria, empate, derrota y marcador más realista.

La API debe aportar:
- partidos reales del Mundial
- fechas
- estados
- fases
- grupos
- resultados finales
- standings
- equipos oficiales
- forma reciente por equipo
- head-to-head cuando esté disponible
- goleadores cuando esté disponible
- alineaciones y estadísticas si están disponibles

El predictor debe combinar estos datos con fuentes externas como ranking FIFA, Elo ratings y resultados históricos.

El resultado esperado por partido debe incluir:
- probabilidad de victoria del equipo local
- probabilidad de empate
- probabilidad de victoria del equipo visitante
- marcador más probable
- otros marcadores realistas
- comparación posterior contra el resultado real
```
