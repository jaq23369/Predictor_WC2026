from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.app.dependencies import get_prediction_service
from backend.app.schemas.prediction import (
    HealthResponse,
    MatchPredictionRequest,
    MatchPredictionResponse,
    TeamsResponse,
)
from backend.app.services.prediction_service import PredictionService


router = APIRouter(tags=["predictions"])


@router.get("/health", response_model=HealthResponse)
def health(service: PredictionService = Depends(get_prediction_service)) -> HealthResponse:
    return HealthResponse(status="ok", models_loaded=bool(service.feature_columns))


@router.get("/teams", response_model=TeamsResponse)
def teams(service: PredictionService = Depends(get_prediction_service)) -> TeamsResponse:
    return TeamsResponse(teams=service.available_teams())


@router.post("/predict", response_model=MatchPredictionResponse)
def predict(
    request: MatchPredictionRequest,
    service: PredictionService = Depends(get_prediction_service),
) -> dict:
    try:
        return service.predict_match(
            request.team_a,
            request.team_b,
            match_date=request.match_date,
            neutral=int(request.neutral),
            team_a_is_home=int(request.team_a_is_home),
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/scores", response_model=MatchPredictionResponse)
def scores(
    request: MatchPredictionRequest,
    service: PredictionService = Depends(get_prediction_service),
) -> dict:
    try:
        return service.predict_match(
            request.team_a,
            request.team_b,
            match_date=request.match_date,
            neutral=int(request.neutral),
            team_a_is_home=int(request.team_a_is_home),
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/world-cup-2026/fixtures")
def world_cup_2026_fixtures(
    service: PredictionService = Depends(get_prediction_service),
) -> list[dict[str, str]]:
    return service.world_cup_2026_fixtures()


@router.get("/world-cup-2026/predictions")
def world_cup_2026_predictions(
    service: PredictionService = Depends(get_prediction_service),
) -> list[dict[str, str]]:
    return service.world_cup_2026_predictions()


@router.get("/football-data/world-cup-2026/matches")
def football_data_world_cup_2026_matches(
    service: PredictionService = Depends(get_prediction_service),
) -> list[dict[str, str]]:
    return service.football_data_world_cup_matches()


@router.get("/football-data/world-cup-2026/teams")
def football_data_world_cup_2026_teams(
    service: PredictionService = Depends(get_prediction_service),
) -> list[dict[str, str]]:
    return service.football_data_world_cup_teams()


@router.get("/football-data/world-cup-2026/standings")
def football_data_world_cup_2026_standings(
    service: PredictionService = Depends(get_prediction_service),
) -> list[dict[str, str]]:
    return service.football_data_world_cup_standings()


@router.get("/transfermarkt/national-team-values")
def transfermarkt_national_team_values(
    service: PredictionService = Depends(get_prediction_service),
) -> list[dict[str, str]]:
    return service.transfermarkt_national_team_values()
