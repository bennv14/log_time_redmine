from __future__ import annotations

import os
from typing import Literal, Mapping, Optional

from redmine_time_client.base import AbstractRedmineTimeClient
from redmine_time_client.http import (
    DEFAULT_JPREP_BASE_URL,
    DEFAULT_JPREP_TIME_ENTRIES_PATH,
    DEFAULT_PLANIO_BASE_URL,
    DEFAULT_PLANIO_TIME_ENTRIES_PATH,
    HttpRedmineTimeClient,
)
from redmine_time_client.mock import MockRedmineTimeClient

RedmineBackend = Literal["mock", "jprep", "planio", "http"]

_mock_singleton: Optional[MockRedmineTimeClient] = None

_HTTP_CONFIG = {
    "jprep": (DEFAULT_JPREP_BASE_URL, DEFAULT_JPREP_TIME_ENTRIES_PATH),
    "http": (DEFAULT_JPREP_BASE_URL, DEFAULT_JPREP_TIME_ENTRIES_PATH),
    "planio": (DEFAULT_PLANIO_BASE_URL, DEFAULT_PLANIO_TIME_ENTRIES_PATH),
}


def parse_redmine_backend_from_env(
    environ: Optional[Mapping[str, str]] = None,
) -> RedmineBackend:
    """Read Redmine client config once at startup.

    REDMINE_CLIENT accepts: mock, jprep, planio. REDMINE_MOCK remains supported
    for existing local workflows and overrides REDMINE_CLIENT when truthy.
    """
    src = os.environ if environ is None else environ
    raw_mock = str(src.get("REDMINE_MOCK", "") or "").strip().lower()
    if raw_mock in ("1", "true", "yes"):
        return "mock"
    raw_client = str(src.get("REDMINE_CLIENT", "") or "").strip().lower()
    if not raw_client:
        return "jprep"
    if raw_client in ("mock", "jprep", "planio", "http"):
        return raw_client  # type: ignore[return-value]
    raise ValueError(f"Unsupported REDMINE_CLIENT: {raw_client}")


def backend_requires_api_key(backend: RedmineBackend) -> bool:
    return backend != "mock"


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
    config = _HTTP_CONFIG.get(backend)
    if config is None:
        raise ValueError(f"Unsupported Redmine backend: {backend}")
    base_url, time_entries_path = config
    return HttpRedmineTimeClient(
        api_key=api_key,
        base_url=base_url,
        time_entries_path=time_entries_path,
    )
