from __future__ import annotations

from functools import lru_cache

from backend.app.services.prediction_service import PredictionService


@lru_cache(maxsize=1)
def get_prediction_service() -> PredictionService:
    return PredictionService()
