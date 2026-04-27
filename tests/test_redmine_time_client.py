import unittest
from unittest.mock import MagicMock, patch

from app import app as flask_app
from redmine_time_client.base import TimeEntryResult
from redmine_time_client.factory import (
    backend_requires_api_key,
    create_redmine_time_client,
    parse_redmine_backend_from_env,
)
from redmine_time_client.http import DEFAULT_REDMINE_BASE_URL, HttpRedmineTimeClient
from redmine_time_client.mock import MockRedmineTimeClient


class TestHttpRedmineTimeClient(unittest.TestCase):
    def setUp(self):
        self.client = HttpRedmineTimeClient(
            api_key="secret",
            time_entries_path="/redmine/time_entries.json",
        )

    @patch("redmine_time_client.http.requests.post")
    def test_post_time_entry_success_201(self, mock_post: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.text = '{"time_entry":{"id":1}}'
        mock_post.return_value = mock_response

        r = self.client.post_time_entry(42, "2025-04-01", 2.5, 9)

        self.assertTrue(r.ok)
        self.assertEqual(r.status_code, 201)
        mock_post.assert_called_once()
        call_kw = mock_post.call_args[1]
        self.assertEqual(
            call_kw["json"],
            {
                "time_entry": {
                    "issue_id": 42,
                    "spent_on": "2025-04-01",
                    "hours": 2.5,
                    "activity_id": 9,
                }
            },
        )
        self.assertEqual(call_kw["headers"]["X-Redmine-API-Key"], "secret")

    @patch("redmine_time_client.http.requests.post")
    def test_post_time_entry_error_422(self, mock_post: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 422
        mock_response.text = "invalid"
        mock_post.return_value = mock_response

        r = self.client.post_time_entry(1, "2025-04-01", 1.0, 9)

        self.assertFalse(r.ok)
        self.assertEqual(r.status_code, 422)
        self.assertIn("invalid", r.error_message or "")

    @patch("redmine_time_client.http.requests.post")
    def test_post_time_entry_request_exception(self, mock_post: MagicMock) -> None:
        mock_post.side_effect = ConnectionError("network down")

        r = self.client.post_time_entry(1, "2025-04-01", 1.0, 9)

        self.assertFalse(r.ok)
        self.assertIn("network", (r.error_message or "").lower())

    @patch("redmine_time_client.http.requests.get")
    def test_list_time_entries_filters_and_paginates(self, mock_get: MagicMock) -> None:
        p1 = MagicMock()
        p1.json.return_value = {
            "time_entries": [
                {
                    "id": 10,
                    "issue": {"id": 42},
                    "spent_on": "2025-04-01",
                    "hours": 1.5,
                    "created_on": "2025-04-01T01:00:00Z",
                },
                {
                    "id": 11,
                    "issue": {"id": 77},
                    "spent_on": "2025-04-01",
                    "hours": 3.0,
                    "created_on": "2025-04-01T02:00:00Z",
                },
            ],
            "total_count": 3,
            "offset": 0,
            "limit": 2,
        }
        p1.raise_for_status.return_value = None
        p2 = MagicMock()
        p2.json.return_value = {
            "time_entries": [
                {
                    "id": 12,
                    "issue": {"id": 42},
                    "spent_on": "2025-04-01",
                    "hours": 2.0,
                    "created_on": "2025-04-01T03:00:00Z",
                }
            ],
            "total_count": 3,
            "offset": 2,
            "limit": 2,
        }
        p2.raise_for_status.return_value = None
        mock_get.side_effect = [p1, p2]

        rows = self.client.list_time_entries(42, "2025-04-01")

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].id, 10)
        self.assertEqual(rows[1].id, 12)
        self.assertEqual(mock_get.call_count, 2)


class TestMockRedmineTimeClient(unittest.TestCase):
    @patch("redmine_time_client.mock.time.sleep")
    @patch("redmine_time_client.mock.random.random", return_value=0.9)
    def test_post_time_entry_returns_201(
        self, mock_random: MagicMock, mock_sleep: MagicMock
    ) -> None:
        c = MockRedmineTimeClient()
        r = c.post_time_entry(1, "2025-01-01", 1.0, 9)
        mock_sleep.assert_called_once_with(1)
        mock_random.assert_called_once()
        self.assertTrue(r.ok)
        self.assertEqual(r.status_code, 201)

    @patch("redmine_time_client.mock.time.sleep")
    @patch("redmine_time_client.mock.random.choice")
    @patch("redmine_time_client.mock.random.random", return_value=0.0)
    def test_post_time_entry_returns_error_when_random_hits_error_rate(
        self,
        mock_random: MagicMock,
        mock_choice: MagicMock,
        mock_sleep: MagicMock,
    ) -> None:
        expected_error = TimeEntryResult(
            ok=False,
            status_code=500,
            error_message="Internal Server Error",
            response_text="<html><body>500</body></html>",
        )
        mock_choice.return_value = expected_error
        c = MockRedmineTimeClient()
        r = c.post_time_entry(1, "2025-01-01", 1.0, 9)
        mock_sleep.assert_called_once_with(1)
        mock_random.assert_called_once()
        mock_choice.assert_called_once()
        self.assertFalse(r.ok)
        self.assertEqual(r.status_code, 500)

    @patch("redmine_time_client.mock.time.sleep")
    def test_post_time_entry_custom_sequence_cycles(self, mock_sleep: MagicMock) -> None:
        seq = [
            TimeEntryResult(ok=True, status_code=201, response_text="{}"),
            TimeEntryResult(
                ok=False,
                status_code=404,
                error_message="not found",
                response_text=None,
            ),
        ]
        c = MockRedmineTimeClient(responses=seq)
        self.assertTrue(c.post_time_entry(1, "2025-01-01", 1.0, 9).ok)
        r2 = c.post_time_entry(1, "2025-01-01", 1.0, 9)
        self.assertFalse(r2.ok)
        self.assertEqual(r2.status_code, 404)
        r3 = c.post_time_entry(1, "2025-01-01", 1.0, 9)
        self.assertTrue(r3.ok)
        self.assertEqual(r3.status_code, 201)
        self.assertEqual(mock_sleep.call_count, 3)

    @patch("redmine_time_client.mock.time.sleep")
    @patch("redmine_time_client.mock.random.random", return_value=0.9)
    def test_list_time_entries_reads_saved_entries(
        self, mock_random: MagicMock, mock_sleep: MagicMock
    ) -> None:
        c = MockRedmineTimeClient(default_error_rate=0.0)
        c.post_time_entry(1, "2025-01-01", 1.0, 9)
        c.post_time_entry(1, "2025-01-01", 2.5, 9)
        rows = c.list_time_entries(1, "2025-01-01")
        self.assertEqual(len(rows), 2)
        self.assertAlmostEqual(sum(r.hours for r in rows), 3.5)
        self.assertEqual(mock_sleep.call_count, 2)
        self.assertEqual(mock_random.call_count, 2)

class TestRedmineClientFactory(unittest.TestCase):
    def test_parse_redmine_backend_from_env_mock_values(self) -> None:
        for val in ("1", "true", "yes", "TRUE", "  Yes "):
            with self.subTest(val=val):
                self.assertEqual(
                    parse_redmine_backend_from_env({"REDMINE_MOCK": val}),
                    "mock",
                )

    def test_parse_redmine_backend_from_env_http_when_unset_or_falsey(self) -> None:
        self.assertEqual(parse_redmine_backend_from_env({}), "http")
        self.assertEqual(
            parse_redmine_backend_from_env({"REDMINE_MOCK": "0"}),
            "http",
        )

    def test_backend_requires_api_key(self) -> None:
        self.assertFalse(backend_requires_api_key("mock"))
        self.assertTrue(backend_requires_api_key("http"))

    def test_create_redmine_time_client_mock(self) -> None:
        c = create_redmine_time_client("mock", api_key=None)
        self.assertIsInstance(c, MockRedmineTimeClient)

    def test_create_redmine_time_client_http(self) -> None:
        c = create_redmine_time_client("http", api_key="k")
        self.assertIsInstance(c, HttpRedmineTimeClient)
        self.assertEqual(c._base, DEFAULT_REDMINE_BASE_URL.rstrip("/"))

    def test_create_redmine_time_client_http_requires_key(self) -> None:
        with self.assertRaises(ValueError):
            create_redmine_time_client("http", api_key=None)


class TestCheckDiffApi(unittest.TestCase):
    def setUp(self) -> None:
        flask_app.config["TESTING"] = True
        flask_app.config["REDMINE_BACKEND"] = "http"
        self.client = flask_app.test_client()

    @patch("app.create_redmine_time_client")
    def test_check_diff_same_and_diff(self, mock_factory: MagicMock) -> None:
        mock_client = MagicMock()
        mock_client.list_time_entries.side_effect = [
            [MagicMock(hours=2.0)],
            [MagicMock(hours=1.0)],
        ]
        mock_factory.return_value = mock_client

        resp = self.client.post(
            "/api/sync/check",
            json={
                "apiKey": "k",
                "entries": [
                    {"issue_id": "1", "spent_on": "2025-04-01", "hours": 2.0},
                    {"issue_id": "2", "spent_on": "2025-04-02", "hours": 3.0},
                ],
            },
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(len(data["items"]), 2)
        self.assertTrue(data["items"][0]["is_same"])
        self.assertFalse(data["items"][1]["is_same"])
        self.assertEqual(data["items"][1]["delta"], 2.0)


if __name__ == "__main__":
    unittest.main()
