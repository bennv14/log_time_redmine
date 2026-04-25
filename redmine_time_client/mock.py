from __future__ import annotations

import random
import time
from typing import List, Optional, Sequence, Union

from redmine_time_client.base import AbstractRedmineTimeClient, TimeEntryResult


def _default_success() -> TimeEntryResult:
    return TimeEntryResult(
        ok=True,
        status_code=201,
        response_text='{"time_entry":{"id":0,"mock":true}}',
    )


def _default_error_pool() -> list[TimeEntryResult]:
    return [
        TimeEntryResult(
            ok=False,
            status_code=422,
            error_message='{"errors":["Activity cannot be blank"]}',
            response_text='{"errors":["Activity cannot be blank"]}',
        ),
        TimeEntryResult(
            ok=False,
            status_code=401,
            error_message="HTTP Basic: Access denied.",
            response_text="HTTP Basic: Access denied.",
        ),
        TimeEntryResult(
            ok=False,
            status_code=500,
            error_message="Internal Server Error",
            response_text="<html><body>500</body></html>",
        ),
        TimeEntryResult(
            ok=False,
            status_code=None,
            error_message="Connection refused (mock)",
            response_text=None,
        ),
    ]


class MockRedmineTimeClient(AbstractRedmineTimeClient):
    """
    No HTTP. Default: randomized mock responses with occasional errors.

    Pass ``responses`` to return a rotating sequence: success, 4xx/5xx bodies,
    or ``ok=False`` with no ``status_code`` (like transport errors in Http client).
    """

    def __init__(
        self,
        *,
        responses: Optional[Sequence[TimeEntryResult]] = None,
        default_error_rate: float = 0.3,
    ) -> None:
        self._sequence: Optional[List[TimeEntryResult]] = (
            list(responses) if responses is not None else None
        )
        self._call_index = 0
        self._default_error_rate = default_error_rate
        self._default_error_pool = _default_error_pool()

    def post_time_entry(
        self,
        issue_id: Union[int, str],
        spent_on: str,
        hours: float,
        activity_id: int,
    ) -> TimeEntryResult:
        time.sleep(1)
        if not self._sequence:
            if random.random() < self._default_error_rate:
                return random.choice(self._default_error_pool)
            return _default_success()
        r = self._sequence[self._call_index % len(self._sequence)]
        self._call_index += 1
        return r

