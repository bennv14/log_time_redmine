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
    comments: str = ""


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
        user_id: Optional[Union[int, str]] = None,
    ) -> List[RedmineTimeEntry]:
        """List time entries for an issue and date (`spent_on`: YYYY-MM-DD).

        Args:
            issue_id: The Redmine issue ID.
            spent_on: The date in YYYY-MM-DD format.
            user_id: Filter by user. Use "me" for current user, or specific user ID.
        """
        raise NotImplementedError

    @abstractmethod
    def list_time_entries_in_range(
        self,
        issue_ids: List[Union[int, str]],
        from_date: str,
        to_date: str,
        user_id: Optional[Union[int, str]] = None,
    ) -> List[RedmineTimeEntry]:
        """List time entries for multiple issues within a date range.

        Args:
            issue_ids: List of Redmine issue IDs.
            from_date: Start date in YYYY-MM-DD format.
            to_date: End date in YYYY-MM-DD format.
            user_id: Filter by user. Use "me" for current user, or specific user ID.
        """
        raise NotImplementedError

    @abstractmethod
    def list_user_time_entries_in_range(
        self,
        from_date: str,
        to_date: str,
        user_id: Optional[Union[int, str]] = None,
    ) -> List[RedmineTimeEntry]:
        """List ALL time entries for a user within a date range (no issue_id filter).

        Args:
            from_date: Start date in YYYY-MM-DD format.
            to_date: End date in YYYY-MM-DD format.
            user_id: Filter by user. Use "me" for current user, or specific user ID.
        """
        raise NotImplementedError

    @abstractmethod
    def update_time_entry(
        self,
        entry_id: Union[int, str],
        hours: float,
    ) -> TimeEntryResult:
        """Update one existing time entry."""
        raise NotImplementedError

    @abstractmethod
    def delete_time_entry(self, entry_id: Union[int, str]) -> TimeEntryResult:
        """Delete one existing time entry."""
        raise NotImplementedError
