# Electronics AI Commerce

Ứng dụng thương mại điện tử cho sản phẩm điện tử tiêu dùng, gồm tìm kiếm AI, gợi ý sản phẩm tương tự, giỏ hàng, checkout, tồn kho và thanh toán/giao hàng mô phỏng. Backend dùng Python/FastAPI, giao diện React/TypeScript và cơ sở dữ liệu MySQL. Mã được tổ chức theo các package `View`, `Controller`, `Model`, `DAO`.

## Chạy dự án trên Windows

Các lệnh dưới đây chạy trong PowerShell. Thư mục làm việc là `Last term Project\Chương 4\e-commerce system`.

### 1. Cài dependencies (bỏ qua nếu đã cài)

```powershell
py -m venv .venv-ai
.\.venv-ai\Scripts\python.exe -m pip install --upgrade pip
.\.venv-ai\Scripts\python.exe -m pip install -r requirements-app.txt -r requirements-ai.txt
cd View
npm.cmd ci
cd ..
```

Nếu `.venv-ai` và `View\node_modules` đã có sẵn, bỏ qua bước này. Trong PowerShell dùng `npm.cmd` để tránh lỗi execution policy với `npm.ps1`.

### 2. Tạo schema và cấu hình kết nối

Đảm bảo dịch vụ MySQL đang chạy. Mở [`database/004_electronics_physical_data_model.sql`](database/004_electronics_physical_data_model.sql) trong MySQL Workbench và chạy toàn bộ script. Script tạo schema riêng `electronics_ecommerce`, không xóa schema cũ. Tài khoản MySQL cần quyền tạo database và bảng.

Ứng dụng đọc thông tin kết nối (`MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`) từ `.env`; tên schema ứng dụng đọc từ `.env.app`. Điền thông tin kết nối cục bộ trong `.env` và kiểm tra `.env.app` có:

```dotenv
APP_DATABASE=electronics_ecommerce
```

Voice search và trích xuất điều kiện bằng Gemini cần `APP_GEMINI_API_KEY` được điền riêng trong `.env.app`. Text search có thể dùng bộ phân tích theo quy tắc khi chưa cấu hình Gemini; voice search cần Gemini hoạt động. Không chép mật khẩu/API key vào README hoặc Git, và không gửi key qua chat.

### 3. Chuẩn bị sản phẩm (nếu schema mới chưa có dữ liệu)

Có thể chuyển danh mục từ schema cũ. Trước hết xem tên schema nguồn trong MySQL Workbench, rồi chạy **preview** (chỉ đọc, không ghi dữ liệu). Thay `TEN_SCHEMA_NGUON` bằng tên schema thật có bảng `Products` và `Categories`:

```powershell
.\.venv-ai\Scripts\python.exe scripts\import_catalog_to_physical_schema.py `
  --source-database TEN_SCHEMA_NGUON `
  --target-database electronics_ecommerce
```

Chỉ khi preview hợp lệ và schema đích còn trống mới chạy lại lệnh trên với `--apply` ở cuối để nhập sản phẩm. Công cụ không xóa hay cập nhật schema nguồn. Nếu ảnh và nội dung sản phẩm chưa có embedding tương thích, sau khi nhập hãy chạy:

```powershell
.\.venv-ai\Scripts\python.exe scripts\prepare_embeddings.py
```

Lệnh tạo embedding cần ảnh tồn tại tại đường dẫn lưu trong database; lần đầu có thể tải model xuống máy. Xem thêm [`docs/application_setup.md`](docs/application_setup.md).

### 4. Tạo tài khoản nhân viên đầu tiên

Sau khi schema và kết nối database đã sẵn sàng, chạy từ thư mục dự án. Lệnh hỏi email, tên, mật khẩu và vai trò; mật khẩu được nhập ẩn:

```powershell
.\.venv-ai\Scripts\python.exe scripts\create_staff.py
```

Chọn `Admin` cho tài khoản quản trị đầu tiên. Khách hàng đăng ký trên giao diện; Admin có thể tạo các tài khoản nhân viên tiếp theo và chọn vai trò.

### 5. Khởi động backend và giao diện

Mở **hai cửa sổ PowerShell** tại thư mục `e-commerce system`.

Cửa sổ thứ nhất — backend:

```powershell
.\.venv-ai\Scripts\python.exe -m uvicorn bootstrap:app --host 127.0.0.1 --port 8008
```

Cửa sổ thứ hai — giao diện phát triển:

```powershell
cd View
npm.cmd run dev
```

Mở giao diện tại **http://127.0.0.1:5174**. API và tài liệu tương tác ở **http://127.0.0.1:8008/docs**. Health check tại **http://127.0.0.1:8008/api/health** phải trả trạng thái `ok`.

Để chạy giao diện đã build cùng backend: trong `View`, chạy `npm.cmd run build`, sau đó khởi động backend và mở **http://127.0.0.1:8008**.

## Vai trò trong ứng dụng

- **Customer:** tìm kiếm text/voice/image, lọc và so sánh sản phẩm, xem gợi ý tương tự, quản lý giỏ, đặt hàng, xem hóa đơn và xác nhận đã nhận hàng.
- **Admin:** quản lý danh mục, sản phẩm, tài khoản/vai trò, tồn kho và nghiệp vụ quản trị.
- **Sales Staff:** xử lý đơn và ghi nhận kết quả thanh toán mô phỏng theo quyền được cấp.
- **Warehouse Staff:** nhập/điều chỉnh tồn, đóng gói và bàn giao đơn cho đơn vị vận chuyển mô phỏng.
- **Manager:** xem và xuất báo cáo doanh số, tồn kho.

Thanh toán và vận chuyển được mô phỏng; ứng dụng không kết nối ngân hàng hoặc đơn vị giao nhận thật.

## Kiểm tra code

Từ thư mục dự án, chạy unit tests:

```powershell
.\.venv-ai\Scripts\python.exe -m pytest tests\unit -q -p no:cacheprovider
```

Kiểm tra cú pháp Python và build giao diện:

```powershell
.\.venv-ai\Scripts\python.exe -m compileall -q DAO Controller Model scripts bootstrap.py
cd View
npm.cmd run build
cd ..
```

## Tài liệu liên quan

- [`docs/application_setup.md`](docs/application_setup.md): cấu hình schema, chuyển dữ liệu và tạo tài khoản.
- [`docs/gemini_setup.md`](docs/gemini_setup.md): cấu hình Gemini cho voice search và phân tích ý định.
- [`docs/implementation_plan.md`](docs/implementation_plan.md): trạng thái triển khai và các hạng mục nghiệm thu.
- [`docs/commerce_acceptance.md`](docs/commerce_acceptance.md): kịch bản nghiệm thu theo vai trò.
- [`database/README.md`](database/README.md): các schema SQL và mục đích sử dụng.
- [`docs/setup_and_validation.md`](docs/setup_and_validation.md): quy trình thu thập và kiểm tra catalogue.
