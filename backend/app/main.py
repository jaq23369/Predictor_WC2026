from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.routes.predictions import router as predictions_router


app = FastAPI(
    title="World Cup 2026 Predictor API",
    description="API para predicciones de partidos y marcadores del Mundial 2026.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        *(origin.strip() for origin in os.getenv("CORS_ORIGINS", "").split(",") if origin.strip()),
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(predictions_router)
app.include_router(predictions_router, prefix="/api")
