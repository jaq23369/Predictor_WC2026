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


class MatchPredictionResponse(BaseModel):
    team_a: str
    team_b: str
    match_date: date
    winner: str
    probabilities: MatchProbabilities
    expected_goals: ExpectedGoals
    estimated_match_metrics: list[EstimatedMatchMetric]
    top_scorelines: list[ScorelineProbability]


class TeamsResponse(BaseModel):
    teams: list[str]


class HealthResponse(BaseModel):
    status: str
    models_loaded: bool
