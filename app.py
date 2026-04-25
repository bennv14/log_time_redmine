import argparse
import csv
import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

from flask import Flask, Response, jsonify, render_template, request, stream_with_context
from flask_cors import CORS

from redmine_time_client import (
    AbstractRedmineTimeClient,
    TimeEntryResult,
    backend_requires_api_key,
    create_redmine_time_client,
    parse_redmine_backend_from_env,
)

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)

DEFAULT_ACTIVITY_ID = 9


def _apply_redmine_backend_config(flask_app: Flask) -> None:
    """Resolve REDMINE_MOCK once per process; set REDMINE_BACKEND on app config."""
    flask_app.config["REDMINE_BACKEND"] = parse_redmine_backend_from_env()


_apply_redmine_backend_config(app)

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
    return render_template('index.html')

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
            
            # Extract basic info (assuming it's above the header)
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
            
            header_row = lines[header_idx]
            # Find date columns (usually after Task URL / Task Name)
            date_cols = []
            for j in range(len(header_row)):
                col_name = header_row[j].strip()
                if re.match(r'\d{1,2}/\d{1,2}', col_name):
                    date_cols.append({"index": j, "date": format_date_with_current_year(col_name), "raw": col_name})
            
            parsed_data["dates"] = [d["date"] for d in date_cols]
            
            # Parse tasks
            for i in range(header_idx + 1, len(lines)):
                row = lines[i]
                if not row or len(row) <= no_idx or not row[no_idx].strip():
                    continue
                
                if row[no_idx].strip().lower() == "sum":
                    continue
                
                # Assuming columns: No, Task Name, Task URL, ... dates ...
                task_name = row[no_idx + 1].strip() if len(row) > no_idx + 1 else ""
                task_url = row[no_idx + 2].strip() if len(row) > no_idx + 2 else ""
                task_id = extract_task_id(task_url)
                
                day_entries = {}
                task_total = 0.0
                
                for d in date_cols:
                    if d["index"] < len(row):
                        val = row[d["index"]].strip()
                        try:
                            hours = float(val) if val else 0.0
                        except ValueError:
                            hours = 0.0
                        day_entries[d["date"]] = hours
                        task_total += hours
                
                parsed_data["tasks"].append({
                    "id": str(task_id) if task_id else f"temp_{i}",
                    "taskId": task_id,
                    "taskName": task_name,
                    "taskUrl": task_url,
                    "dayEntries": day_entries,
                    "totalHours": task_total
                })
                parsed_data["effortSum"] += task_total
                
            return jsonify(parsed_data)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

_SSE_MAX_WORKERS = 8


def _format_sse(data: Dict[str, Any]) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def _post_one(
    client: AbstractRedmineTimeClient, entry: Dict[str, Any]
) -> Tuple[str, Dict[str, Any], TimeEntryResult]:
    eid = str(entry.get("entry_id", ""))
    try:
        issue = entry.get("issue_id")
        spent = entry.get("spent_on")
        hours = float(entry.get("hours", 0))
        act = int(entry.get("activity_id", DEFAULT_ACTIVITY_ID))
        res = client.post_time_entry(issue, str(spent), hours, act)
        _log_time_entry_result(entry, res)
        return eid, entry, res
    except Exception as e:
        app.logger.error("entry task failed: %s", e)
        res = TimeEntryResult(ok=False, error_message=str(e))
        _log_time_entry_result(entry, res)
        return eid, entry, res


@app.route("/api/sync/stream", methods=["POST"])
def sync_redmine_stream():
    data = request.get_json(silent=True) or {}
    api_key = data.get("apiKey")
    entries: List[Dict[str, Any]] = data.get("entries", [])

    backend = app.config["REDMINE_BACKEND"]
    if backend_requires_api_key(backend) and not api_key:
        return jsonify({"error": "Vui lòng nhập khóa API"}), 400
    if not entries:
        return jsonify({"error": "Không có bản ghi cần đồng bộ"}), 400
    for e in entries:
        if not e.get("entry_id"):
            return jsonify({"error": "Mỗi entry cần có entry_id (định danh ổn định từ client)"}), 400

    def generate():
        client: AbstractRedmineTimeClient = create_redmine_time_client(
            backend,
            api_key=api_key,
        )
        n = len(entries)
        max_workers = min(_SSE_MAX_WORKERS, max(1, n))
        success = 0
        failed = 0
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            future_map = {pool.submit(_post_one, client, e): e for e in entries}
            for fut in as_completed(future_map):
                eid, orig, res = fut.result()
                if res.ok:
                    success += 1
                else:
                    failed += 1
                yield _format_sse(
                    {
                        "type": "result",
                        "entry_id": eid,
                        "issue_id": orig.get("issue_id"),
                        "spent_on": orig.get("spent_on"),
                        "hours": orig.get("hours"),
                        "ok": res.ok,
                        "status_code": res.status_code,
                        "error": res.error_message,
                    }
                )
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
    args = parser.parse_args()
    if args.mock:
        app.config["REDMINE_BACKEND"] = "mock"
    app.run(debug=True, host="0.0.0.0", port=5001)
