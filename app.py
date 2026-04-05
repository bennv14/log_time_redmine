import os
import csv
import re
import logging
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)

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

@app.route('/api/sync', methods=['POST'])
def sync_redmine():
    data = request.json
    api_key = data.get('apiKey')
    entries = data.get('entries', [])
    logging.info(f"API Key: {api_key}")
    logging.info(f"Entries: {entries}")
    
    if not api_key:
        return jsonify({"error": "Vui lòng nhập khóa API"}), 400
    
    headers = {
        "Content-Type": "application/json",
        "X-Redmine-API-Key": api_key
    }
    
    success_count = 0
    errors = []
    
    for entry in entries:
        payload = {
            "time_entry": {
                "issue_id": entry.get("issue_id"),
                "spent_on": entry.get("spent_on"),
                "hours": entry.get("hours"),
                "activity_id": 9,
            }
        }
        
        url = "https://redmine.jprep.jp/redmine/time_entries.json"
        app.logger.info(f"Sending request to {url} with payload: {payload}")
        
        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=15
            )
            app.logger.info(f"Response status: {response.status_code}, body: {response.text}")
            if response.status_code in (200, 201):
                success_count += 1
            else:
                errors.append(f"Task {entry.get('issue_id')} on {entry.get('spent_on')}: {response.text}")
        except Exception as e:
            app.logger.error(f"Request failed: {str(e)}")
            errors.append(f"Task {entry.get('issue_id')} on {entry.get('spent_on')}: {str(e)}")
            
    if errors:
        return jsonify({
            "status": "partial_success" if success_count > 0 else "error",
            "success_count": success_count,
            "errors": errors
        }), 207 if success_count > 0 else 400
        
    return jsonify({"status": "success", "success_count": success_count})

if __name__ == '__main__':
    app.run(debug=True, host = '0.0.0.0', port=5000)
