from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from backend.app.services.football_data_service import load_dotenv, parse_retry_after


BASE_URL = "https://v3.football.api-sports.io"
DEFAULT_TIMEOUT = 30


class APIFootballError(RuntimeError):
    pass


class APIFootballClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = 2,
        request_delay: float = 0.35,
    ) -> None:
        load_dotenv()
        self.api_key = api_key or os.getenv("API_FOOTBALL_API_KEY")
        self.base_url = (base_url or os.getenv("API_FOOTBALL_BASE_URL", BASE_URL)).rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.request_delay = request_delay

        if not self.api_key:
            raise APIFootballError(
                "Falta API_FOOTBALL_API_KEY. Define la variable de entorno o crea un .env local."
            )

    def get(self, path: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        query = f"?{urlencode(params)}" if params else ""
        url = f"{self.base_url}{path}{query}"
        attempts = 0

        while True:
            request = Request(
                url,
                headers={
                    "x-apisports-key": self.api_key,
                    "User-Agent": "Predicciones-Mundial2026/0.1",
                },
            )
            try:
                if self.request_delay > 0:
                    time.sleep(self.request_delay)
                with urlopen(request, timeout=self.timeout) as response:
                    body = response.read().decode("utf-8")
                    data = json.loads(body)
                    errors = data.get("errors")
                    if errors:
                        if isinstance(errors, dict) and errors.get("rateLimit") and attempts < self.max_retries:
                            attempts += 1
                            time.sleep(65)
                            continue
                        raise APIFootballError(f"API-Football error: {errors}")
                    return {
                        "data": data,
                        "headers": dict(response.headers.items()),
                        "synced_at": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
                        "url": url,
                    }
            except HTTPError as error:
                headers = dict(error.headers.items()) if error.headers else {}
                if error.code == 429 and attempts < self.max_retries:
                    attempts += 1
                    time.sleep(parse_retry_after(headers.get("Retry-After")))
                    continue

                detail = error.read().decode("utf-8", errors="replace")
                raise APIFootballError(f"API-Football error {error.code}: {detail}") from error

    def search_team(self, name: str) -> dict[str, Any]:
        return self.get("/teams", {"search": name})

    def team_fixtures(self, team_id: str, last: int = 5) -> dict[str, Any]:
        return self.get("/fixtures", {"team": team_id, "last": str(last)})

    def team_fixtures_between(self, team_id: str, season: int, from_date: str, to_date: str) -> dict[str, Any]:
        return self.get(
            "/fixtures",
            {"team": team_id, "season": str(season), "from": from_date, "to": to_date},
        )

    def fixture_statistics(self, fixture_id: str) -> dict[str, Any]:
        return self.get("/fixtures/statistics", {"fixture": fixture_id})

    def fixture_events(self, fixture_id: str) -> dict[str, Any]:
        return self.get("/fixtures/events", {"fixture": fixture_id})

    def fixture_lineups(self, fixture_id: str) -> dict[str, Any]:
        return self.get("/fixtures/lineups", {"fixture": fixture_id})
