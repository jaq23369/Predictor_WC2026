from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class MatchPredictionRequest(BaseModel):
    team_a: str = Field(..., examples=["Mexico"])
    team_b: str = Field(..., examples=["South Africa"])
    match_date: date | None = Field(None, examples=["2026-06-11"])
    neutral: bool = Field(True)
    team_a_is_home: bool = Field(False)


class ScorelineProbability(BaseModel):
    score: str
    probability: float


class MatchProbabilities(BaseModel):
    team_a_win: float
    draw: float
    team_b_win: float


class ExpectedGoals(BaseModel):
    team_a: float
    team_b: float


class EstimatedMetricValue(BaseModel):
    team_a: float
    team_b: float


class EstimatedMatchMetric(BaseModel):
    key: str
    label: str
    unit: str = ""
    decimals: int = 1
    team_values: EstimatedMetricValue
    note: str


class RecentTeamResult(BaseModel):
    date: date
    home_team: str
    away_team: str
    home_score: int
    away_score: int
    opponent: str
    goals_for: int
    goals_against: int
    result_for_team: str
    tournament: str = ""


class RecentResults(BaseModel):
    team_a: list[RecentTeamResult]
    team_b: list[RecentTeamResult]


class RecentTeamSummary(BaseModel):
    matches: int
    wins: int
    draws: int
    losses: int
    points: int
    goals_for: int
    goals_against: int
    avg_goals_for: float
    avg_goals_against: float
    clean_sheets: int
    scored_in_matches: int


class RecentSummary(BaseModel):
    team_a: RecentTeamSummary
    team_b: RecentTeamSummary


class RecentMatchStatsValue(BaseModel):
    matches: int
    avg_possession: float
    avg_shots: float
    avg_shots_on_target: float
    avg_chances_created: float
    avg_corners: float
    avg_fouls: float
    avg_yellow_cards: float
    avg_red_cards: float


class RecentMatchStats(BaseModel):
    team_a: RecentMatchStatsValue
    team_b: RecentMatchStatsValue


class MatchMonteCarlo(BaseModel):
    simulations: int
    probabilities: MatchProbabilities
    winner: str
    expected_goals: ExpectedGoals
    top_scorelines: list[ScorelineProbability]


class MatchPredictionResponse(BaseModel):
    team_a: str
    team_b: str
    match_date: date
    winner: str
    probabilities: MatchProbabilities
    model_probabilities: MatchProbabilities
    expected_goals: ExpectedGoals
    monte_carlo: MatchMonteCarlo
    estimated_match_metrics: list[EstimatedMatchMetric]
    top_scorelines: list[ScorelineProbability]
    recent_results: RecentResults
    recent_summary: RecentSummary
    recent_match_stats: RecentMatchStats


class TeamsResponse(BaseModel):
    teams: list[str]


class HealthResponse(BaseModel):
    status: str
    models_loaded: bool
