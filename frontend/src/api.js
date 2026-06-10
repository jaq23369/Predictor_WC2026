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

export function predictMatch(payload) {
  return request("/predict", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
