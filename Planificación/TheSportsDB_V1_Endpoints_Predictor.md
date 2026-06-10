# TheSportsDB V1 - Endpoints Relevantes para el Predictor Mundial 2026

## Base URL

```text
https://www.thesportsdb.com/api/v1/json/123/
```

API Key gratuita:

```text
123
```

---

# Endpoints Prioridad Alta

## 1. Buscar selección por nombre

```http
searchteams.php?t=Argentina
```

### Uso

Permite obtener:

- ID del equipo
- Nombre oficial
- País
- Información básica

### Necesario para

Identificar el TEAM_ID que usarán los demás endpoints.

---

## 2. Información completa de selección

```http
lookupteam.php?id=TEAM_ID
```

### Devuelve

- Nombre
- País
- Liga
- Estadio
- Escudos y logos

### Valor para predictor

Bajo-Medio

---

## 3. Plantilla completa de jugadores

```http
lookup_all_players.php?id=TEAM_ID
```

### Devuelve

Todos los jugadores registrados para la selección.

### Variables posibles

- Edad promedio
- Número de jugadores
- Profundidad de plantilla
- Cruce con Transfermarkt

### Impacto

Alto

---

## 4. Últimos partidos

```http
eventslast.php?id=TEAM_ID
```

### Variables derivables

- Forma últimos 5 partidos
- Forma últimos 10 partidos
- Victorias
- Empates
- Derrotas
- Goles anotados
- Goles recibidos
- Diferencia de gol

### Impacto

Muy Alto

---

## 5. Próximos partidos

```http
eventsnext.php?id=TEAM_ID
```

### Uso

- Calendario automático
- Actualización de simulaciones

### Impacto

Alto

---

## 6. Información completa de un partido

```http
lookupevent.php?id=EVENT_ID
```

### Devuelve

- Equipos
- Fecha
- Resultado
- Liga
- Estadio
- Temporada

### Impacto

Alto

---

## 7. Estadísticas del partido

```http
lookupeventstats.php?id=EVENT_ID
```

### Variables posibles

- Posesión
- Tiros
- Tiros al arco
- Corners
- Faltas
- Tarjetas

### Features sugeridas

- posesion_promedio
- tiros_promedio
- tiros_arco_promedio
- corners_promedio

### Impacto

Muy Alto

---

## 8. Alineaciones

```http
lookuplineup.php?id=EVENT_ID
```

### Devuelve

- Titulares
- Suplentes

### Uso

- Detectar ausencias
- Analizar continuidad del once titular

### Impacto

Medio-Alto

---

## 9. Timeline del partido

```http
lookuptimeline.php?id=EVENT_ID
```

### Devuelve

- Goles
- Cambios
- Tarjetas
- Eventos cronológicos

### Impacto

Medio

---

# Calendarios y Torneos

## 10. Calendario completo de temporada

```http
eventsseason.php?id=LEAGUE_ID&s=2025-2026
```

### Uso

- Mundial 2026
- Eliminatorias
- Nations League
- Copa América

### Impacto

Muy Alto

---

## 11. Eventos por fecha

```http
eventsday.php?d=2026-06-15
```

### Uso

Obtener todos los partidos de una fecha específica.

### Impacto

Alto

---

## 12. Próximos partidos de una competición

```http
eventsnextleague.php?id=LEAGUE_ID
```

### Impacto

Medio

---

## 13. Partidos recientes de una competición

```http
eventspastleague.php?id=LEAGUE_ID
```

### Impacto

Medio

---

# Jugadores

## Información de jugador

```http
lookupplayer.php?id=PLAYER_ID
```

### Devuelve

- Edad
- Altura
- Peso
- Posición

---

## Estadísticas de jugador

```http
lookupplayerstats.php?id=PLAYER_ID
```

### Uso

Construcción de métricas agregadas por selección.

---

# Ligas y Tablas

## Tabla de posiciones

```http
lookuptable.php?l=4328&s=2025-2026
```

### Devuelve

- Posición
- Puntos
- Diferencia de gol

---

## Todas las ligas

```http
all_leagues.php
```

---

## Todas las temporadas

```http
search_all_seasons.php?id=4328
```

---

# Endpoints que NO aportan valor significativo al predictor

```http
lookuptv.php
eventstv.php
eventshighlights.php
lookupequipment.php
lookuphonours.php
lookupmilestones.php
lookupcontracts.php
lookupformerteams.php
```

Estos endpoints son útiles para:

- Frontend
- Visualización
- Historiales
- Videos
- Información adicional

Pero no mejoran significativamente las predicciones.

---

# Recomendación para Integración Inicial

Implementar primero:

```text
searchteams.php
lookupteam.php
lookup_all_players.php
eventslast.php
eventsnext.php
eventsseason.php
lookupeventstats.php
lookuplineup.php
```

Con estos 8 endpoints se pueden generar la mayoría de variables útiles para el predictor:

- forma_5
- forma_10
- goles_favor_recientes
- goles_contra_recientes
- diferencia_gol_reciente
- posesion_promedio
- tiros_promedio
- tiros_arco_promedio
- corners_promedio
- edad_promedio_plantilla
- profundidad_plantilla
