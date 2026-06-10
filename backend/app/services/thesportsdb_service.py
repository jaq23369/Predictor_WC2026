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


BASE_URL = "https://www.thesportsdb.com/api/v1/json"
DEFAULT_API_KEY = "123"
DEFAULT_TIMEOUT = 30


class TheSportsDBError(RuntimeError):
    pass


class TheSportsDBClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = 2,
        request_delay: float = 0.25,
    ) -> None:
        load_dotenv()
        self.api_key = api_key or os.getenv("THESPORTSDB_API_KEY", DEFAULT_API_KEY)
        self.base_url = (base_url or os.getenv("THESPORTSDB_BASE_URL", BASE_URL)).rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.request_delay = request_delay

    def get(self, endpoint: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        query = f"?{urlencode(params)}" if params else ""
        url = f"{self.base_url}/{self.api_key}/{endpoint}{query}"
        attempts = 0

        while True:
            request = Request(url, headers={"User-Agent": "Predicciones-Mundial2026/0.1"})
            try:
                if self.request_delay > 0:
                    time.sleep(self.request_delay)
                with urlopen(request, timeout=self.timeout) as response:
                    body = response.read().decode("utf-8")
                    return {
                        "data": json.loads(body),
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
                raise TheSportsDBError(f"TheSportsDB error {error.code}: {detail}") from error

    def search_team(self, name: str) -> dict[str, Any]:
        return self.get("searchteams.php", {"t": name})

    def lookup_team(self, team_id: str) -> dict[str, Any]:
        return self.get("lookupteam.php", {"id": team_id})

    def lookup_all_players(self, team_id: str) -> dict[str, Any]:
        return self.get("lookup_all_players.php", {"id": team_id})

    def last_events(self, team_id: str) -> dict[str, Any]:
        return self.get("eventslast.php", {"id": team_id})

    def next_events(self, team_id: str) -> dict[str, Any]:
        return self.get("eventsnext.php", {"id": team_id})

    def lookup_event(self, event_id: str) -> dict[str, Any]:
        return self.get("lookupevent.php", {"id": event_id})

    def lookup_event_stats(self, event_id: str) -> dict[str, Any]:
        return self.get("lookupeventstats.php", {"id": event_id})

    def lookup_lineup(self, event_id: str) -> dict[str, Any]:
        return self.get("lookuplineup.php", {"id": event_id})

    def lookup_timeline(self, event_id: str) -> dict[str, Any]:
        return self.get("lookuptimeline.php", {"id": event_id})
