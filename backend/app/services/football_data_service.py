from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen


BASE_URL = "https://api.football-data.org/v4"
DEFAULT_TIMEOUT = 30


class FootballDataError(RuntimeError):
    pass


def load_dotenv(path: Path | None = None) -> None:
    env_path = path or Path.cwd() / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def parse_retry_after(value: str | None) -> float:
    if not value:
        return 60.0
    try:
        return float(value)
    except ValueError:
        return 60.0


class FootballDataClient:
    def __init__(
        self,
        token: str | None = None,
        base_url: str = BASE_URL,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = 2,
    ) -> None:
        load_dotenv()
        self.token = token or os.getenv("FOOTBALL_DATA_API_TOKEN")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

        if not self.token:
            raise FootballDataError(
                "Falta FOOTBALL_DATA_API_TOKEN. Define la variable de entorno o crea un .env local."
            )

    def get(self, path: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        query = ""
        if params:
            from urllib.parse import urlencode

            query = f"?{urlencode(params)}"

        url = f"{self.base_url}{path}{query}"
        attempts = 0

        while True:
            request = Request(url, headers={"X-Auth-Token": self.token})
            try:
                with urlopen(request, timeout=self.timeout) as response:
                    body = response.read().decode("utf-8")
                    return {
                        "data": json.loads(body),
                        "headers": dict(response.headers.items()),
                        "synced_at": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
                    }
            except HTTPError as error:
                headers = dict(error.headers.items()) if error.headers else {}
                if error.code == 429 and attempts < self.max_retries:
                    attempts += 1
                    time.sleep(parse_retry_after(headers.get("Retry-After")))
                    continue

                detail = error.read().decode("utf-8", errors="replace")
                raise FootballDataError(
                    f"football-data.org error {error.code}: {detail}"
                ) from error

    def world_cup_matches(self, season: int | None = None) -> dict[str, Any]:
        params = {"season": str(season)} if season else None
        return self.get("/competitions/WC/matches", params=params)

    def world_cup_standings(self, season: int | None = None) -> dict[str, Any]:
        params = {"season": str(season)} if season else None
        return self.get("/competitions/WC/standings", params=params)

    def world_cup_teams(self, season: int | None = None) -> dict[str, Any]:
        params = {"season": str(season)} if season else None
        return self.get("/competitions/WC/teams", params=params)

    def world_cup_scorers(self, season: int | None = None) -> dict[str, Any]:
        params = {"season": str(season)} if season else None
        return self.get("/competitions/WC/scorers", params=params)

    def head_to_head(self, match_id: int) -> dict[str, Any]:
        return self.get(f"/matches/{match_id}/head2head")
