import argparse
import csv
import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

from flask import Flask, Response, jsonify, render_template, request, stream_with_context
from flask_cors import CORS

from redmine_time_client import (
    AbstractRedmineTimeClient,
    RedmineTimeEntry,
    TimeEntryResult,
    backend_requires_api_key,
    create_redmine_time_client,
    parse_redmine_backend_from_env,
)

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)

DEFAULT_ACTIVITY_ID = 9

_ACTIVITY_IDS = {
    "jprep": 9,
    "planio": 20,
    "mock": 9,
}


def _apply_redmine_backend_config(flask_app: Flask) -> None:
    """Resolve Redmine client once per process; set REDMINE_CLIENT on app config."""
    flask_app.config["REDMINE_CLIENT"] = parse_redmine_backend_from_env()


_apply_redmine_backend_config(app)

DEFAULT_ACTIVITY_ID = _ACTIVITY_IDS.get(app.config["REDMINE_CLIENT"], 9)

_LOGS_DIR = Path(__file__).resolve().parent / "logs"
_LOGS_DIR.mkdir(parents=True, exist_ok=True)
_time_entry_logger = logging.getLogger("app.time_entry")
_time_entry_logger.setLevel(logging.INFO)
if not _time_entry_logger.handlers:
    _te_handler = logging.FileHandler(
        _LOGS_DIR / "redmine_time_entry.log", encoding="utf-8"
    )
    _te_handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    _time_entry_logger.addHandler(_te_handler)
_time_entry_logger.propagate = False


def _log_time_entry_result(entry: Dict[str, Any], res: TimeEntryResult) -> None:
    record: Dict[str, Any] = {
        "entry_id": str(entry.get("entry_id", "")),
        "issue_id": entry.get("issue_id"),
        "spent_on": entry.get("spent_on"),
        "hours": entry.get("hours"),
        "activity_id": entry.get("activity_id", DEFAULT_ACTIVITY_ID),
        "ok": res.ok,
        "status_code": res.status_code,
        "error": res.error_message,
        "request_url": res.request_url,
        "request_headers": res.request_headers,
        "request_payload": res.request_payload,
        "response_text": res.response_text,
    }
    _time_entry_logger.info(json.dumps(record, ensure_ascii=False))

def extract_task_id(url):
    match = re.search(r'/(\d+)$', url)
    return int(match.group(1)) if match else None

def format_date_with_current_year(date_str):
    if not date_str:
        return ""
    # Assuming format like "12/05" -> "YYYY-12-05"
    try:
        current_year = datetime.now().year
        # Handle "DD/MM" or "MM/DD" - assuming "MM/DD" based on common usage, but let's check
        # Actually, let's just append year and parse if it's MM/DD
        parts = date_str.split('/')
        if len(parts) == 2:
            return f"{current_year}-{parts[0].zfill(2)}-{parts[1].zfill(2)}" # Assuming MM/DD or DD/MM, let's just format it
        return date_str
    except Exception:
        return date_str

@app.route('/')
def index():
    return render_template('index.html', DEFAULT_ACTIVITY_ID=DEFAULT_ACTIVITY_ID)

@app.route('/api/upload', methods=['POST'])
def upload_csv():
    if 'file' not in request.files:
        return jsonify({"error": "Không tìm thấy tệp được tải lên"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Bạn chưa chọn tệp CSV"}), 400
    
    if file:
        try:
            stream = file.stream.read().decode("utf-8")
            reader = csv.reader(stream.splitlines())
            
            parsed_data = {
                "memberName": "",
                "role": "",
                "effortSum": 0.0,
                "tasks": [],
                "dates": []
            }
            
            lines = list(reader)
            if not lines:
                return jsonify({"error": "Tệp CSV trống"}), 400

            header_idx = -1
            no_idx = -1

            # Find header row
            for i, row in enumerate(lines):
                if row:
                    for j, cell in enumerate(row):
                        if cell.strip().lower() == "no":
                            header_idx = i
                            no_idx = j
                            break
                if header_idx != -1:
                    break

            if header_idx == -1:
                return jsonify({"error": "Định dạng CSV không hợp lệ: không tìm thấy cột 'No'"}), 400

            # Validation errors list
            validation_errors = []

            # Extract basic info
            effort_sum_from_meta = 0.0
            for i in range(header_idx):
                row = lines[i]
                for j, cell in enumerate(row):
                    key = cell.strip().lower()
                    if "name" in key or "thành viên" in key or "member" in key:
                        if len(row) > j + 1:
                            parsed_data["memberName"] = row[j+1].strip()
                    elif "role" in key or "vai trò" in key:
                        if len(row) > j + 1:
                            parsed_data["role"] = row[j+1].strip()
                    elif "effort sum" in key or "tổng công suất" in key:
                        if len(row) > j + 1:
                            try:
                                effort_sum_from_meta = float(row[j+1].strip())
                            except ValueError:
                                pass

            header_row = lines[header_idx]
            # Find date columns
            date_cols = []
            for j in range(len(header_row)):
                col_name = header_row[j].strip()
                if re.match(r'\d{1,2}/\d{1,2}', col_name):
                    date_cols.append({"index": j, "date": format_date_with_current_year(col_name), "raw": col_name})

            if not date_cols:
                return jsonify({"error": "Không tìm thấy cột ngày (định dạng MM/DD)"}), 400

            parsed_data["dates"] = [d["date"] for d in date_cols]

            # Find "Task Effort (h)" column index
            effort_col_idx = -1
            for j, cell in enumerate(header_row):
                if "effort" in cell.lower() and "(h)" in cell.lower():
                    effort_col_idx = j
                    break

            # Parse tasks
            actual_sum = 0.0
            daily_sums = {d["date"]: 0.0 for d in date_cols}
            sum_row = None

            for i in range(header_idx + 1, len(lines)):
                row = lines[i]
                if not row or len(row) <= no_idx:
                    continue

                no_val = row[no_idx].strip().lower()
                if no_val == "sum":
                    sum_row = row
                    continue

                # Assuming columns: No, Task Name, Task URL, ... dates ...
                task_name = row[no_idx + 1].strip() if len(row) > no_idx + 1 else ""
                task_url = row[no_idx + 2].strip() if len(row) > no_idx + 2 else ""
                task_id = extract_task_id(task_url)

                # Validation: Task ID missing if Task Name/URL exists
                if (task_name or task_url) and not task_id and no_val:
                    if "ouchieigo" not in task_name.lower(): # Special case from sample
                         validation_errors.append(f"Dòng {i+1}: URL công việc không chứa ID Redmine hợp lệ")

                day_entries = {}
                task_total = 0.0

                for d in date_cols:
                    if d["index"] < len(row):
                        val = row[d["index"]].strip()
                        if val:
                            try:
                                hours = float(val)
                                if hours < 0:
                                    validation_errors.append(f"Dòng {i+1}, ngày {d['raw']}: Giờ không được âm ({val})")
                                elif hours > 24:
                                    validation_errors.append(f"Dòng {i+1}, ngày {d['raw']}: Giờ vượt quá 24h ({val})")
                            except ValueError:
                                validation_errors.append(f"Dòng {i+1}, ngày {d['raw']}: Giá trị không phải số ({val})")
                                hours = 0.0
                        else:
                            hours = 0.0
                        day_entries[d["date"]] = hours
                        task_total += hours
                        daily_sums[d["date"]] += hours

                # Skip rows that have no sequence number, no task info, and no hours
                if not no_val and not task_name and not task_url and task_total == 0:
                    continue

                parsed_data["tasks"].append({
                    "id": str(task_id) if task_id else f"temp_{i}",
                    "taskId": task_id,
                    "taskName": task_name,
                    "taskUrl": task_url,
                    "dayEntries": day_entries,
                    "totalHours": task_total
                })
                actual_sum += task_total

            parsed_data["effortSum"] = actual_sum

            if validation_errors:
                parsed_data["validationErrors"] = validation_errors

            return jsonify(parsed_data)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

_SSE_MAX_WORKERS = 10


def _format_sse(data: Dict[str, Any]) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def _build_check_items(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for raw in entries:
        issue_id = str(raw.get("issue_id", "")).strip()
        spent_on = str(raw.get("spent_on", "")).strip()
        if not issue_id or not spent_on:
            continue
        key = (issue_id, spent_on)
        item = grouped.get(key)
        if item is None:
            item = {
                "issue_id": issue_id,
                "spent_on": spent_on,
                "web_hours": 0.0,
                "activity_id": int(raw.get("activity_id", DEFAULT_ACTIVITY_ID)),
            }
            grouped[key] = item
        item["web_hours"] += float(raw.get("hours", 0) or 0)
    return list(grouped.values())


def _check_range(
    client: AbstractRedmineTimeClient,
    issue_ids: List[Union[int, str]],
    from_date: str,
    to_date: str,
) -> Dict[str, List[Dict[str, Any]]]:
    try:
        redmine_entries = client.list_time_entries_in_range(
            issue_ids=issue_ids,
            from_date=from_date,
            to_date=to_date,
            user_id="me",
        )
        result: Dict[str, List[Dict[str, Any]]] = {}
        for entry in redmine_entries:
            issue_id_str = str(entry.issue_id)
            if issue_id_str not in result:
                result[issue_id_str] = []
            result[issue_id_str].append(_serialize_redmine_time_entry(entry))
        return result
    except Exception as e:
        app.logger.error("check range failed: %s", e)
        raise


def _check_user_range(
    client: AbstractRedmineTimeClient,
    from_date: str,
    to_date: str,
) -> Dict[str, List[Dict[str, Any]]]:
    try:
        redmine_entries = client.list_user_time_entries_in_range(
            from_date=from_date,
            to_date=to_date,
            user_id="me",
        )
        result: Dict[str, List[Dict[str, Any]]] = {}
        for entry in redmine_entries:
            issue_id_str = str(entry.issue_id)
            if issue_id_str not in result:
                result[issue_id_str] = []
            result[issue_id_str].append(_serialize_redmine_time_entry(entry))
        return result
    except Exception as e:
        app.logger.error("check user range failed: %s", e)
        raise


def _serialize_redmine_time_entry(entry) -> Dict[str, Any]:
    raw_id = getattr(entry, "id", None)
    raw_issue_id = getattr(entry, "issue_id", None)
    return {
        "id": raw_id if isinstance(raw_id, (int, str)) else None,
        "issue_id": raw_issue_id if isinstance(raw_issue_id, (int, str)) else None,
        "spent_on": str(getattr(entry, "spent_on", "") or ""),
        "hours": float(getattr(entry, "hours", 0) or 0),
        "created_on": str(getattr(entry, "created_on", "") or ""),
        "comments": str(getattr(entry, "comments", "") or ""),
    }


def _check_one(
    client: AbstractRedmineTimeClient, item: Dict[str, Any]
) -> Dict[str, Any]:
    issue_id = item["issue_id"]
    spent_on = item["spent_on"]
    web_hours = float(item["web_hours"])
    try:
        redmine_entries = client.list_time_entries(issue_id=issue_id, spent_on=spent_on, user_id="me")
        redmine_hours = float(sum(float(e.hours or 0) for e in redmine_entries))
        delta = round(web_hours - redmine_hours, 4)
        return {
            "issue_id": issue_id,
            "spent_on": spent_on,
            "web_hours": round(web_hours, 4),
            "redmine_hours": round(redmine_hours, 4),
            "delta": delta,
            "is_same": abs(delta) < 1e-9,
            "count_redmine_entries": len(redmine_entries),
            "redmine_entries": [
                _serialize_redmine_time_entry(e) for e in redmine_entries
            ],
        }
    except Exception as e:
        app.logger.error("check diff failed (%s, %s): %s", issue_id, spent_on, e)
        return {
            "issue_id": issue_id,
            "spent_on": spent_on,
            "web_hours": round(web_hours, 4),
            "redmine_hours": None,
            "delta": None,
            "is_same": False,
            "error": str(e),
            "redmine_entries": [],
        }


def _resolve_check_diff_one(
    client: AbstractRedmineTimeClient, item: Dict[str, Any]
) -> Dict[str, Any]:
    issue_id = item["issue_id"]
    spent_on = item["spent_on"]
    web_hours = round(float(item["web_hours"]), 4)
    activity_id = int(item.get("activity_id", DEFAULT_ACTIVITY_ID))
    try:
        before = _check_one(client, item)
        if before.get("error"):
            return {
                "type": "result",
                "issue_id": issue_id,
                "spent_on": spent_on,
                "web_hours": web_hours,
                "ok": False,
                "action": "error",
                "error": before["error"],
                "check": before,
            }

        redmine_hours = float(before.get("redmine_hours") or 0)
        delta = round(web_hours - redmine_hours, 4)
        if abs(delta) < 1e-9:
            return {
                "type": "result",
                "issue_id": issue_id,
                "spent_on": spent_on,
                "web_hours": web_hours,
                "ok": True,
                "action": "same",
                "message": "Redmine đã giống Web.",
                "check": before,
            }

        if delta < 0:
            return {
                "type": "result",
                "issue_id": issue_id,
                "spent_on": spent_on,
                "web_hours": web_hours,
                "ok": False,
                "action": "blocked_redmine_greater",
                "error": (
                    "Giờ Redmine đang lớn hơn giờ Web; không đồng bộ tự động được."
                ),
                "check": before,
            }

        res = client.post_time_entry(issue_id, spent_on, delta, activity_id)
        _log_time_entry_result(
            {
                "entry_id": f"resolve:{issue_id}:{spent_on}",
                "issue_id": issue_id,
                "spent_on": spent_on,
                "hours": delta,
                "activity_id": activity_id,
            },
            res,
        )
        if not res.ok:
            return {
                "type": "result",
                "issue_id": issue_id,
                "spent_on": spent_on,
                "web_hours": web_hours,
                "ok": False,
                "action": "create_delta_failed",
                "error": res.error_message or f"HTTP {res.status_code}",
                "status_code": res.status_code,
                "check": before,
            }

        after = _check_one(client, item)
        return {
            "type": "result",
            "issue_id": issue_id,
            "spent_on": spent_on,
            "web_hours": web_hours,
            "ok": not bool(after.get("error")),
            "action": "created_missing" if redmine_hours == 0 else "created_delta",
            "created_hours": delta,
            "message": f"Đã tạo thêm {delta:.2f}h trên Redmine.",
            "status_code": res.status_code,
            "check": after,
        }
    except Exception as e:
        app.logger.error("resolve check diff failed (%s, %s): %s", issue_id, spent_on, e)
        return {
            "type": "result",
            "issue_id": issue_id,
            "spent_on": spent_on,
            "web_hours": web_hours,
            "ok": False,
            "action": "error",
            "error": str(e),
        }


@app.route("/api/sync/check/time-entry/<entry_id>", methods=["PATCH", "DELETE"])
def mutate_redmine_time_entry(entry_id: str):
    data = request.get_json(silent=True) or {}
    api_key = data.get("apiKey")
    issue_id = str(data.get("issueId", "")).strip()
    spent_on = str(data.get("spentOn", "")).strip()
    web_hours = data.get("webHours")

    backend = app.config["REDMINE_CLIENT"]
    if backend_requires_api_key(backend) and not api_key:
        return jsonify({"error": "Vui lòng nhập khóa API"}), 400
    if not issue_id or not spent_on or web_hours is None:
        return jsonify({"error": "Thiếu issueId, spentOn hoặc webHours"}), 400

    client: AbstractRedmineTimeClient = create_redmine_time_client(
        backend,
        api_key=api_key,
    )

    if request.method == "DELETE":
        res = client.delete_time_entry(entry_id)
    else:
        try:
            hours = float(data.get("hours"))
        except (TypeError, ValueError):
            return jsonify({"error": "Giờ chỉnh sửa không hợp lệ"}), 400
        if hours < 0:
            return jsonify({"error": "Giờ chỉnh sửa không được âm"}), 400
        res = client.update_time_entry(entry_id, hours)

    if not res.ok:
        return (
            jsonify(
                {
                    "ok": False,
                    "error": res.error_message or f"HTTP {res.status_code}",
                    "status_code": res.status_code,
                }
            ),
            400,
        )

    check = _check_one(
        client,
        {
            "issue_id": issue_id,
            "spent_on": spent_on,
            "web_hours": float(web_hours),
            "activity_id": int(data.get("activityId", DEFAULT_ACTIVITY_ID)),
        },
    )
    return jsonify({"ok": True, "status_code": res.status_code, "check": check})


@app.route("/api/sync/check", methods=["POST"])
def check_redmine_diff():
    data = request.get_json(silent=True) or {}
    api_key = data.get("apiKey")
    entries: List[Dict[str, Any]] = data.get("entries", [])

    backend = app.config["REDMINE_CLIENT"]
    if backend_requires_api_key(backend) and not api_key:
        return jsonify({"error": "Vui lòng nhập khóa API"}), 400
    if not entries:
        return jsonify({"error": "Không có bản ghi để kiểm tra"}), 400

    client: AbstractRedmineTimeClient = create_redmine_time_client(
        backend,
        api_key=api_key,
    )
    items = _build_check_items(entries)
    n = len(items)
    max_workers = min(_SSE_MAX_WORKERS, max(1, n))
    output: List[Dict[str, Any]] = [None] * n # type: ignore

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        # We use a list to keep order if possible, though not strictly required by API
        # but it's nicer.
        future_to_idx = {pool.submit(_check_one, client, item): i for i, item in enumerate(items)}
        for fut in as_completed(future_to_idx):
            idx = future_to_idx[fut]
            output[idx] = fut.result()

    return jsonify({"items": output})


@app.route("/api/sync/check/user-range", methods=["POST"])
def check_redmine_diff_user_range():
    data = request.get_json(silent=True) or {}
    api_key = data.get("apiKey")
    from_date = data.get("from_date", "").strip()
    to_date = data.get("to_date", "").strip()

    backend = app.config["REDMINE_CLIENT"]
    if backend_requires_api_key(backend) and not api_key:
        return jsonify({"error": "Vui lòng nhập khóa API"}), 400
    if not from_date or not to_date:
        return jsonify({"error": "Thiếu from_date hoặc to_date"}), 400

    client: AbstractRedmineTimeClient = create_redmine_time_client(
        backend,
        api_key=api_key,
    )

    try:
        result = _check_user_range(client, from_date, to_date)
        return jsonify({"issues": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/sync/check/resolve/stream", methods=["POST"])
def resolve_redmine_check_diff_stream():
    data = request.get_json(silent=True) or {}
    api_key = data.get("apiKey")
    entries: List[Dict[str, Any]] = data.get("entries", [])

    backend = app.config["REDMINE_CLIENT"]
    if backend_requires_api_key(backend) and not api_key:
        return jsonify({"error": "Vui lòng nhập khóa API"}), 400
    if not entries:
        return jsonify({"error": "Không có bản ghi cần đồng bộ"}), 400

    items = _build_check_items(entries)

    def generate():
        client: AbstractRedmineTimeClient = create_redmine_time_client(
            backend,
            api_key=api_key,
        )
        n = len(items)
        max_workers = min(_SSE_MAX_WORKERS, max(1, n))
        success = 0
        failed = 0
        skipped = 0

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            future_map = {pool.submit(_resolve_check_diff_one, client, item): item for item in items}
            for fut in as_completed(future_map):
                result = fut.result()
                if result.get("ok"):
                    if result.get("action") == "same":
                        skipped += 1
                    else:
                        success += 1
                else:
                    failed += 1
                yield _format_sse(result)

        yield _format_sse(
            {
                "type": "done",
                "total": n,
                "success": success,
                "failed": failed,
                "skipped": skipped,
            }
        )

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.route("/api/sync/check/stream", methods=["POST"])
def check_redmine_diff_stream():
    data = request.get_json(silent=True) or {}
    api_key = data.get("apiKey")
    entries: List[Dict[str, Any]] = data.get("entries", [])

    backend = app.config["REDMINE_CLIENT"]
    if backend_requires_api_key(backend) and not api_key:
        return jsonify({"error": "Vui lòng nhập khóa API"}), 400
    if not entries:
        return jsonify({"error": "Không có bản ghi để kiểm tra"}), 400

    items = _build_check_items(entries)

    def generate():
        client: AbstractRedmineTimeClient = create_redmine_time_client(
            backend,
            api_key=api_key,
        )
        n = len(items)
        max_workers = min(_SSE_MAX_WORKERS, max(1, n))
        success = 0
        failed = 0
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            future_map = {pool.submit(_check_one, client, item): item for item in items}
            for fut in as_completed(future_map):
                result = fut.result()
                if result.get("error"):
                    failed += 1
                else:
                    success += 1
                yield _format_sse({"type": "result", **result})
        yield _format_sse(
            {
                "type": "done",
                "total": n,
                "success": success,
                "failed": failed,
            }
        )

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Redmine time entry UI")
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use MockRedmineTimeClient (no real HTTP, API key optional).",
    )
    parser.add_argument(
        "--client",
        choices=("jprep", "planio", "mock"),
        default=None,
        help="Redmine client to use. Defaults to REDMINE_CLIENT or jprep.",
    )
    args = parser.parse_args()
    if args.mock:
        app.config["REDMINE_CLIENT"] = "mock"
    elif args.client:
        app.config["REDMINE_CLIENT"] = args.client
    DEFAULT_ACTIVITY_ID = _ACTIVITY_IDS.get(app.config["REDMINE_CLIENT"], 9)
    app.run(debug=True, host="0.0.0.0", port=5001)
