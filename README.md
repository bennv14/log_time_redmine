# Redmine Time Logger

Ứng dụng web **Flask** để nhập timesheet từ **CSV**, chỉnh sửa ma trận công việc × ngày, rồi gửi **time entry** lên Redmine qua REST API. Luồng đồng bộ dùng **Server-Sent Events (SSE)**; server xử lý song song các entry (ThreadPoolExecutor, tối đa 8 worker).

## Yêu cầu

- Python 3.9+
- Trình duyệt hỗ trợ `fetch` và đọc `ReadableStream` (SSE)

Phụ thuộc chính: xem [`requirements.txt`](requirements.txt) (Flask, Flask-Cors, requests; còn có pandas trong file nhưng mã nguồn hiện **không** import pandas).

## Cài đặt

```bash
cd log_time_redmine
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
```

`pip install -e .` cài package [`redmine_time_client`](redmine_time_client/) (metadata trong [`pyproject.toml`](pyproject.toml), [`setup.py`](setup.py) gọi `setuptools.setup()`).

## Chạy ứng dụng

```bash
flask --app app run --debug --host 0.0.0.0 --port 5000
```

Hoặc:

```bash
python app.py
```

Mở `http://127.0.0.1:5000/`.

### Chế độ mock (không gọi Redmine thật)

- Biến môi trường: `REDMINE_MOCK` = `1`, `true`, hoặc `yes` (không phân biệt hoa thường, bỏ qua khoảng trắng đầu/cuối) → backend `mock`; API key không bắt buộc trên server.
- Hoặc: `python app.py --mock` (ghi đè config thành mock khi khởi chạy trực tiếp `app.py`).

`MockRedmineTimeClient` luôn trả thành công (HTTP 201, payload JSON giả).

**Lưu ý:** Form trên giao diện vẫn yêu cầu nhập API key trước khi bấm đồng bộ; với mock, server không kiểm tra key nhưng client có thể gửi chuỗi bất kỳ.

## Cấu trúc thư mục (chính)

| Path | Mô tả |
|------|--------|
| [`app.py`](app.py) | Flask: CORS, parse CSV `/api/upload`, SSE `/api/sync/stream`, ghi log kết quả từng entry |
| [`redmine_time_client/`](redmine_time_client/) | Client trừu tượng + HTTP + mock + factory chọn backend từ env |
| [`templates/index.html`](templates/index.html) | Giao diện Bootstrap 5, Google Fonts, modal thêm/sửa task |
| [`static/js/app.js`](static/js/app.js) | Ma trận giờ, upload CSV, SSE, bảng kết quả, retry bản lỗi |
| [`static/css/style.css`](static/css/style.css) | Style tùy chỉnh |
| [`tests/`](tests/) | Unit test: HTTP client (mock `requests`), mock client, factory / env |
| [`logs/`](logs/) | `redmine_time_entry.log` (JSON mỗi dòng; thư mục có `.gitkeep`, nội dung log thường bị `.gitignore`) |

## Định dạng CSV (server)

- Phải có hàng header chứa cột tên **`No`** (không phân biệt hoa thường).
- Phía trên header: các dòng metadata — tìm ô có nhãn gợi ý **tên / thành viên / member** và **role / vai trò** để điền `memberName`, `role`.
- Cột ngày: header khớp mẫu `M/D` hoặc `MM/DD` (ví dụ `4/25`) → server gắn **năm hiện tại** thành `YYYY-MM-DD`.
- Từng dòng task sau header: cột `No`, tiếp theo **tên task**, **URL task**; issue id suy ra từ **số cuối đường dẫn** URL (regex `/(\d+)$`). Dòng `Sum` hoặc dòng trống `No` bị bỏ qua.
- Ô ngày: số giờ (float); ô rỗng hoặc không parse được → 0.

## Giao diện (client)

- Lần đầu tải trang: cột ngày theo **tháng hiện tại** (đủ ngày trong tháng).
- Sau khi upload CSV thành công: `appState` thay bằng JSON server → cột ngày theo **CSV**.
- Thêm / sửa / xóa hàng task; nhập giờ theo từng ô; **activity_id** gửi lên mặc định **9** (hằng `DEFAULT_ACTIVITY_ID` ở server và client).
- Mỗi ô có giờ &gt; 0 khi đồng bộ tạo một entry riêng; `entry_id` do trình duyệt tạo (`crypto.randomUUID()`).

## Package `redmine_time_client`

| Thành phần | Vai trò |
|------------|---------|
| `AbstractRedmineTimeClient` | Contract `post_time_entry(issue_id, spent_on, hours, activity_id)` |
| `TimeEntryResult` | `ok`, `status_code`, `error_message`, `response_text` |
| `HttpRedmineTimeClient` | `requests.post` JSON tới `{base}{path}`; base mặc định `https://redmine.jprep.jp`, path mặc định `/redmine/time_entries.json`; header `X-Redmine-API-Key` |
| `MockRedmineTimeClient` | Không HTTP; luôn OK |
| `parse_redmine_backend_from_env` / `create_redmine_time_client` / `backend_requires_api_key` | Chọn `http` vs `mock` |

Đổi server Redmine: sửa hằng trong [`redmine_time_client/http.py`](redmine_time_client/http.py) (`DEFAULT_REDMINE_BASE_URL`, `DEFAULT_TIME_ENTRIES_PATH`) hoặc mở rộng code nếu cần cấu hình động.

## API HTTP

| Method | Path | Mô tả |
|--------|------|--------|
| `GET` | `/` | Trang UI |
| `POST` | `/api/upload` | `multipart/form-data`, field `file` (CSV UTF-8). Trả JSON: `memberName`, `role`, `effortSum`, `tasks[]` (`taskId`, `taskName`, `taskUrl`, `dayEntries` map ngày → giờ, `totalHours`), `dates[]` |
| `POST` | `/api/sync/stream` | JSON `{"apiKey": "...", "entries": [...]}`. Mỗi entry: `entry_id` (bắt buộc), `issue_id`, `spent_on` (`YYYY-MM-DD`), `hours`, `activity_id` (tùy chọn, mặc định server **9**). Trả `text/event-stream` (SSE): nhiều sự kiện `type: "result"`, cuối cùng `type: "done"` với `total`, `success`, `failed` |

Phản hồi lỗi 400 thường là JSON `{ "error": "..." }` (không phải SSE).

## Ghi log server

Logger `app.time_entry` ghi file [`logs/redmine_time_entry.log`](logs/redmine_time_entry.log): mỗi dòng một object JSON (entry + `ok`, `status_code`, `error`, `response_text`).

## Chạy test

```bash
python3 -m unittest discover -s tests -p "test_*.py" -v
```

Cần đã cài `requests` và package editable như trên.

## Triển khai / reverse proxy (SSE)

Đặt sau Nginx hoặc proxy tương tự: tắt buffering cho route SSE, ví dụ:

```nginx
proxy_buffering off;
proxy_cache off;
```

Ứng dụng đã gửi header `X-Accel-Buffering: no` trên response SSE.

## Tài liệu thêm

- [`docs/PROJECT_DOCUMENTATION.md`](docs/PROJECT_DOCUMENTATION.md) — bối cảnh sản phẩm (một phần có thể mô tả stack cũ; code chạy là Flask + JS).

## License

Chưa khai báo. Thêm file license nếu công khai repo.
