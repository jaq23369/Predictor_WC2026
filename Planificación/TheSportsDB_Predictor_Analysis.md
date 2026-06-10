# Evaluación de Integración de TheSportsDB para Predictor Mundial 2026

## Objetivo

Evaluar si la API de TheSportsDB puede aportar variables adicionales que mejoren la precisión de las predicciones de partidos, resultados y simulaciones del Mundial 2026.

Actualmente el predictor ya utiliza o planea utilizar:

- Resultados históricos internacionales
- Elo Ratings
- Ranking FIFA
- Valor de mercado por selección
- Simulaciones Monte Carlo
- Variables de sede y localía

La idea es determinar qué datos dinámicos puede aportar TheSportsDB para complementar estas fuentes.

---

# Principales aportes al predictor

## 1. Calendario automático de partidos

La API permite obtener:

- Próximos partidos
- Partidos anteriores
- Calendarios completos
- Calendarios de selecciones
- Calendarios de ligas

### Endpoints relevantes

### V1

```text
eventsnext.php
eventslast.php
eventsseason.php
```

### V2

```text
schedule/next/team/{id}
schedule/previous/team/{id}
schedule/full/team/{id}
schedule/league/{id}/{season}
```

### Beneficios

- Actualización automática del Mundial.
- Evitar ingreso manual de resultados.
- Actualizar simulaciones conforme avanza el torneo.
- Recalcular probabilidades después de cada jornada.

---

# 2. Forma reciente de las selecciones

La API permite consultar los últimos encuentros disputados por un equipo.

### Endpoint

```text
eventslast.php?id=TEAM_ID
```

### Variables derivables

- Victorias últimos 5 partidos.
- Victorias últimos 10 partidos.
- Empates recientes.
- Derrotas recientes.
- Goles anotados recientes.
- Goles recibidos recientes.
- Diferencia de gol reciente.
- Puntos obtenidos recientemente.

### Potencial impacto

ALTO

---

# 3. Estadísticas de partidos

### Endpoints

```text
lookupeventstats.php?id=EVENT_ID
lookup/event_stats/{id}
```

### Variables potenciales

- Posesión
- Tiros
- Tiros al arco
- Corners
- Faltas
- Tarjetas

### Potencial impacto

MEDIO-ALTO

---

# 4. Alineaciones

### Endpoints

```text
lookuplineup.php?id=EVENT_ID
lookup/event_lineup/{id}
```

### Beneficios

- Detectar ausencias.
- Validar convocatorias.
- Construir variables de continuidad.

### Potencial impacto

MEDIO

---

# 5. Estadísticas de jugadores

### Endpoints

```text
lookupplayerstats.php?id=PLAYER_ID
lookup/player_stats/{id}
```

### Aplicaciones

- Goles acumulados de convocados.
- Asistencias acumuladas.
- Producción ofensiva agregada.

### Potencial impacto

MEDIO

---

# 6. Plantillas completas

### Endpoints

```text
lookup_all_players.php?id=TEAM_ID
list/players/{idTeam}
```

### Posibles usos

- Cruzar con Transfermarkt.
- Calcular valor total de plantilla.
- Calcular edad promedio.
- Calcular profundidad del plantel.

### Potencial impacto

ALTO

---

# 7. Tablas de posiciones

### Endpoint

```text
lookuptable.php?l=LEAGUE_ID
```

### Potencial impacto

MEDIO

---

# 8. Resultados históricos adicionales

### Endpoints

```text
eventsseason.php
eventspastleague.php
```

### Potencial impacto

MEDIO

---

# 9. Livescores (Premium)

### Endpoints

```text
livescore/all
livescore/soccer
livescore/{league}
```

### Potencial impacto

MEDIO

---

# Datos visuales disponibles

- Escudos
- Logos
- Banderas
- Fotos de jugadores
- Estadios
- Highlights

Impacto predictivo: NULO

---

# Limitaciones importantes

La API NO proporciona:

- Elo Ratings
- Ranking FIFA
- Valor de mercado Transfermarkt
- Probabilidades de apuestas
- xG avanzados tipo StatsBomb
- Convocatorias oficiales completas
- Lesiones actualizadas
- Suspensiones actualizadas

---

# Recomendación

TheSportsDB no debería reemplazar Elo, Ranking FIFA o Transfermarkt.

Sin embargo, sí puede convertirse en la principal fuente de datos dinámicos para:

- Calendario del Mundial.
- Resultados actualizados.
- Forma reciente de equipos.
- Estadísticas de partidos.
- Alineaciones.
- Plantillas.
- Automatización de simulaciones.

La integración tendría sentido especialmente para generar variables actualizadas automáticamente conforme avance el Mundial 2026 y reducir la necesidad de mantenimiento manual de datos.
