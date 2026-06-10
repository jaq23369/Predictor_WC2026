const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "No se pudo completar la solicitud.");
  }

  return response.json();
}

export function getTeams() {
  return request("/teams");
}

export function getWorldCupFixtures() {
  return request("/world-cup-2026/fixtures");
}

export function getWorldCupPredictions() {
  return request("/world-cup-2026/predictions");
}

export function getTransfermarktValues() {
  return request("/transfermarkt/national-team-values");
}

export function getFootballDataTeams() {
  return request("/football-data/world-cup-2026/teams");
}

export function getSquads() {
  return request("/world-cup-2026/squads");
}

export function getSquadSummary() {
  return request("/world-cup-2026/squad-summary");
}

export function getSimulation() {
  return request("/world-cup-2026/simulation");
}

export function getTheSportsDBCoverage() {
  return request("/thesportsdb/coverage");
}

export function getTheSportsDBRecentForm() {
  return request("/thesportsdb/recent-form");
}

export function getTheSportsDBRecentMatchStats() {
  return request("/thesportsdb/recent-match-stats");
}

export function getAPIFootballTeamMatchStats() {
  return request("/api-football/team-match-stats");
}

export function getAPIFootballCoverage() {
  return request("/api-football/coverage");
}

export function predictMatch(payload) {
  return request("/predict", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
