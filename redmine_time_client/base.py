from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Union


@dataclass
class TimeEntryResult:
    """Result of a single Redmine time entry create request."""

    ok: bool
    status_code: Optional[int] = None
    error_message: Optional[str] = None
    response_text: Optional[str] = None


@dataclass
class RedmineTimeEntry:
    id: int
    issue_id: Union[int, str, None]
    spent_on: str
    hours: float
    created_on: str


class AbstractRedmineTimeClient(ABC):
    """
    Abstract client for posting one time entry to Redmine.
    Implement this in tests with a mock that does not perform HTTP.
    """

    @abstractmethod
    def post_time_entry(
        self,
        issue_id: Union[int, str],
        spent_on: str,
        hours: float,
        activity_id: int,
    ) -> TimeEntryResult:
        """POST one time entry. `spent_on` is ISO date string YYYY-MM-DD."""
        raise NotImplementedError

    @abstractmethod
    def list_time_entries(
        self,
        issue_id: Union[int, str],
        spent_on: str,
    ) -> List[RedmineTimeEntry]:
        """List time entries for an issue and date (`spent_on`: YYYY-MM-DD)."""
        raise NotImplementedError
