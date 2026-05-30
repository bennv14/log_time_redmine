import pytest
from playwright.sync_api import expect


TEST_URL = "http://localhost:5001"


def test_check_diff_button_exists(page):
    page.goto(TEST_URL)
    page.wait_for_load_state("networkidle")

    content = page.content()
    print("Page content length:", len(content))
    print("Page title:", page.title())

    api_key_input = page.locator("#api-key")
    check_diff_btn = page.locator("#btn-check-diff")

    print("api_key_input count:", api_key_input.count())
    print("check_diff_btn count:", check_diff_btn.count())

    expect(api_key_input).to_be_visible()
    expect(check_diff_btn).to_be_visible()


def test_check_diff_button_disabled_without_api_key(page):
    page.goto(TEST_URL)
    page.wait_for_load_state("networkidle")
    check_diff_btn = page.locator("#btn-check-diff")
    expect(check_diff_btn).to_be_enabled()


def test_check_diff_button_enabled_with_api_key(page):
    page.goto(TEST_URL)
    page.wait_for_load_state("networkidle")
    api_key_input = page.locator("#api-key")
    check_diff_btn = page.locator("#btn-check-diff")

    api_key_input.fill("test-api-key")
    expect(check_diff_btn).to_be_enabled()


def test_collect_check_data_sends_only_date_range(page):
    page.goto(TEST_URL)
    page.wait_for_load_state("networkidle")
    api_key_input = page.locator("#api-key")
    check_diff_btn = page.locator("#btn-check-diff")

    def handle_route(route):
        body = route.request.post_data
        if body:
            data = route.request.post_data_json
            if "from_date" in data or "to_date" in data:
                response_body = b'{"issues": {}}'
                route.fulfill(status=200, body=response_body, content_type="application/json")
                return
        route.continue_()

    page.route("**/api/sync/check/user-range", handle_route)

    api_key_input.fill("test-api-key")
    check_diff_btn.click()

    page.wait_for_timeout(500)


def test_check_diff_returns_all_redmine_entries_in_date_range(page):
    page.goto(TEST_URL)
    page.wait_for_load_state("networkidle")
    api_key_input = page.locator("#api-key")
    check_diff_btn = page.locator("#btn-check-diff")

    def handle_route(route):
        response_body = b'''{"issues": {"42": [{"id": 10, "issue_id": 42, "spent_on": "2025-04-01", "hours": 1.5, "created_on": "now", "comments": ""}], "77": [{"id": 12, "issue_id": 77, "spent_on": "2025-04-01", "hours": 3.0, "created_on": "now", "comments": ""}]}}'''
        route.fulfill(status=200, body=response_body, content_type="application/json")

    page.route("**/api/sync/check/user-range", handle_route)

    api_key_input.fill("test-api-key")
    check_diff_btn.click()

    page.wait_for_timeout(1000)