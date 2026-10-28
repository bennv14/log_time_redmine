from __future__ import annotations

import json
import logging
import random
import time
from typing import List, Optional, Union

import requests
from requests.adapters import HTTPAdapter

from redmine_time_client.base import (
    AbstractRedmineTimeClient,
    RedmineTimeEntry,
    TimeEntryResult,
)

logger = logging.getLogger(__name__)

DEFAULT_JPREP_BASE_URL = "https://redmine.jprep.jp"
DEFAULT_PLANIO_BASE_URL = "https://bennv.planio.com"
DEFAULT_REDMINE_BASE_URL = DEFAULT_JPREP_BASE_URL
DEFAULT_JPREP_TIME_ENTRIES_PATH = "/redmine/time_entries.json"
DEFAULT_PLANIO_TIME_ENTRIES_PATH = "/time_entries.json"
DEFAULT_TIME_ENTRIES_PATH = DEFAULT_JPREP_TIME_ENTRIES_PATH


class HttpRedmineTimeClient(AbstractRedmineTimeClient):
    """
    Redmine REST client using requests.Session with connection pooling and throttling jitter.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_REDMINE_BASE_URL,
        time_entries_path: str = DEFAULT_TIME_ENTRIES_PATH,
        timeout: int = 15,
        pool_connections: int = 10,
        pool_maxsize: int = 10,
        jitter_ms: float = 50.0,
        session: Optional[requests.Session] = None,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._api_key = api_key
        self._path = time_entries_path if time_entries_path.startswith("/") else f"/{time_entries_path}"
        self._timeout = timeout
        self._url = f"{self._base}{self._path}"
        self._jitter_ms = jitter_ms

        if session is not None:
            self._session = session
        else:
            self._session = requests.Session()
            adapter = HTTPAdapter(
                pool_connections=pool_connections,
                pool_maxsize=pool_maxsize,
                max_retries=0,
            )
            self._session.mount("http://", adapter)
            self._session.mount("https://", adapter)

    def _throttle(self) -> None:
        if self._jitter_ms > 0:
            delay = random.uniform(self._jitter_ms * 0.8, self._jitter_ms * 1.2) / 1000.0
            time.sleep(delay)

    def close(self) -> None:
        """Close the underlying requests Session."""
        self._session.close()

    def __enter__(self) -> HttpRedmineTimeClient:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def _entry_url(self, entry_id: Union[int, str]) -> str:
        path_without_json = self._path[:-5] if self._path.endswith(".json") else self._path
        return f"{self._base}{path_without_json}/{entry_id}.json"

    def _parse_error(self, text: str, status_code: int) -> str:
        if not text:
            return f"HTTP {status_code}"
        try:
            data = json.loads(text)
            if isinstance(data, dict) and "errors" in data:
                errors = data["errors"]
                if isinstance(errors, list):
                    return "\n".join(str(e) for e in errors)
                return str(errors)
        except Exception:
            pass
        return text[:2000]

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
            self._throttle()
            response = self._session.post(
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
                    request_url=self._url,
                    request_headers=headers,
                    request_payload=payload,
                )
            err = self._parse_error(text, response.status_code)
            return TimeEntryResult(
                ok=False,
                status_code=response.status_code,
                error_message=err,
                response_text=text[:2000] if text else None,
                request_url=self._url,
                request_headers=headers,
                request_payload=payload,
            )
        except Exception as e:
            logger.warning("post_time_entry failed: %s", e)
            return TimeEntryResult(
                ok=False,
                error_message=str(e),
                request_url=self._url,
                request_headers=headers,
                request_payload=payload,
            )

    def list_time_entries(
        self,
        issue_id: Union[int, str],
        spent_on: str,
        user_id: Union[int, str, None] = None,
    ) -> List[RedmineTimeEntry]:
        headers = {"X-Redmine-API-Key": self._api_key}
        entries: List[RedmineTimeEntry] = []
        offset = 0
        limit = 100

        while True:
            params = {
                "issue_id": issue_id,
                "spent_on": spent_on,
                "offset": offset,
                "limit": limit,
            }
            if user_id is not None:
                params["user_id"] = user_id
            self._throttle()
            response = self._session.get(
                self._url,
                params=params,
                headers=headers,
                timeout=self._timeout,
            )
            response.raise_for_status()
            body = response.json() or {}
            items = body.get("time_entries", [])
            total_count = int(body.get("total_count", len(items)))

            for item in items:
                item_spent_on = str(item.get("spent_on") or "")
                raw_issue = item.get("issue") or {}
                item_issue_id = raw_issue.get("id", item.get("issue_id"))
                if str(item_issue_id) != str(issue_id) or item_spent_on != spent_on:
                    continue
                entries.append(
                    RedmineTimeEntry(
                        id=int(item.get("id")),
                        issue_id=item_issue_id,
                        spent_on=item_spent_on,
                        hours=float(item.get("hours") or 0),
                        created_on=str(item.get("created_on") or ""),
                        comments=str(item.get("comments") or ""),
                    )
                )

            offset += len(items)
            if offset >= total_count or not items:
                break

        return entries

    def list_time_entries_in_range(
        self,
        issue_ids: List[Union[int, str]],
        from_date: str,
        to_date: str,
        user_id: Union[int, str, None] = None,
    ) -> List[RedmineTimeEntry]:
        if not issue_ids:
            return []
        headers = {"X-Redmine-API-Key": self._api_key}
        entries: List[RedmineTimeEntry] = []
        offset = 0
        limit = 100
        issue_ids_str = ",".join(str(i) for i in issue_ids)

        while True:
            params = {
                "issue_id": issue_ids_str,
                "from": from_date,
                "to": to_date,
                "offset": offset,
                "limit": limit,
            }
            if user_id is not None:
                params["user_id"] = user_id
            self._throttle()
            response = self._session.get(
                self._url,
                params=params,
                headers=headers,
                timeout=self._timeout,
            )
            response.raise_for_status()
            body = response.json() or {}
            items = body.get("time_entries", [])
            total_count = int(body.get("total_count", len(items)))

            for item in items:
                raw_issue = item.get("issue") or {}
                item_issue_id = raw_issue.get("id", item.get("issue_id"))
                item_spent_on = str(item.get("spent_on") or "")
                entries.append(
                    RedmineTimeEntry(
                        id=int(item.get("id")),
                        issue_id=item_issue_id,
                        spent_on=item_spent_on,
                        hours=float(item.get("hours") or 0),
                        created_on=str(item.get("created_on") or ""),
                        comments=str(item.get("comments") or ""),
                    )
                )

            offset += len(items)
            if offset >= total_count or not items:
                break

        return entries

    def list_user_time_entries_in_range(
        self,
        from_date: str,
        to_date: str,
        user_id: Union[int, str, None] = None,
    ) -> List[RedmineTimeEntry]:
        headers = {"X-Redmine-API-Key": self._api_key}
        entries: List[RedmineTimeEntry] = []
        offset = 0
        limit = 100

        while True:
            params = {
                "from": from_date,
                "to": to_date,
                "offset": offset,
                "limit": limit,
            }
            if user_id is not None:
                params["user_id"] = user_id
            self._throttle()
            response = self._session.get(
                self._url,
                params=params,
                headers=headers,
                timeout=self._timeout,
            )
            response.raise_for_status()
            body = response.json() or {}
            items = body.get("time_entries", [])
            total_count = int(body.get("total_count", len(items)))

            for item in items:
                raw_issue = item.get("issue") or {}
                item_issue_id = raw_issue.get("id", item.get("issue_id"))
                item_spent_on = str(item.get("spent_on") or "")
                entries.append(
                    RedmineTimeEntry(
                        id=int(item.get("id")),
                        issue_id=item_issue_id,
                        spent_on=item_spent_on,
                        hours=float(item.get("hours") or 0),
                        created_on=str(item.get("created_on") or ""),
                        comments=str(item.get("comments") or ""),
                    )
                )

            offset += len(items)
            if offset >= total_count or not items:
                break

        return entries

    def update_time_entry(
        self,
        entry_id: Union[int, str],
        hours: float,
    ) -> TimeEntryResult:
        payload = {"time_entry": {"hours": float(hours)}}
        headers = {
            "Content-Type": "application/json",
            "X-Redmine-API-Key": self._api_key,
        }
        try:
            url = self._entry_url(entry_id)
            self._throttle()
            response = self._session.put(
                url,
                json=payload,
                headers=headers,
                timeout=self._timeout,
            )
            text = response.text
            if response.status_code in (200, 204):
                return TimeEntryResult(
                    ok=True,
                    status_code=response.status_code,
                    response_text=text[:2000] if text else None,
                    request_url=url,
                    request_headers=headers,
                    request_payload=payload,
                )
            err = self._parse_error(text, response.status_code)
            return TimeEntryResult(
                ok=False,
                status_code=response.status_code,
                error_message=err,
                response_text=text[:2000] if text else None,
                request_url=url,
                request_headers=headers,
                request_payload=payload,
            )
        except Exception as e:
            logger.warning("update_time_entry failed: %s", e)
            return TimeEntryResult(
                ok=False,
                error_message=str(e),
                request_url=self._entry_url(entry_id),
                request_headers=headers,
                request_payload=payload,
            )

    def delete_time_entry(self, entry_id: Union[int, str]) -> TimeEntryResult:
        headers = {"X-Redmine-API-Key": self._api_key}
        url = self._entry_url(entry_id)
        try:
            self._throttle()
            response = self._session.delete(
                url,
                headers=headers,
                timeout=self._timeout,
            )
            text = response.text
            if response.status_code in (200, 204):
                return TimeEntryResult(
                    ok=True,
                    status_code=response.status_code,
                    response_text=text[:2000] if text else None,
                    request_url=url,
                    request_headers=headers,
                )
            err = self._parse_error(text, response.status_code)
            return TimeEntryResult(
                ok=False,
                status_code=response.status_code,
                error_message=err,
                response_text=text[:2000] if text else None,
                request_url=url,
                request_headers=headers,
            )
        except Exception as e:
            logger.warning("delete_time_entry failed: %s", e)
            return TimeEntryResult(
                ok=False,
                error_message=str(e),
                request_url=url,
                request_headers=headers,
            )
