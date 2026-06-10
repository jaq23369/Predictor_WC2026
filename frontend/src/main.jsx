import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  BarChart3,
  CalendarDays,
  ChevronRight,
  CircleAlert,
  Goal,
  Info,
  RefreshCw,
  Search,
  ShieldCheck,
  Trophy,
} from "lucide-react";
import {
  getTeams,
  getTransfermarktValues,
  getWorldCupFixtures,
  getWorldCupPredictions,
  predictMatch,
} from "./api";
import "./styles.css";

const PHASES = [
  {
    id: "group",
    label: "Fase de grupos",
    status: "Disponible",
    description: "Predicciones por partido usando los fixtures actuales.",
  },
  {
    id: "round16",
    label: "Octavos",
    status: "Pendiente",
    description: "Se calculará al simular clasificados desde grupos.",
  },
  {
    id: "quarter",
    label: "Cuartos",
    status: "Pendiente",
    description: "Depende de los cruces generados por simulación.",
  },
  {
    id: "semi",
    label: "Semifinales",
    status: "Pendiente",
    description: "Se actualizará cuando exista bracket simulado.",
  },
  {
    id: "final",
    label: "Final",
    status: "Pendiente",
    description: "Mostrará campeón probable tras Monte Carlo.",
  },
];

const DEFAULT_REQUEST = {
  team_a: "Mexico",
  team_b: "South Africa",
  match_date: "2026-06-11",
  neutral: false,
  team_a_is_home: true,
};

const GROUP_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("");

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
  return fixtures.find(
    (fixture) =>
      fixture.home_team === teamA &&
      fixture.away_team === teamB
  );
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

function App() {
  const [teams, setTeams] = useState([]);
  const [fixtures, setFixtures] = useState([]);
  const [fixturePredictions, setFixturePredictions] = useState([]);
  const [transfermarktValues, setTransfermarktValues] = useState([]);
  const [selectedPhase, setSelectedPhase] = useState("group");
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
        const [teamsResponse, fixturesResponse, predictionsResponse, transfermarktResponse] = await Promise.all([
          getTeams(),
          getWorldCupFixtures(),
          getWorldCupPredictions(),
          getTransfermarktValues(),
        ]);

        if (!active) return;

        setTeams(teamsResponse.teams);
        setFixtures(fixturesResponse);
        setFixturePredictions(predictionsResponse);
        setTransfermarktValues(transfermarktResponse);
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
    const grouped = new Map(
      groupData.groups.map((group) => [group.label, { ...group, matches: [] }])
    );

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
        matches: group.matches.sort((a, b) =>
          `${a.date}-${a.home_team}`.localeCompare(`${b.date}-${b.home_team}`)
        ),
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

  const selectedPhaseData = PHASES.find((phase) => phase.id === selectedPhase);
  const fixtureMeta = prediction ? pickFixtureMeta(fixtures, prediction.team_a, prediction.team_b) : null;
  const marketByTeam = useMemo(() => {
    const map = new Map();
    transfermarktValues.forEach((row) => map.set(row.team, row));
    return map;
  }, [transfermarktValues]);
  const marketA = prediction ? marketByTeam.get(prediction.team_a) : null;
  const marketB = prediction ? marketByTeam.get(prediction.team_b) : null;

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

      {error && (
        <div className="notice" role="alert">
          <CircleAlert size={18} />
          <span>{error}</span>
        </div>
      )}

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
              <select
                value={form.team_a}
                onChange={(event) => setForm({ ...form, team_a: event.target.value })}
              >
                {teams.map((team) => (
                  <option key={team} value={team}>{team}</option>
                ))}
              </select>
            </label>

            <label>
              Equipo B
              <select
                value={form.team_b}
                onChange={(event) => setForm({ ...form, team_b: event.target.value })}
              >
                {teams.map((team) => (
                  <option key={team} value={team}>{team}</option>
                ))}
              </select>
            </label>

            <label>
              Fecha
              <input
                type="date"
                value={form.match_date || ""}
                onChange={(event) => setForm({ ...form, match_date: event.target.value })}
              />
            </label>

            <div className="toggle-row">
              <label className="checkbox-line">
                <input
                  type="checkbox"
                  checked={form.neutral}
                  onChange={(event) => setForm({ ...form, neutral: event.target.checked })}
                />
                Sede neutral
              </label>
              <label className="checkbox-line">
                <input
                  type="checkbox"
                  checked={form.team_a_is_home}
                  onChange={(event) => setForm({ ...form, team_a_is_home: event.target.checked })}
                />
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

      <section className="phases-section">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Simulación</p>
            <h2>Estado por fase</h2>
          </div>
          <Info size={22} aria-hidden="true" />
        </div>

        <div className="phase-tabs" role="tablist" aria-label="Fases del Mundial">
          {PHASES.map((phase) => (
            <button
              key={phase.id}
              className={phase.id === selectedPhase ? "phase-tab active" : "phase-tab"}
              type="button"
              onClick={() => setSelectedPhase(phase.id)}
            >
              <span>{phase.label}</span>
              <small>{phase.status}</small>
            </button>
          ))}
        </div>

        <div className="phase-detail">
          <div>
            <h3>{selectedPhaseData.label}</h3>
            <p>{selectedPhaseData.description}</p>
          </div>
          {selectedPhase === "group" ? (
            <div className="phase-metrics">
              <StatPill icon={CalendarDays} label="Partidos" value={fixturePredictions.length} />
              <StatPill icon={Trophy} label="Favoritos 60%+" value={groupSummary.favorites} />
              <StatPill icon={Activity} label="Parejos" value={groupSummary.closeMatches} />
              <StatPill icon={BarChart3} label="Empate medio" value={formatPercent(groupSummary.avgDraw)} />
            </div>
          ) : (
            <div className="pending-card">
              <ChevronRight size={18} aria-hidden="true" />
              <span>Esta fase se calculará cuando agreguemos Monte Carlo para avanzar clasificados y cruces.</span>
            </div>
          )}
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
            <input
              type="search"
              placeholder="Buscar equipo, ciudad o ganador"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
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
                      const fixture = fixtures.find(
                        (item) =>
                          item.date === row.date &&
                          item.home_team === row.home_team &&
                          item.away_team === row.away_team
                      );
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
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
