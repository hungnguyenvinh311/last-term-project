# Chạy ứng dụng Electronics AI Commerce

Ứng dụng gồm backend Python/FastAPI, giao diện React/TypeScript và MySQL. Mã được tổ chức trong bốn package gốc `View`, `Controller`, `Model`, `DAO`; `bootstrap.py` ghép các lớp khi chạy. Tài liệu này hướng dẫn chuyển sang physical data model mới mà không sửa hoặc xóa schema dữ liệu cũ.

## 1. Tạo schema mới

Mở `database/004_electronics_physical_data_model.sql` trong MySQL Workbench và chạy toàn bộ script. Script tạo riêng schema `electronics_ecommerce`; nó không xóa hay sửa schema cũ.

Nếu muốn dùng tiếp danh mục sản phẩm từ schema cũ, trước tiên chạy lệnh xem trước. Lệnh mặc định chỉ đọc, không ghi dữ liệu:

```powershell
.venv-ai\Scripts\python.exe scripts\import_catalog_to_physical_schema.py `
  --source-database ecommerce_relationship_review `
  --target-database electronics_ecommerce
```

Kiểm tra `sourceProductCount`, `missingStock`, `invalidProducts` và số dòng trong target. Chỉ khi target trống, sản phẩm có giá VND hợp lệ và mỗi sản phẩm có số lượng tồn thì mới chạy nhập dữ liệu:

```powershell
.venv-ai\Scripts\python.exe scripts\import_catalog_to_physical_schema.py `
  --source-database ecommerce_relationship_review `
  --target-database electronics_ecommerce --apply
```

Lệnh nhập chỉ thêm danh mục, sản phẩm, loại sản phẩm con và tồn kho vào hai bảng trống; không xóa hoặc cập nhật schema nguồn. Số lượng tồn được đọc từ `Inventory` nguồn hoặc thuộc tính số lượng trong `technicalSpecs`. Nếu thiếu số lượng, lệnh dừng và liệt kê mã sản phẩm cần bổ sung.

Sau đó đặt `APP_DATABASE=electronics_ecommerce` trong file riêng `.env.app`. Giữ nguyên các giá trị kết nối và API key trong file; không đưa `.env.app` lên Git và không gửi khóa trong chat. Có thể chuẩn bị lại embedding bằng lệnh `scripts/prepare_embeddings.py` sau khi chọn target schema.

## 2. Cài và chạy

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-app.txt -r requirements-ai.txt
cd View
npm.cmd ci
npm.cmd run build
cd ..
.venv\Scripts\python.exe -m uvicorn bootstrap:app --host 127.0.0.1 --port 8008
```

Mở **http://127.0.0.1:8008**. Tài liệu API ở **http://127.0.0.1:8008/docs** và health check ở **http://127.0.0.1:8008/api/health**. Nếu đã cài `.venv-ai`, có thể thay `.venv\Scripts\python.exe` bằng `.venv-ai\Scripts\python.exe`.

Đăng ký customer từ giao diện. Tạo tài khoản Admin đầu tiên bằng lệnh cục bộ sau; mật khẩu được nhập ẩn trong terminal:

```powershell
.venv\Scripts\python.exe scripts\create_staff.py
```

Lệnh cho chọn một trong bốn vai trò. Sau khi có Admin, tạo các tài khoản nhân viên còn lại trong màn hình quản trị tài khoản.

## 3. Chức năng theo vai trò

- **Customer:** tìm kiếm văn bản/giọng nói/hình ảnh, lọc theo loại/brand/giá/tồn kho, xem sản phẩm tương tự, so sánh, quản lý giỏ, checkout, xem hóa đơn và đơn hàng, xác nhận đã nhận hàng.
- **Admin:** quản lý sản phẩm và danh mục, tài khoản và vai trò, báo cáo, nghiệp vụ thanh toán/đơn, nhập và điều chỉnh tồn.
- **Sales Staff:** xem đơn, ghi nhận kết quả kiểm tra chuyển khoản và xác nhận COD sau giao hàng.
- **Warehouse Staff:** nhập/điều chỉnh tồn và chuyển trạng thái đóng gói, bàn giao vận chuyển mô phỏng.
- **Manager:** xem báo cáo doanh số và tồn kho, lọc theo ngày, loại sản phẩm và brand, tải CSV/PDF.

Thanh toán và vận chuyển là luồng mô phỏng trong ứng dụng. Hệ thống không gọi ngân hàng hay đơn vị giao nhận thật. Schema hiện lưu số điện thoại trong hồ sơ User, không có trường snapshot số điện thoại riêng cho từng Order.

## 4. Kiểm tra

```powershell
.venv\Scripts\python.exe -m pytest tests/unit -q -p no:cacheprovider
cd View
npm.cmd --prefix . run build
```

Kiểm thử MySQL đầu-cuối cần một schema test riêng và cấu hình kết nối tương ứng. Không chạy các kiểm thử này trên schema đang dùng thật.
