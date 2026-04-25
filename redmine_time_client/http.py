from __future__ import annotations

import logging
from typing import Union

import requests

from redmine_time_client.base import AbstractRedmineTimeClient, TimeEntryResult

logger = logging.getLogger(__name__)

DEFAULT_REDMINE_BASE_URL = "https://redmine.jprep.jp"
DEFAULT_TIME_ENTRIES_PATH = "/redmine/time_entries.json"


class HttpRedmineTimeClient(AbstractRedmineTimeClient):
    """
    Redmine REST client using requests.
    One instance per API key; safe to use from multiple threads if each call uses requests.post
    (no shared Session by default).
    """

    def __init__(
        self,
        api_key: str,
        time_entries_path: str = DEFAULT_TIME_ENTRIES_PATH,
        timeout: int = 15,
    ) -> None:
        self._base = DEFAULT_REDMINE_BASE_URL.rstrip("/")
        self._api_key = api_key
        self._path = time_entries_path if time_entries_path.startswith("/") else f"/{time_entries_path}"
        self._timeout = timeout
        self._url = f"{self._base}{self._path}"

    def post_time_entry(
        self,
        issue_id: Union[int, str],
        spent_on: str,
        hours: float,
        activity_id: int,
    ) -> TimeEntryResult:
        payload = {
            "time_entry": {
                "issue_id": int(issue_id) if str(issue_id).isdigit() else issue_id,
                "spent_on": spent_on,
                "hours": float(hours),
                "activity_id": int(activity_id),
            }
        }
        headers = {
            "Content-Type": "application/json",
            "X-Redmine-API-Key": self._api_key,
        }
        try:
            response = requests.post(
                self._url,
                json=payload,
                headers=headers,
                timeout=self._timeout,
            )
            text = response.text
            if response.status_code in (200, 201):
                return TimeEntryResult(
                    ok=True,
                    status_code=response.status_code,
                    response_text=text[:2000] if text else None,
                )
            err = text[:2000] if text else f"HTTP {response.status_code}"
            return TimeEntryResult(
                ok=False,
                status_code=response.status_code,
                error_message=err,
                response_text=text[:2000] if text else None,
            )
        except Exception as e:
            logger.warning("post_time_entry failed: %s", e)
            return TimeEntryResult(ok=False, error_message=str(e))
