from __future__ import annotations

import os
from typing import Literal, Mapping, Optional

from redmine_time_client.base import AbstractRedmineTimeClient
from redmine_time_client.http import HttpRedmineTimeClient
from redmine_time_client.mock import MockRedmineTimeClient

RedmineBackend = Literal["mock", "http"]

_mock_singleton: Optional[MockRedmineTimeClient] = None


def parse_redmine_backend_from_env(
    environ: Optional[Mapping[str, str]] = None,
) -> RedmineBackend:
    """Read REDMINE_MOCK once at startup; truthy values select mock backend."""
    src = os.environ if environ is None else environ
    raw = str(src.get("REDMINE_MOCK", "") or "").strip().lower()
    if raw in ("1", "true", "yes"):
        return "mock"
    return "http"


def backend_requires_api_key(backend: RedmineBackend) -> bool:
    return backend == "http"


def _get_mock_client() -> MockRedmineTimeClient:
    global _mock_singleton
    if _mock_singleton is None:
        _mock_singleton = MockRedmineTimeClient()
    return _mock_singleton


def create_redmine_time_client(
    backend: RedmineBackend,
    *,
    api_key: Optional[str],
) -> AbstractRedmineTimeClient:
    if backend == "mock":
        return _get_mock_client()
    if not api_key:
        raise ValueError("api_key is required for http backend")
    return HttpRedmineTimeClient(api_key=api_key)
