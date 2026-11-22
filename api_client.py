"""Small standard-library Dolibarr REST API client (Python 3.14)."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


class DolibarrAPIError(RuntimeError):
    pass


class DolibarrClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        self.base_url = (base_url or os.getenv("DOLIBARR_BASE_URL", "")).rstrip("/")
        self.api_key = api_key or os.getenv("DOLIBARR_API_KEY", "")
        if not self.base_url:
            raise ValueError("Set DOLIBARR_BASE_URL, e.g. https://your-host/dolibarr/api/index.php")
        if not self.api_key:
            raise ValueError("Set DOLIBARR_API_KEY to your Dolibarr API token")
        self.api_root = self.base_url if self.base_url.endswith("/api/index.php") else self.base_url + "/api/index.php"

    def request(self, method: str, path: str, *, params: dict | None = None,
                body: dict | None = None) -> Any:
        url = self.api_root + "/" + path.lstrip("/")
        if params:
            url += "?" + urllib.parse.urlencode(params)
        data = None if body is None else json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            method=method,
            headers={
                "DOLAPIKEY": self.api_key,
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise DolibarrAPIError(
                f"{method} {url} failed with HTTP {exc.code}: {details}"
            ) from exc
        except urllib.error.URLError as exc:
            raise DolibarrAPIError(f"Could not connect to Dolibarr: {exc.reason}") from exc

    def get(self, path: str, params: dict | None = None) -> Any:
        return self.request("GET", path, params=params)

    def post(self, path: str, body: dict) -> Any:
        return self.request("POST", path, body=body)
