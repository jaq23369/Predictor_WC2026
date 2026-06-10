import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  BarChart3,
  CalendarDays,
  CircleAlert,
  Flag,
  Goal,
  ListChecks,
  RefreshCw,
  Search,
  ShieldCheck,
  Trophy,
  Users,
} from "lucide-react";
import {
  getAPIFootballTeamMatchStats,
  getFootballDataTeams,
  getSquads,
  getSquadSummary,
  getTeams,
  getTheSportsDBRecentForm,
  getTheSportsDBRecentMatchStats,
  getTransfermarktValues,
  getWorldCupFixtures,
  getWorldCupPredictions,
  getSimulation,
  predictMatch,
} from "./api";
import "./styles.css";

const DEFAULT_REQUEST = {
  team_a: "Mexico",
  team_b: "South Africa",
  match_date: "2026-06-11",
  neutral: false,
  team_a_is_home: true,
};

const GROUP_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("");

const TEAM_NAME_ALIASES = {
  "Bosnia-Herzegovina": "Bosnia and Herzegovina",
  "Cape Verde Islands": "Cape Verde",
  "Cabo Verde": "Cape Verde",
  "Congo DR": "DR Congo",
  "Democratic Republic of Congo": "DR Congo",
  "Democratic Republic of the Congo": "DR Congo",
  "IR Iran": "Iran",
  "Islamic Republic of Iran": "Iran",
  "Ivory Coast": "Côte d'Ivoire",
  "Cote d'Ivoire": "Côte d'Ivoire",
  "Korea Republic": "South Korea",
  "Republic of Korea": "South Korea",
  "Turkiye": "Turkey",
  "Türkiye": "Turkey",
  "United States of America": "United States",
  USA: "United States",
};

const POSITION_ORDER = ["Goalkeepers", "Defenders", "Midfielders", "Forwards"];
const LINEUP_SHAPE = {
  Goalkeepers: 1,
  Defenders: 4,
  Midfielders: 3,
  Forwards: 3,
};

function canonicalTeamName(value) {
  const name = String(value || "").replace(/\s+/g, " ").trim();
  return TEAM_NAME_ALIASES[name] || name;
}

function formatPercent(value) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? `${numeric.toFixed(1)}%` : "0.0%";
}

function formatMoney(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric) || numeric <= 0) return "Sin dato";
  if (numeric >= 1_000_000_000) return `€${(numeric / 1_000_000_000).toFixed(2)}B`;
  if (numeric >= 1_000_000) return `€${(numeric / 1_000_000).toFixed(1)}M`;
  return `€${Math.round(numeric / 1_000)}K`;
}

function formatNumber(value, decimals = 1) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric) || numeric <= 0) return "Sin dato";
  return numeric.toFixed(decimals);
}

function metricValue(row, primaryKey, fallbackKey) {
  if (!row) return undefined;
  return row[primaryKey] ?? row[fallbackKey];
}

function formatDate(value) {
  if (!value) return "Sin fecha";
  return new Intl.DateTimeFormat("es-GT", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(`${value}T12:00:00`));
}

function inferGroups(fixtures) {
  const adjacency = new Map();

  fixtures.forEach((fixture) => {
    if (!adjacency.has(fixture.home_team)) adjacency.set(fixture.home_team, new Set());
    if (!adjacency.has(fixture.away_team)) adjacency.set(fixture.away_team, new Set());
    adjacency.get(fixture.home_team).add(fixture.away_team);
    adjacency.get(fixture.away_team).add(fixture.home_team);
  });

  const seen = new Set();
  const components = [];

  fixtures.forEach((fixture) => {
    [fixture.home_team, fixture.away_team].forEach((team) => {
      if (seen.has(team)) return;

      const stack = [team];
      const teams = [];
      seen.add(team);

      while (stack.length) {
        const current = stack.pop();
        teams.push(current);
        adjacency.get(current)?.forEach((next) => {
          if (!seen.has(next)) {
            seen.add(next);
            stack.push(next);
          }
        });
      }

      components.push(teams.sort((a, b) => a.localeCompare(b)));
    });
  });

  const teamToGroup = new Map();
  const groups = components.map((teams, index) => {
    const label = `Grupo ${GROUP_LETTERS[index]}`;
    teams.forEach((team) => teamToGroup.set(team, label));
    return { label, teams };
  });

  return { groups, teamToGroup };
}

function pickFixtureMeta(fixtures, teamA, teamB) {
  return fixtures.find((fixture) => fixture.home_team === teamA && fixture.away_team === teamB);
}

function StatPill({ icon: Icon, label, value }) {
  return (
    <div className="stat-pill">
      <Icon size={16} aria-hidden="true" />
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function ProbabilityBar({ label, value, tone }) {
  return (
    <div className="probability-row">
      <div className="probability-heading">
        <span>{label}</span>
        <strong>{formatPercent(value)}</strong>
      </div>
      <div className="track" aria-hidden="true">
        <div className={`fill ${tone}`} style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
      </div>
    </div>
  );
}

function TeamCrest({ src, name }) {
  if (!src) {
    return (
      <div className="crest-fallback" aria-hidden="true">
        {name?.slice(0, 2).toUpperCase()}
      </div>
    );
  }

  return <img className="team-crest" src={src} alt="" loading="lazy" />;
}

function playerValue(player) {
  const value = Number(player.market_value_in_eur);
  return Number.isFinite(value) ? value : 0;
}

function likelyLineup(players) {
  const selected = [];
  const used = new Set();

  POSITION_ORDER.forEach((position) => {
    const candidates = players
      .filter((player) => player.position_group === position)
      .sort((a, b) => playerValue(b) - playerValue(a) || Number(a.player_order_in_position || 0) - Number(b.player_order_in_position || 0));
    candidates.slice(0, LINEUP_SHAPE[position]).forEach((player) => {
      selected.push(player);
      used.add(`${player.player}-${player.position_group}-${player.player_order_in_position}`);
    });
  });

  if (selected.length < 11) {
    players
      .filter((player) => !used.has(`${player.player}-${player.position_group}-${player.player_order_in_position}`))
      .sort((a, b) => playerValue(b) - playerValue(a))
      .slice(0, 11 - selected.length)
      .forEach((player) => selected.push(player));
  }

  return POSITION_ORDER.map((position) => ({
    position,
    players: selected.filter((player) => player.position_group === position),
  })).filter((line) => line.players.length > 0);
}

function TeamProbabilityCard({ team, crest, probability, tone }) {
  return (
    <article className={`team-probability-card ${tone}`}>
      <TeamCrest src={crest} name={team} />
      <div>
        <span>{team}</span>
        <strong>{formatPercent(probability)}</strong>
      </div>
    </article>
  );
}

function LineupPitch({ team, crest, lines, tone }) {
  const totalPlayers = lines.reduce((sum, line) => sum + line.players.length, 0);

  return (
    <article className={`lineup-card ${tone}`}>
      <div className="lineup-header">
        <TeamCrest src={crest} name={team} />
        <div>
          <span>Alineación posible</span>
          <strong>{team}</strong>
        </div>
      </div>

      {totalPlayers > 0 ? (
        <div className="pitch-lines">
          {lines.map((line) => (
            <div className="pitch-line" key={`${team}-${line.position}`}>
              {line.players.map((player) => (
                <div className="player-bubble" key={`${team}-${player.player}-${player.position_group}`}>
                  <span>{player.player.split(" ").map((part) => part[0]).join("").slice(0, 2).toUpperCase()}</span>
                  <strong>{player.player}</strong>
                </div>
              ))}
            </div>
          ))}
        </div>
      ) : (
        <div className="empty-lineup">Sin convocatoria suficiente para armar once probable.</div>
      )}
    </article>
  );
}

function App() {
  const [activeView, setActiveView] = useState("predict");
  const [teams, setTeams] = useState([]);
  const [fixtures, setFixtures] = useState([]);
  const [fixturePredictions, setFixturePredictions] = useState([]);
  const [transfermarktValues, setTransfermarktValues] = useState([]);
  const [footballDataTeams, setFootballDataTeams] = useState([]);
  const [squads, setSquads] = useState([]);
  const [squadSummary, setSquadSummary] = useState([]);
  const [theSportsDBRecentForm, setTheSportsDBRecentForm] = useState([]);
  const [theSportsDBRecentStats, setTheSportsDBRecentStats] = useState([]);
  const [apiFootballTeamStats, setAPIFootballTeamStats] = useState([]);
  const [simulation, setSimulation] = useState(null);
  const [selectedAnalysisTeam, setSelectedAnalysisTeam] = useState("");
  const [form, setForm] = useState(DEFAULT_REQUEST);
  const [prediction, setPrediction] = useState(null);
  const [loading, setLoading] = useState(true);
  const [predicting, setPredicting] = useState(false);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");

  useEffect(() => {
    let active = true;

    async function loadInitialData() {
      try {
        const [
          teamsResponse,
          fixturesResponse,
          predictionsResponse,
          transfermarktResponse,
          footballDataTeamsResponse,
          squadsResponse,
          squadSummaryResponse,
          theSportsDBRecentFormResponse,
          theSportsDBRecentStatsResponse,
          apiFootballTeamStatsResponse,
          simulationResponse,
        ] = await Promise.all([
          getTeams(),
          getWorldCupFixtures(),
          getWorldCupPredictions(),
          getTransfermarktValues(),
          getFootballDataTeams(),
          getSquads(),
          getSquadSummary(),
          getTheSportsDBRecentForm(),
          getTheSportsDBRecentMatchStats(),
          getAPIFootballTeamMatchStats(),
          getSimulation(),
        ]);

        if (!active) return;

        setTeams(teamsResponse.teams);
        setFixtures(fixturesResponse);
        setFixturePredictions(predictionsResponse);
        setTransfermarktValues(transfermarktResponse);
        setFootballDataTeams(footballDataTeamsResponse);
        setSquads(squadsResponse);
        setSquadSummary(squadSummaryResponse);
        setTheSportsDBRecentForm(theSportsDBRecentFormResponse);
        setTheSportsDBRecentStats(theSportsDBRecentStatsResponse);
        setAPIFootballTeamStats(apiFootballTeamStatsResponse);
        setSimulation(simulationResponse);
        setSelectedAnalysisTeam(squadSummaryResponse[0]?.team || "Mexico");
      } catch (requestError) {
        if (active) setError(requestError.message);
      } finally {
        if (active) setLoading(false);
      }
    }

    loadInitialData();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    handlePredict(DEFAULT_REQUEST);
  }, []);

  async function handlePredict(payload = form) {
    setPredicting(true);
    setError("");
    try {
      const result = await predictMatch(payload);
      setPrediction(result);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setPredicting(false);
    }
  }

  function handleSubmit(event) {
    event.preventDefault();
    handlePredict(form);
  }

  function selectFixture(fixture) {
    const payload = {
      team_a: fixture.home_team,
      team_b: fixture.away_team,
      match_date: fixture.date,
      neutral: fixture.neutral === "1",
      team_a_is_home: fixture.neutral !== "1",
    };
    setForm(payload);
    setActiveView("predict");
    handlePredict(payload);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  const filteredPredictions = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return fixturePredictions;
    return fixturePredictions.filter((row) =>
      `${row.home_team} ${row.away_team} ${row.predicted_winner} ${row.city}`
        .toLowerCase()
        .includes(term)
    );
  }, [fixturePredictions, search]);

  const groupData = useMemo(() => inferGroups(fixtures), [fixtures]);

  const groupedPredictions = useMemo(() => {
    const grouped = new Map(groupData.groups.map((group) => [group.label, { ...group, matches: [] }]));

    filteredPredictions.forEach((row) => {
      const groupLabel = groupData.teamToGroup.get(row.home_team) || "Sin grupo";
      if (!grouped.has(groupLabel)) {
        grouped.set(groupLabel, { label: groupLabel, teams: [], matches: [] });
      }
      grouped.get(groupLabel).matches.push(row);
    });

    return Array.from(grouped.values())
      .filter((group) => group.matches.length > 0)
      .map((group) => ({
        ...group,
        matches: group.matches.sort((a, b) => `${a.date}-${a.home_team}`.localeCompare(`${b.date}-${b.home_team}`)),
      }));
  }, [filteredPredictions, groupData]);

  const groupSummary = useMemo(() => {
    const matches = fixturePredictions.length || 1;
    const avgDraw = fixturePredictions.reduce((sum, row) => sum + Number(row.draw_probability), 0) / matches;
    const favorites = fixturePredictions.filter((row) => {
      const home = Number(row.home_win_probability);
      const away = Number(row.away_win_probability);
      return Math.max(home, away) >= 60;
    }).length;
    const closeMatches = fixturePredictions.filter((row) => {
      const home = Number(row.home_win_probability);
      const away = Number(row.away_win_probability);
      return Math.abs(home - away) <= 8;
    }).length;

    return { avgDraw, favorites, closeMatches };
  }, [fixturePredictions]);

  const marketByTeam = useMemo(() => {
    const map = new Map();
    transfermarktValues.forEach((row) => map.set(canonicalTeamName(row.team), row));
    return map;
  }, [transfermarktValues]);

  const crestByTeam = useMemo(() => {
    const map = new Map();
    footballDataTeams.forEach((row) => map.set(canonicalTeamName(row.name), row.crest));
    return map;
  }, [footballDataTeams]);

  const squadSummaryByTeam = useMemo(() => {
    const map = new Map();
    squadSummary.forEach((row) => map.set(canonicalTeamName(row.team), row));
    return map;
  }, [squadSummary]);

  const squadsByTeam = useMemo(() => {
    const map = new Map();
    squads.forEach((row) => {
      const team = canonicalTeamName(row.team);
      if (!map.has(team)) map.set(team, []);
      map.get(team).push(row);
    });
    return map;
  }, [squads]);

  const recentFormByTeam = useMemo(() => {
    const map = new Map();
    theSportsDBRecentForm.forEach((row) => map.set(canonicalTeamName(row.team), row));
    return map;
  }, [theSportsDBRecentForm]);

  const recentStatsByTeam = useMemo(() => {
    const map = new Map();
    theSportsDBRecentStats.forEach((row) => map.set(canonicalTeamName(row.team), row));
    return map;
  }, [theSportsDBRecentStats]);

  const apiFootballStatsByTeam = useMemo(() => {
    const map = new Map();
    apiFootballTeamStats.forEach((row) => map.set(canonicalTeamName(row.team), row));
    return map;
  }, [apiFootballTeamStats]);

  const analysisTeams = useMemo(
    () =>
      [...squadSummary]
        .sort((a, b) => `${a.group}-${a.team}`.localeCompare(`${b.group}-${b.team}`))
        .map((row) => row.team),
    [squadSummary]
  );

  const selectedSummary = squadSummaryByTeam.get(canonicalTeamName(selectedAnalysisTeam));
  const selectedPlayers = useMemo(
    () =>
      squads
        .filter((row) => canonicalTeamName(row.team) === canonicalTeamName(selectedAnalysisTeam))
        .sort((a, b) => {
          const positionDiff =
            POSITION_ORDER.indexOf(a.position_group) - POSITION_ORDER.indexOf(b.position_group);
          if (positionDiff !== 0) return positionDiff;
          return Number(a.player_order_in_position || 0) - Number(b.player_order_in_position || 0);
        }),
    [squads, selectedAnalysisTeam]
  );

  const playersByPosition = useMemo(() => {
    const grouped = new Map(POSITION_ORDER.map((position) => [position, []]));
    selectedPlayers.forEach((player) => {
      if (!grouped.has(player.position_group)) grouped.set(player.position_group, []);
      grouped.get(player.position_group).push(player);
    });
    return Array.from(grouped.entries()).filter(([, players]) => players.length > 0);
  }, [selectedPlayers]);

  const selectedTeamFixtures = useMemo(
    () =>
      fixturePredictions
        .filter(
          (row) =>
            canonicalTeamName(row.home_team) === canonicalTeamName(selectedAnalysisTeam) ||
            canonicalTeamName(row.away_team) === canonicalTeamName(selectedAnalysisTeam)
        )
        .sort((a, b) => `${a.date}-${a.home_team}`.localeCompare(`${b.date}-${b.home_team}`)),
    [fixturePredictions, selectedAnalysisTeam]
  );

  const fixtureMeta = prediction ? pickFixtureMeta(fixtures, prediction.team_a, prediction.team_b) : null;
  const marketA = prediction ? marketByTeam.get(canonicalTeamName(prediction.team_a)) : null;
  const marketB = prediction ? marketByTeam.get(canonicalTeamName(prediction.team_b)) : null;
  const crestA = prediction ? crestByTeam.get(canonicalTeamName(prediction.team_a)) : "";
  const crestB = prediction ? crestByTeam.get(canonicalTeamName(prediction.team_b)) : "";
  const lineupA = prediction ? likelyLineup(squadsByTeam.get(canonicalTeamName(prediction.team_a)) || []) : [];
  const lineupB = prediction ? likelyLineup(squadsByTeam.get(canonicalTeamName(prediction.team_b)) || []) : [];
  const recentFormA = prediction ? recentFormByTeam.get(canonicalTeamName(prediction.team_a)) : null;
  const recentFormB = prediction ? recentFormByTeam.get(canonicalTeamName(prediction.team_b)) : null;
  const recentStatsA = prediction
    ? apiFootballStatsByTeam.get(canonicalTeamName(prediction.team_a)) || recentStatsByTeam.get(canonicalTeamName(prediction.team_a))
    : null;
  const recentStatsB = prediction
    ? apiFootballStatsByTeam.get(canonicalTeamName(prediction.team_b)) || recentStatsByTeam.get(canonicalTeamName(prediction.team_b))
    : null;
  const selectedMarket = marketByTeam.get(canonicalTeamName(selectedAnalysisTeam));
  const selectedCrest = crestByTeam.get(canonicalTeamName(selectedAnalysisTeam));

  return (
    <main className="app-shell">
      <section className="top-panel">
        <div className="brand-block">
          <div className="brand-mark" aria-hidden="true">
            <Trophy size={26} />
          </div>
          <div>
            <p className="eyebrow">Mundial 2026</p>
            <h1>Predicciones claras para comparar partidos</h1>
          </div>
        </div>
        <div className="system-state">
          <ShieldCheck size={18} aria-hidden="true" />
          <span>Modelos conectados a FastAPI</span>
        </div>
      </section>

      <nav className="top-nav" aria-label="Vistas principales">
        <button className={activeView === "predict" ? "nav-button active" : "nav-button"} type="button" onClick={() => setActiveView("predict")}>
          <Activity size={17} />
          Predecir
        </button>
        <button className={activeView === "simulation" ? "nav-button active" : "nav-button"} type="button" onClick={() => setActiveView("simulation")}>
          <ListChecks size={17} />
          Simulación
        </button>
        <button className={activeView === "analysis" ? "nav-button active" : "nav-button"} type="button" onClick={() => setActiveView("analysis")}>
          <Users size={17} />
          Análisis
        </button>
      </nav>

      {error && (
        <div className="notice" role="alert">
          <CircleAlert size={18} />
          <span>{error}</span>
        </div>
      )}

      {activeView === "predict" && (
        <>
          <section className="dashboard-grid">
            <form className="predictor-panel" onSubmit={handleSubmit}>
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Predictor</p>
                  <h2>Partido individual</h2>
                </div>
                <button className="icon-button" type="button" onClick={() => handlePredict()} aria-label="Actualizar predicción">
                  <RefreshCw size={18} />
                </button>
              </div>

              <div className="field-grid">
                <label>
                  Equipo A
                  <select value={form.team_a} onChange={(event) => setForm({ ...form, team_a: event.target.value })}>
                    {teams.map((team) => (
                      <option key={team} value={team}>{team}</option>
                    ))}
                  </select>
                </label>

                <label>
                  Equipo B
                  <select value={form.team_b} onChange={(event) => setForm({ ...form, team_b: event.target.value })}>
                    {teams.map((team) => (
                      <option key={team} value={team}>{team}</option>
                    ))}
                  </select>
                </label>

                <label>
                  Fecha
                  <input type="date" value={form.match_date || ""} onChange={(event) => setForm({ ...form, match_date: event.target.value })} />
                </label>

                <div className="toggle-row">
                  <label className="checkbox-line">
                    <input type="checkbox" checked={form.neutral} onChange={(event) => setForm({ ...form, neutral: event.target.checked })} />
                    Sede neutral
                  </label>
                  <label className="checkbox-line">
                    <input type="checkbox" checked={form.team_a_is_home} onChange={(event) => setForm({ ...form, team_a_is_home: event.target.checked })} />
                    Equipo A local
                  </label>
                </div>
              </div>

              <button className="primary-action" type="submit" disabled={predicting || loading}>
                <Activity size={18} />
                {predicting ? "Calculando" : "Calcular predicción"}
              </button>
            </form>

            <section className="result-panel">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Resultado más probable</p>
                  <h2>{prediction ? prediction.winner : "Cargando"}</h2>
                </div>
                <Goal size={24} aria-hidden="true" />
              </div>

              {prediction && (
                <>
                  <div className="match-title">
                    <strong>{prediction.team_a}</strong>
                    <span>vs</span>
                    <strong>{prediction.team_b}</strong>
                  </div>

                  <div className="probability-stack">
                    <ProbabilityBar label={`${prediction.team_a} gana`} value={prediction.probabilities.team_a_win} tone="home" />
                    <ProbabilityBar label="Empate" value={prediction.probabilities.draw} tone="draw" />
                    <ProbabilityBar label={`${prediction.team_b} gana`} value={prediction.probabilities.team_b_win} tone="away" />
                  </div>

                  <div className="stat-row">
                    <StatPill icon={Goal} label={`xG ${prediction.team_a}`} value={prediction.expected_goals.team_a} />
                    <StatPill icon={Goal} label={`xG ${prediction.team_b}`} value={prediction.expected_goals.team_b} />
                    <StatPill icon={CalendarDays} label="Fecha" value={prediction.match_date} />
                  </div>

                  <div className="market-comparison">
                    <div className="market-card">
                      <span>{prediction.team_a}</span>
                      <strong>{formatMoney(marketA?.total_market_value)}</strong>
                      <small>Edad media {marketA?.average_age || "s/d"} · ranking TM {marketA?.fifa_ranking_transfermarkt || "s/d"}</small>
                    </div>
                    <div className="market-card">
                      <span>{prediction.team_b}</span>
                      <strong>{formatMoney(marketB?.total_market_value)}</strong>
                      <small>Edad media {marketB?.average_age || "s/d"} · ranking TM {marketB?.fifa_ranking_transfermarkt || "s/d"}</small>
                    </div>
                  </div>

                  {fixtureMeta && (
                    <p className="context-line">
                      {fixtureMeta.city}, {fixtureMeta.country} · {fixtureMeta.neutral === "1" ? "sede neutral" : "localía registrada"}
                    </p>
                  )}
                </>
              )}
            </section>
          </section>

          {prediction && (
            <section className="match-detail-section">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Detalle del partido</p>
                  <h2>Probabilidades, contexto y onces posibles</h2>
                </div>
                <Flag size={22} aria-hidden="true" />
              </div>

              <div className="match-probability-board">
                <TeamProbabilityCard
                  team={prediction.team_a}
                  crest={crestA}
                  probability={prediction.probabilities.team_a_win}
                  tone="home"
                />
                <article className="draw-probability-card">
                  <span>Empate</span>
                  <strong>{formatPercent(prediction.probabilities.draw)}</strong>
                </article>
                <TeamProbabilityCard
                  team={prediction.team_b}
                  crest={crestB}
                  probability={prediction.probabilities.team_b_win}
                  tone="away"
                />
              </div>

              <div className="match-metrics-grid">
                <article className="metric-comparison-card">
                  <span>Goles esperados</span>
                  <div>
                    <strong>{prediction.expected_goals.team_a}</strong>
                    <small>{prediction.team_a}</small>
                  </div>
                  <div>
                    <strong>{prediction.expected_goals.team_b}</strong>
                    <small>{prediction.team_b}</small>
                  </div>
                </article>
                <article className="metric-comparison-card">
                  <span>Goles recientes</span>
                  <div>
                    <strong>{formatNumber(recentFormA?.avg_goals_for_last_available)}</strong>
                    <small>{prediction.team_a}</small>
                  </div>
                  <div>
                    <strong>{formatNumber(recentFormB?.avg_goals_for_last_available)}</strong>
                    <small>{prediction.team_b}</small>
                  </div>
                </article>
                <article className="metric-comparison-card">
                  <span>Corners promedio</span>
                  <div>
                    <strong>{formatNumber(metricValue(recentStatsA, "avg_corners", "avg_corners_last_available"))}</strong>
                    <small>{prediction.team_a}</small>
                  </div>
                  <div>
                    <strong>{formatNumber(metricValue(recentStatsB, "avg_corners", "avg_corners_last_available"))}</strong>
                    <small>{prediction.team_b}</small>
                  </div>
                </article>
                <article className="metric-comparison-card">
                  <span>Tiros al arco</span>
                  <div>
                    <strong>{formatNumber(metricValue(recentStatsA, "avg_shots_on_goal", "avg_shots_on_target_last_available"))}</strong>
                    <small>{prediction.team_a}</small>
                  </div>
                  <div>
                    <strong>{formatNumber(metricValue(recentStatsB, "avg_shots_on_goal", "avg_shots_on_target_last_available"))}</strong>
                    <small>{prediction.team_b}</small>
                  </div>
                </article>
                <article className="metric-comparison-card">
                  <span>Posesión promedio</span>
                  <div>
                    <strong>{formatNumber(metricValue(recentStatsA, "avg_possession", "avg_possession_last_available"))}</strong>
                    <small>{prediction.team_a}</small>
                  </div>
                  <div>
                    <strong>{formatNumber(metricValue(recentStatsB, "avg_possession", "avg_possession_last_available"))}</strong>
                    <small>{prediction.team_b}</small>
                  </div>
                </article>
                <article className="metric-comparison-card">
                  <span>Tarjetas amarillas</span>
                  <div>
                    <strong>{formatNumber(metricValue(recentStatsA, "avg_yellow_cards", "avg_yellow_cards_last_available"))}</strong>
                    <small>{prediction.team_a}</small>
                  </div>
                  <div>
                    <strong>{formatNumber(metricValue(recentStatsB, "avg_yellow_cards", "avg_yellow_cards_last_available"))}</strong>
                    <small>{prediction.team_b}</small>
                  </div>
                </article>
                <article className="metric-comparison-card">
                  <span>Tarjetas rojas</span>
                  <div>
                    <strong>{formatNumber(metricValue(recentStatsA, "avg_red_cards", "avg_red_cards_last_available"))}</strong>
                    <small>{prediction.team_a}</small>
                  </div>
                  <div>
                    <strong>{formatNumber(metricValue(recentStatsB, "avg_red_cards", "avg_red_cards_last_available"))}</strong>
                    <small>{prediction.team_b}</small>
                  </div>
                </article>
                <article className="metric-comparison-card">
                  <span>Faltas promedio</span>
                  <div>
                    <strong>{formatNumber(metricValue(recentStatsA, "avg_fouls", "avg_fouls_last_available"))}</strong>
                    <small>{prediction.team_a}</small>
                  </div>
                  <div>
                    <strong>{formatNumber(metricValue(recentStatsB, "avg_fouls", "avg_fouls_last_available"))}</strong>
                    <small>{prediction.team_b}</small>
                  </div>
                </article>
              </div>

              <div className="lineups-grid">
                <LineupPitch team={prediction.team_a} crest={crestA} lines={lineupA} tone="home" />
                <LineupPitch team={prediction.team_b} crest={crestB} lines={lineupB} tone="away" />
              </div>

              <p className="context-line">
                Las alineaciones son una proyección visual desde convocatorias disponibles. Corners, tarjetas, faltas, tiros y posesión usan estadísticas históricas disponibles de API-Football 2024 cuando existen.
              </p>
            </section>
          )}

          <section className="scorelines-section">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Marcadores</p>
                <h2>Escenarios más probables</h2>
              </div>
              <BarChart3 size={22} aria-hidden="true" />
            </div>
            <div className="scoreline-grid">
              {(prediction?.top_scorelines || []).slice(0, 8).map((row) => (
                <article className="scoreline-card" key={row.score}>
                  <strong>{row.score}</strong>
                  <span>{formatPercent(row.probability)}</span>
                </article>
              ))}
            </div>
          </section>

          <section className="fixtures-section">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Fase de grupos</p>
                <h2>Predicciones disponibles</h2>
              </div>
              <label className="search-box">
                <Search size={17} aria-hidden="true" />
                <input type="search" placeholder="Buscar equipo, ciudad o ganador" value={search} onChange={(event) => setSearch(event.target.value)} />
              </label>
            </div>

            <div className="grouped-fixtures">
              {groupedPredictions.map((group) => (
                <article className="group-card" key={group.label}>
                  <div className="group-card-header">
                    <div>
                      <h3>{group.label}</h3>
                      <p>{group.teams.join(" · ")}</p>
                    </div>
                    <span>{group.matches.length} partidos</span>
                  </div>

                  <div className="group-match-list">
                    {group.matches.map((row) => (
                      <button
                        className="group-match-row"
                        type="button"
                        key={`${row.date}-${row.home_team}-${row.away_team}`}
                        onClick={() => {
                          const fixture = fixtures.find((item) => item.date === row.date && item.home_team === row.home_team && item.away_team === row.away_team);
                          if (fixture) selectFixture(fixture);
                        }}
                      >
                        <div className="group-match-date">
                          <strong>{row.date.slice(5)}</strong>
                          <span>{row.city}</span>
                        </div>
                        <div className="group-match-teams">
                          <strong>{row.home_team}</strong>
                          <span>vs</span>
                          <strong>{row.away_team}</strong>
                        </div>
                        <div className="group-match-probs">
                          <span title={`${row.home_team} gana`}>{formatPercent(Number(row.home_win_probability))}</span>
                          <span title="Empate">{formatPercent(Number(row.draw_probability))}</span>
                          <span title={`${row.away_team} gana`}>{formatPercent(Number(row.away_win_probability))}</span>
                        </div>
                        <div className="group-match-pick">
                          <strong>{row.predicted_winner}</strong>
                          <span>{row.most_likely_score}</span>
                        </div>
                      </button>
                    ))}
                  </div>
                </article>
              ))}
            </div>
          </section>
        </>
      )}

      {activeView === "simulation" && (
        <section className="simulation-section">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Simulación</p>
              <h2>Camino estimado al campeón</h2>
            </div>
            <Trophy size={24} aria-hidden="true" />
          </div>

          <div className="simulation-hero">
            <div>
              <span>Campeón proyectado</span>
              <strong>{simulation?.projected_champion || "Calculando"}</strong>
              <p>El bracket usa las probabilidades actuales del modelo para avanzar selecciones desde grupos y cruces.</p>
            </div>
            <div className="phase-metrics">
              <StatPill icon={CalendarDays} label="Partidos grupo" value={fixturePredictions.length} />
              <StatPill icon={Trophy} label="Favoritos 60%+" value={groupSummary.favorites} />
              <StatPill icon={Activity} label="Partidos parejos" value={groupSummary.closeMatches} />
              <StatPill icon={BarChart3} label="Empate medio" value={formatPercent(groupSummary.avgDraw)} />
            </div>
          </div>

          <div className="simulation-grid">
            {(simulation?.groups || []).map((group) => (
              <article className="standings-card" key={group.group}>
                <h3>{group.group}</h3>
                <div className="standings-table">
                  {group.standings.map((row) => (
                    <div className={row.position <= 2 ? "standing-row qualifies" : row.position === 3 ? "standing-row third" : "standing-row"} key={`${group.group}-${row.team}`}>
                      <span>{row.position}</span>
                      <strong>{row.team}</strong>
                      <span>{Number(row.expected_points).toFixed(2)} pts</span>
                      <span>DG {Number(row.expected_goal_difference).toFixed(2)}</span>
                    </div>
                  ))}
                </div>
              </article>
            ))}
          </div>

          <div className="bracket-section">
            {(simulation?.bracket || []).map((round) => (
              <section className="round-column" key={round.round}>
                <h3>{round.round}</h3>
                {round.matches.map((match) => (
                  <article className="bracket-match" key={`${round.round}-${match.team_a}-${match.team_b}`}>
                    <div>
                      <strong>{match.team_a}</strong>
                      <span>{formatPercent(match.team_a_win)}</span>
                    </div>
                    <div>
                      <strong>{match.team_b}</strong>
                      <span>{formatPercent(match.team_b_win)}</span>
                    </div>
                    <p>Avanza: <strong>{match.winner}</strong> · marcador {match.top_score}</p>
                  </article>
                ))}
              </section>
            ))}
          </div>
        </section>
      )}

      {activeView === "analysis" && (
        <section className="analysis-section">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Análisis</p>
              <h2>Convocatorias, valor y partidos por selección</h2>
            </div>
            <label className="team-picker">
              Selección
              <select value={selectedAnalysisTeam} onChange={(event) => setSelectedAnalysisTeam(event.target.value)}>
                {analysisTeams.map((team) => (
                  <option key={team} value={team}>{team}</option>
                ))}
              </select>
            </label>
          </div>

          <div className="team-overview">
            <div className="team-identity">
              <TeamCrest src={selectedCrest} name={selectedAnalysisTeam} />
              <div>
                <p className="eyebrow">Grupo {selectedSummary?.group || "s/d"}</p>
                <h2>{selectedAnalysisTeam || "Selecciona una selección"}</h2>
                <span>{selectedSummary?.matched_players || 0} de {selectedSummary?.players_count || 0} jugadores enlazados con Transfermarkt</span>
              </div>
            </div>

            <div className="analysis-stats">
              <StatPill icon={Users} label="Convocados" value={selectedSummary?.players_count || 0} />
              <StatPill icon={BarChart3} label="Valor plantilla" value={formatMoney(selectedSummary?.squad_market_value || selectedMarket?.total_market_value)} />
              <StatPill icon={Trophy} label="Top 11" value={formatMoney(selectedSummary?.top_11_players_value)} />
              <StatPill icon={Flag} label="Ranking TM" value={selectedMarket?.fifa_ranking_transfermarkt || "s/d"} />
            </div>
          </div>

          <div className="analysis-grid">
            <section className="squad-panel">
              <div className="section-heading compact">
                <div>
                  <p className="eyebrow">Plantilla oficial</p>
                  <h3>Jugadores convocados</h3>
                </div>
              </div>

              {playersByPosition.map(([position, players]) => (
                <div className="position-group" key={position}>
                  <h4>{position}</h4>
                  <div className="player-list">
                    {players.map((player) => (
                      <article className="player-row" key={`${player.team}-${player.player}-${player.player_order_in_position}`}>
                        <div>
                          <strong>{player.player}</strong>
                          <span>{player.position || player.sub_position || position}</span>
                        </div>
                        <div>
                          <span>{player.transfermarkt_club || player.official_club || "Club s/d"}</span>
                          <strong>{formatMoney(player.market_value_in_eur)}</strong>
                        </div>
                      </article>
                    ))}
                  </div>
                </div>
              ))}
            </section>

            <section className="team-fixtures-panel">
              <div className="section-heading compact">
                <div>
                  <p className="eyebrow">Calendario</p>
                  <h3>Partidos y probabilidades</h3>
                </div>
              </div>

              <div className="team-fixture-list">
                {selectedTeamFixtures.map((row) => {
                  const selectedIsHome = canonicalTeamName(row.home_team) === canonicalTeamName(selectedAnalysisTeam);
                  const opponent = selectedIsHome ? row.away_team : row.home_team;
                  const winProbability = selectedIsHome ? row.home_win_probability : row.away_win_probability;
                  const loseProbability = selectedIsHome ? row.away_win_probability : row.home_win_probability;

                  return (
                    <button
                      className="team-fixture-card"
                      type="button"
                      key={`${row.date}-${row.home_team}-${row.away_team}`}
                      onClick={() => {
                        const fixture = fixtures.find((item) => item.date === row.date && item.home_team === row.home_team && item.away_team === row.away_team);
                        if (fixture) selectFixture(fixture);
                      }}
                    >
                      <div>
                        <span>{formatDate(row.date)} · {row.city}</span>
                        <strong>vs {opponent}</strong>
                      </div>
                      <div className="fixture-probability-summary">
                        <span>Gana {formatPercent(Number(winProbability))}</span>
                        <span>Empata {formatPercent(Number(row.draw_probability))}</span>
                        <span>Pierde {formatPercent(Number(loseProbability))}</span>
                      </div>
                      <p>Más probable: {row.predicted_winner} · {row.most_likely_score}</p>
                    </button>
                  );
                })}
              </div>
            </section>
          </div>
        </section>
      )}
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
