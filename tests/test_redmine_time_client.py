import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from app import app as flask_app
from redmine_time_client.base import RedmineTimeEntry, TimeEntryResult
from redmine_time_client.factory import (
    backend_requires_api_key,
    create_redmine_time_client,
    parse_redmine_backend_from_env,
)
from redmine_time_client.http import (
    DEFAULT_JPREP_BASE_URL,
    DEFAULT_JPREP_TIME_ENTRIES_PATH,
    DEFAULT_PLANIO_BASE_URL,
    DEFAULT_PLANIO_TIME_ENTRIES_PATH,
    DEFAULT_REDMINE_BASE_URL,
    HttpRedmineTimeClient,
)
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
        self.assertEqual(
            mock_post.call_args[0][0],
            f"{DEFAULT_REDMINE_BASE_URL}{DEFAULT_JPREP_TIME_ENTRIES_PATH}",
        )

    @patch("redmine_time_client.http.requests.post")
    def test_post_time_entry_uses_planio_config(self, mock_post: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.text = '{"time_entry":{"id":2}}'
        mock_post.return_value = mock_response
        client = HttpRedmineTimeClient(
            api_key="secret",
            base_url=DEFAULT_PLANIO_BASE_URL,
            time_entries_path=DEFAULT_PLANIO_TIME_ENTRIES_PATH,
        )

        r = client.post_time_entry(42, "2025-04-01", 2.5, 9)

        self.assertTrue(r.ok)
        self.assertEqual(
            mock_post.call_args[0][0],
            f"{DEFAULT_PLANIO_BASE_URL}{DEFAULT_PLANIO_TIME_ENTRIES_PATH}",
        )

    @patch("redmine_time_client.http.requests.put")
    def test_update_time_entry_uses_individual_url(self, mock_put: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_response.text = ""
        mock_put.return_value = mock_response

        r = self.client.update_time_entry(123, 2.0)

        self.assertTrue(r.ok)
        self.assertEqual(r.status_code, 204)
        self.assertEqual(
            mock_put.call_args[0][0],
            f"{DEFAULT_REDMINE_BASE_URL}/redmine/time_entries/123.json",
        )
        self.assertEqual(mock_put.call_args[1]["json"], {"time_entry": {"hours": 2.0}})

    @patch("redmine_time_client.http.requests.delete")
    def test_delete_time_entry_uses_individual_url(self, mock_delete: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_response.text = ""
        mock_delete.return_value = mock_response

        r = self.client.delete_time_entry(123)

        self.assertTrue(r.ok)
        self.assertEqual(r.status_code, 204)
        self.assertEqual(
            mock_delete.call_args[0][0],
            f"{DEFAULT_REDMINE_BASE_URL}/redmine/time_entries/123.json",
        )

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

    @patch("redmine_time_client.http.requests.get")
    def test_list_user_time_entries_in_range_no_issue_filter(self, mock_get: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {
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
                    "spent_on": "2025-04-02",
                    "hours": 3.0,
                    "created_on": "2025-04-02T02:00:00Z",
                },
            ],
            "total_count": 2,
            "offset": 0,
            "limit": 100,
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        rows = self.client.list_user_time_entries_in_range("2025-04-01", "2025-04-30")

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].id, 10)
        self.assertEqual(rows[0].issue_id, 42)
        self.assertEqual(rows[1].id, 11)
        self.assertEqual(rows[1].issue_id, 77)
        call_params = mock_get.call_args[1]["params"]
        self.assertNotIn("issue_id", call_params)
        self.assertEqual(call_params["from"], "2025-04-01")
        self.assertEqual(call_params["to"], "2025-04-30")


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

    @patch("redmine_time_client.mock.time.sleep")
    @patch("redmine_time_client.mock.random.random", return_value=0.9)
    def test_update_and_delete_time_entry_mutates_saved_entries(
        self, mock_random: MagicMock, mock_sleep: MagicMock
    ) -> None:
        c = MockRedmineTimeClient(default_error_rate=0.0)
        c.post_time_entry(1, "2025-01-01", 1.0, 9)
        entry = c.list_time_entries(1, "2025-01-01")[0]

        update_res = c.update_time_entry(entry.id, 2.5)
        self.assertTrue(update_res.ok)
        self.assertAlmostEqual(c.list_time_entries(1, "2025-01-01")[0].hours, 2.5)

        delete_res = c.delete_time_entry(entry.id)
        self.assertTrue(delete_res.ok)
        self.assertEqual(c.list_time_entries(1, "2025-01-01"), [])

    def test_list_user_time_entries_in_range_returns_all_entries_in_range(self) -> None:
        existing = [
            RedmineTimeEntry(10, 1, "2025-04-01", 1.5, "now"),
            RedmineTimeEntry(11, 2, "2025-04-02", 2.0, "now"),
            RedmineTimeEntry(12, 1, "2025-04-03", 3.0, "now"),
            RedmineTimeEntry(13, 3, "2025-04-05", 1.0, "now"),
        ]
        c = MockRedmineTimeClient(existing_entries=existing)

        rows = c.list_user_time_entries_in_range("2025-04-01", "2025-04-30")

        self.assertEqual(len(rows), 4)
        issue_ids = {r.issue_id for r in rows}
        self.assertEqual(issue_ids, {1, 2, 3})
        spent_ons = {r.spent_on for r in rows}
        self.assertEqual(spent_ons, {"2025-04-01", "2025-04-02", "2025-04-03", "2025-04-05"})


class TestRedmineClientFactory(unittest.TestCase):
    def test_parse_redmine_backend_from_env_mock_values(self) -> None:
        for val in ("1", "true", "yes", "TRUE", "  Yes "):
            with self.subTest(val=val):
                self.assertEqual(
                    parse_redmine_backend_from_env({"REDMINE_MOCK": val}),
                    "mock",
                )

    def test_parse_redmine_backend_from_env_jprep_when_unset_or_falsey(self) -> None:
        self.assertEqual(parse_redmine_backend_from_env({}), "jprep")
        self.assertEqual(
            parse_redmine_backend_from_env({"REDMINE_MOCK": "0"}),
            "jprep",
        )

    def test_parse_redmine_backend_from_env_explicit_clients(self) -> None:
        self.assertEqual(
            parse_redmine_backend_from_env({"REDMINE_CLIENT": "planio"}),
            "planio",
        )
        self.assertEqual(
            parse_redmine_backend_from_env({"REDMINE_CLIENT": "jprep"}),
            "jprep",
        )
        self.assertEqual(
            parse_redmine_backend_from_env({"REDMINE_CLIENT": "mock"}),
            "mock",
        )

    def test_parse_redmine_backend_from_env_mock_overrides_client(self) -> None:
        self.assertEqual(
            parse_redmine_backend_from_env(
                {"REDMINE_CLIENT": "planio", "REDMINE_MOCK": "true"}
            ),
            "mock",
        )

    def test_parse_redmine_backend_from_env_rejects_unknown_client(self) -> None:
        with self.assertRaises(ValueError):
            parse_redmine_backend_from_env({"REDMINE_CLIENT": "unknown"})

    def test_backend_requires_api_key(self) -> None:
        self.assertFalse(backend_requires_api_key("mock"))
        self.assertTrue(backend_requires_api_key("jprep"))
        self.assertTrue(backend_requires_api_key("planio"))

    def test_create_redmine_time_client_mock(self) -> None:
        c = create_redmine_time_client("mock", api_key=None)
        self.assertIsInstance(c, MockRedmineTimeClient)

    def test_create_redmine_time_client_jprep(self) -> None:
        c = create_redmine_time_client("jprep", api_key="k")
        self.assertIsInstance(c, HttpRedmineTimeClient)
        self.assertEqual(c._base, DEFAULT_JPREP_BASE_URL.rstrip("/"))
        self.assertEqual(c._path, DEFAULT_JPREP_TIME_ENTRIES_PATH)

    def test_create_redmine_time_client_planio(self) -> None:
        c = create_redmine_time_client("planio", api_key="k")
        self.assertIsInstance(c, HttpRedmineTimeClient)
        self.assertEqual(c._base, DEFAULT_PLANIO_BASE_URL.rstrip("/"))
        self.assertEqual(c._path, DEFAULT_PLANIO_TIME_ENTRIES_PATH)

    def test_create_redmine_time_client_http_alias_uses_jprep(self) -> None:
        c = create_redmine_time_client("http", api_key="k")
        self.assertIsInstance(c, HttpRedmineTimeClient)
        self.assertEqual(c._base, DEFAULT_JPREP_BASE_URL.rstrip("/"))
        self.assertEqual(c._path, DEFAULT_JPREP_TIME_ENTRIES_PATH)

    def test_create_redmine_time_client_http_requires_key(self) -> None:
        with self.assertRaises(ValueError):
            create_redmine_time_client("planio", api_key=None)


class TestCheckDiffApi(unittest.TestCase):
    def setUp(self) -> None:
        flask_app.config["TESTING"] = True
        flask_app.config["REDMINE_CLIENT"] = "jprep"
        self.client = flask_app.test_client()

    @patch("app._SSE_MAX_WORKERS", 1)
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

    @patch("app._SSE_MAX_WORKERS", 1)
    @patch("app.create_redmine_time_client")
    def test_resolve_check_diff_creates_missing_and_delta_and_blocks_greater(
        self, mock_factory: MagicMock
    ) -> None:
        mock_client = MagicMock()
        mock_client.list_time_entries.side_effect = [
            [],
            [RedmineTimeEntry(100, 1, "2025-04-01", 2.0, "now")],
            [RedmineTimeEntry(200, 2, "2025-04-02", 1.0, "now")],
            [
                RedmineTimeEntry(200, 2, "2025-04-02", 1.0, "now"),
                RedmineTimeEntry(201, 2, "2025-04-02", 2.0, "now"),
            ],
            [RedmineTimeEntry(300, 3, "2025-04-03", 5.0, "now")],
        ]
        mock_client.post_time_entry.side_effect = [
            TimeEntryResult(ok=True, status_code=201, response_text="{}"),
            TimeEntryResult(ok=True, status_code=201, response_text="{}"),
        ]
        mock_factory.return_value = mock_client

        resp = self.client.post(
            "/api/sync/check/resolve/stream",
            json={
                "apiKey": "k",
                "entries": [
                    {"issue_id": "1", "spent_on": "2025-04-01", "hours": 2.0},
                    {"issue_id": "2", "spent_on": "2025-04-02", "hours": 3.0},
                    {"issue_id": "3", "spent_on": "2025-04-03", "hours": 2.0},
                ],
            },
        )

        self.assertEqual(resp.status_code, 200)
        text = resp.get_data(as_text=True)
        self.assertIn('"action": "created_missing"', text)
        self.assertIn('"action": "created_delta"', text)
        self.assertIn('"action": "blocked_redmine_greater"', text)
        self.assertIn('"success": 2', text)
        self.assertIn('"failed": 1', text)
        self.assertEqual(mock_client.post_time_entry.call_count, 2)
        self.assertEqual(mock_client.post_time_entry.call_args_list[0].args[:3], ("1", "2025-04-01", 2.0))
        self.assertEqual(mock_client.post_time_entry.call_args_list[1].args[:3], ("2", "2025-04-02", 2.0))

    @patch("app.create_redmine_time_client")
    def test_mutate_redmine_time_entry_updates_and_returns_check(
        self, mock_factory: MagicMock
    ) -> None:
        mock_client = MagicMock()
        mock_client.update_time_entry.return_value = TimeEntryResult(ok=True, status_code=204)
        mock_client.list_time_entries.return_value = [
            RedmineTimeEntry(10, 1, "2025-04-01", 2.0, "now")
        ]
        mock_factory.return_value = mock_client

        resp = self.client.patch(
            "/api/sync/check/time-entry/10",
            json={
                "apiKey": "k",
                "issueId": "1",
                "spentOn": "2025-04-01",
                "webHours": 2.0,
                "hours": 2.0,
            },
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["ok"])
        self.assertTrue(data["check"]["is_same"])
        mock_client.update_time_entry.assert_called_once_with("10", 2.0)

    @patch("app.create_redmine_time_client")
    def test_mutate_redmine_time_entry_deletes_and_returns_check(
        self, mock_factory: MagicMock
    ) -> None:
        mock_client = MagicMock()
        mock_client.delete_time_entry.return_value = TimeEntryResult(ok=True, status_code=204)
        mock_client.list_time_entries.return_value = []
        mock_factory.return_value = mock_client

        resp = self.client.delete(
            "/api/sync/check/time-entry/10",
            json={
                "apiKey": "k",
                "issueId": "1",
                "spentOn": "2025-04-01",
                "webHours": 2.0,
            },
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["check"]["redmine_hours"], 0)
        mock_client.delete_time_entry.assert_called_once_with("10")

    @patch("app.create_redmine_time_client")
    def test_check_user_range_returns_all_redmine_entries(self, mock_factory: MagicMock) -> None:
        mock_client = MagicMock()
        mock_client.list_user_time_entries_in_range.return_value = [
            RedmineTimeEntry(10, 42, "2025-04-01", 1.5, "now"),
            RedmineTimeEntry(11, 77, "2025-04-02", 2.0, "now"),
        ]
        mock_factory.return_value = mock_client

        resp = self.client.post(
            "/api/sync/check/user-range",
            json={
                "apiKey": "k",
                "from_date": "2025-04-01",
                "to_date": "2025-04-30",
            },
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("issues", data)
        self.assertEqual(len(data["issues"]), 2)
        self.assertIn("42", data["issues"])
        self.assertIn("77", data["issues"])
        mock_client.list_user_time_entries_in_range.assert_called_once_with(
            from_date="2025-04-01", to_date="2025-04-30", user_id="me"
        )


class TestUploadCsvApi(unittest.TestCase):
    def setUp(self) -> None:
        flask_app.config["TESTING"] = True
        self.client = flask_app.test_client()

    def test_upload_hb2_timesheet_returns_json(self) -> None:
        csv_path = (
            Path(__file__).resolve().parents[1]
            / "HB2_1799_JPREP Dojo_Timesheet_202604.csv"
        )

        with csv_path.open("rb") as f:
            resp = self.client.post(
                "/api/upload",
                data={"file": (f, csv_path.name)},
                content_type="multipart/form-data",
            )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content_type, "application/json")
        data = resp.get_json()
        self.assertEqual(data["memberName"], "Nguyen Van Ben")
        self.assertEqual(data["role"], "Dev App")
        self.assertEqual(data["effortSum"], 76.0)
        self.assertIn("2026-04-01", data["dates"])
        self.assertEqual(data["tasks"][0]["taskId"], 1)


if __name__ == "__main__":
    unittest.main()
