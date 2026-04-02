# Tài Liệu Dự Án: Time Log Viewer (Redmine Integration)

Tài liệu này mô tả chi tiết về sản phẩm, câu chuyện người dùng (User Story), thiết kế cơ bản (Basic Design) và thiết kế chi tiết (Detailed Design) của ứng dụng Time Log Viewer dựa trên mã nguồn hiện tại.

---

## 1. Product Requirements Document (PRD)

### 1.1. Tổng quan sản phẩm (Product Overview)
**Time Log Viewer** là một ứng dụng (được xây dựng bằng Flutter) giúp người dùng (đặc biệt là lập trình viên, quản lý dự án) dễ dàng nhập (import) lịch sử làm việc từ file CSV, xem dưới dạng bảng ma trận (Task x Ngày), chỉnh sửa trực tiếp và tự động đồng bộ (bulk upload) dữ liệu thời gian làm việc (time entries) lên hệ thống quản lý dự án Redmine thông qua API.

### 1.2. Mục tiêu (Objectives)
- Giảm thiểu thời gian nhập liệu thủ công lên hệ thống Redmine.
- Cung cấp giao diện trực quan (bảng 2D) để rà soát, kiểm tra chéo số giờ làm việc theo từng ngày và từng task.
- Cho phép chỉnh sửa linh hoạt (thêm/sửa/xóa task và giờ làm việc) trước khi gửi dữ liệu chính thức.

### 1.3. Tính năng chính (Key Features)
1. **Import CSV**: Đọc và phân tích (parse) file CSV chứa thông tin thành viên, vai trò, tổng số giờ và chi tiết từng task theo ngày.
2. **Hiển thị Bảng 2D (Matrix View)**: Hiển thị danh sách task ở cột cố định (pinned column) và các ngày làm việc ở hàng ngang (pinned row) giống Excel.
3. **Quản lý Task**: Thêm task mới, sửa thông tin task (ID, Tên, URL), xóa task.
4. **Quản lý Giờ làm việc (Time Entry)**: Click vào từng ô trong bảng để nhập/sửa/xóa số giờ làm việc của một task trong một ngày cụ thể.
5. **Đồng bộ Redmine (API Integration)**: Nhập API Key của Redmine và gửi hàng loạt (bulk create) dữ liệu time entry lên server.
6. **Summary Bar**: Hiển thị tóm tắt thông tin người dùng, vai trò, tổng số giờ và tổng số task.

### 1.4. Yêu cầu phi chức năng (Non-Functional Requirements)
- **Hiệu năng**: Bảng 2D phải cuộn mượt mà ngay cả khi có nhiều task và nhiều ngày (sử dụng `two_dimensional_scrollables`).
- **Xử lý lỗi**: Báo lỗi rõ ràng khi file CSV sai định dạng hoặc khi gọi API Redmine thất bại.
- **Bảo mật**: API Key không được lưu trữ vĩnh viễn (chỉ nhập khi cần gửi) để tránh lộ lọt thông tin.

---

## 2. User Stories

Dưới đây là các câu chuyện người dùng mô tả nhu cầu thực tế khi sử dụng hệ thống:

- **US01 - Import CSV**: Là một nhân viên, tôi muốn tải lên file CSV chứa log time của mình để hệ thống tự động đọc và hiển thị dữ liệu mà không cần tôi nhập tay lại từ đầu.
- **US02 - Xem dữ liệu dạng bảng**: Là một nhân viên, tôi muốn xem dữ liệu log time dưới dạng bảng (các task ở cột trái, các ngày ở hàng trên cùng) để dễ dàng đối chiếu số giờ làm việc mỗi ngày.
- **US03 - Chỉnh sửa giờ làm việc**: Là một nhân viên, tôi muốn click vào một ô bất kỳ trong bảng để sửa/thêm/xóa số giờ làm việc, giúp tôi sửa các sai sót trong file CSV gốc.
- **US04 - Quản lý Task**: Là một nhân viên, tôi muốn thêm một task mới bị thiếu, hoặc xóa một task thừa, hoặc sửa ID/URL của task để đảm bảo dữ liệu map đúng với Redmine.
- **US05 - Mở link Task**: Là một nhân viên, tôi muốn click vào URL của task trong bảng để mở trình duyệt xem chi tiết task đó trên Redmine.
- **US06 - Gửi dữ liệu lên Redmine**: Là một nhân viên, tôi muốn nhập API Key và nhấn nút "Send", hệ thống sẽ tự động tạo time entries cho tất cả các task có số giờ > 0 lên Redmine, giúp tôi tiết kiệm thời gian nhập liệu từng dòng.
- **US07 - Xem tổng quan**: Là một nhân viên, tôi muốn xem thanh tóm tắt (Summary Bar) hiển thị tên tôi, tổng số giờ đã log và tổng số task để kiểm tra nhanh xem mình đã log đủ giờ trong tháng chưa.

---

## 3. Basic Design (Thiết kế cơ bản)

### 3.1. Kiến trúc tổng thể (Architecture)
Ứng dụng áp dụng kiến trúc **Feature-based** kết hợp với **BLoC Pattern** để quản lý trạng thái.
- **UI Layer**: Các Widget của Flutter, sử dụng `two_dimensional_scrollables` cho bảng phức tạp.
- **Business Logic Layer**: `CsvBloc` xử lý các sự kiện từ UI (import, edit, delete) và cập nhật `CsvState`.
- **Data/Repository Layer**: `TimeEntryRepository` chịu trách nhiệm giao tiếp với API bên ngoài (Redmine) thông qua thư viện `Dio`. `CsvParser` chịu trách nhiệm xử lý logic parse text.

### 3.2. Cấu trúc thư mục (Directory Structure)
```text
lib/
├── main.dart
├── features/
│   ├── csv/
│   │   ├── bloc/ (csv_bloc.dart, csv_event.dart, csv_state.dart)
│   │   ├── models/ (csv_model.dart)
│   │   ├── screens/ (csv_screen.dart)
│   │   └── utils/ (csv_parser.dart)
│   └── time_entry/
│       ├── models/ (time_entry_request.dart)
│       └── repositories/ (time_entry_repository.dart)
```

### 3.3. Luồng dữ liệu chính (Data Flow)
1. **Luồng Import**: User click "Import CSV" -> `FilePicker` mở -> Trả về bytes -> `CsvParser` phân tích text -> Tạo ra `ParsedData` -> `CsvBloc` emit state `loaded` -> UI render bảng.
2. **Luồng Edit**: User click ô bảng -> Nhập số giờ -> `CsvBloc` nhận event `EditDayEntry` -> Cập nhật `TaskEntry` trong State -> UI re-render ô đó.
3. **Luồng Sync API**: User click "Send API" -> Nhập API Key -> UI gom toàn bộ `TaskEntry` có giờ > 0 tạo thành danh sách `TimeEntryRequest` -> Gọi `TimeEntryRepository.createMultipleTimeEntries` -> Nhận response thành công/thất bại -> Hiển thị SnackBar.

---

## 4. Detailed Design (Thiết kế chi tiết)

### 4.1. Data Models
- **`DayEntry`**: Lưu trữ ngày (`String date`) và số giờ làm việc (`double hours`).
- **`TaskEntry`**: Đại diện cho 1 hàng trong bảng. Gồm `taskId`, `taskName`, `taskUrl`, và danh sách `dayEntries`. Có getter `totalHours` để tính tổng giờ của task.
- **`ParsedData`**: Chứa thông tin header của CSV (`memberName`, `role`, `effortSum`) và danh sách `tasks`.
- **`TimeEntryRequest`**: Model để serialize thành JSON gửi lên Redmine API. Bao gồm `issue_id`, `spent_on`, `hours`, `activity_id` (mặc định = 9 - Development), `comments` (tên task).

### 4.2. State Management (CSV BLoC)
- **Events**:
  - `_PickFileEvent`: Kích hoạt chọn file.
  - `_AddTaskEvent`, `_DeleteTaskEvent`, `_EditTaskEvent`: CRUD cho hàng (Task).
  - `_AddDayEntryEvent`, `_EditDayEntryEvent`, `_DeleteDayEntryEvent`: CRUD cho ô (Giờ làm việc trong ngày).
- **State (`CsvState`)**:
  - `status`: `initial`, `loading`, `loaded`, `error`.
  - `data`: Chứa `ParsedData` gốc (header info).
  - `tasks`: Danh sách `TaskEntry` hiện tại (có thể bị thay đổi so với gốc do user edit).
  - `errorMessage`: Chuỗi thông báo lỗi nếu có.

### 4.3. UI Components (`CsvScreen`)
- **`_EmptyView`**: Hiển thị khi chưa có file nào được chọn. Nút Import to ở giữa màn hình.
- **`_ErrorView`**: Hiển thị khi parse lỗi hoặc đọc file lỗi.
- **`_ContentView`**: Chứa giao diện chính khi đã có dữ liệu.
  - Sử dụng `TableView.builder` từ package `two_dimensional_scrollables`.
  - **Pinned Column (Cột 0)**: Chứa thông tin Task (`_TaskInfoCell`). Hiển thị ID, Tên, URL, Tổng giờ của task và các nút Edit/Delete task.
  - **Pinned Row (Hàng 0)**: Chứa thông tin Ngày tháng. Tự động highlight màu đỏ nhạt cho ngày cuối tuần (Thứ 7, Chủ Nhật).
  - **Cells (Các ô giao điểm)**: Hiển thị số giờ. Khi click vào sẽ biến thành `TextField` để nhập liệu. FocusNode được sử dụng để tự động lưu (save) khi user click ra ngoài ô (onFocusChange).
- **`_SummaryBar`**: Thanh ngang ở trên cùng hiển thị Tên, Role, Tổng giờ, Tổng số task.

### 4.4. Utilities & Services
- **`CsvParser`**:
  - Đọc file CSV theo từng dòng (sử dụng `csv` package).
  - Tìm dòng Header ("No") để xác định danh sách các ngày.
  - Bỏ qua các dòng không cần thiết, map các cột dữ liệu vào `TaskEntry` và `DayEntry`.
  - Hàm `_extractTaskIdFromUrl`: Dùng Regex `r'/(\d+)$'` để lấy Issue ID từ link Redmine.
  - Hàm `_formatDateWithCurrentYear`: Xử lý các định dạng ngày tháng thiếu năm (VD: "12/05" -> "YYYY/12/05").
- **`TimeEntryRepository`**:
  - Sử dụng `Dio` cấu hình header `X-Redmine-API-Key` và `Content-Type: application/json`.
  - Hàm `createMultipleTimeEntries`: Lặp qua danh sách request, gọi API `POST /time_entries.json`. Gom các lỗi lại (nếu có task gửi xịt) và throw Exception tổng hợp ở cuối quá trình để UI hiển thị.

### 4.5. API Integration Details
- **Endpoint**: `POST https://redmine.jprep.jp/redmine/time_entries.json`
- **Headers**:
  - `Content-Type`: `application/json`
  - `X-Redmine-API-Key`: `<User_Input_Key>`
- **Payload Format**:
  ```json
  {
    "time_entry": {
      "issue_id": 12345,
      "spent_on": "2023-10-25",
      "hours": 4.5,
      "activity_id": 9,
      "comments": "Task Name"
    }
  }
  ```

---
*Tài liệu được tạo tự động dựa trên cấu trúc mã nguồn hiện tại của dự án.*