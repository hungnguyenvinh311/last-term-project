# Kế hoạch và trạng thái triển khai — Electronics E-Commerce

Cập nhật: 17/11/2026. Đây là trạng thái hiện hành của lần tái tổ chức code theo Physical Data Model trong `Minor thesis`. Sơ đồ package chưa sửa; sẽ đối chiếu lại sau khi luồng code và nghiệm thu database hoàn tất.

## Nguyên tắc

- Bốn package gốc: `View`, `Controller`, `Model`, `DAO`; `bootstrap.py` lắp ráp dependency.
- DAO truy vấn schema mới `electronics_ecommerce`, được tạo bởi `database/004_electronics_physical_data_model.sql`. Không thêm bảng/cột ngoài ERD.
- Schema cũ và source catalogue không bị xóa hoặc cập nhật. Chuyển danh mục sang schema mới chỉ qua script preview; ghi dữ liệu yêu cầu cờ `--apply` và target phải trống.
- Payment/shipping là mô phỏng. Không triển khai serial/IMEI, voucher, review, hoàn tiền thật hay API đối tác.

## Công việc đã triển khai trong code

| Nhóm | Nội dung chính | Tình trạng |
|---|---|---|
| Cấu hình/schema | Tách database đích, thêm `CREATE DATABASE` vào SQL, chặn app dùng ba schema cũ | Đã làm; chưa chạy SQL trên MySQL |
| Tài khoản/phân quyền | User/Customer/Employee/Account/AuthSession; Admin, Sales Staff, Warehouse Staff, Manager; giới hạn API và màn hình theo role | Đã làm |
| Danh mục/sản phẩm | CRUD theo thuộc tính vật lý; subtype điện tử; mô tả được lưu trong `technicalSpecs`; log admin qua AuditLog | Đã làm |
| Search/Recommendation | DAO theo schema mới; text/voice/image, lọc brand/giá/loại/tồn; lịch sử search; gợi ý cùng loại còn hàng | Đã làm trong code; cần nghiệm thu trên dữ liệu mới |
| Cart/checkout | Kiểm tra giá/tồn trong transaction; snapshot OrderItem, invoice, payment; giữ/phân bổ tồn | Đã làm |
| Kho/giao hàng | Receipt, adjustment, StockMovement; hold hết hạn; xuất kho khi dispatch; khách xác nhận đã nhận | Đã làm |
| Thanh toán | Nhân viên ghi nhận kết quả online/COD, PaymentEvent có idempotency; QR là hướng dẫn chuyển khoản tĩnh | Đã làm, mô phỏng |
| Báo cáo | Sales/inventory theo ngày, brand, loại; CSV/PDF; chỉ doanh số đã thanh toán | Đã làm |
| Nghiệm thu | Unit tests, TypeScript, compile/import backend | Đã chạy; chi tiết bên dưới |

Các điểm schema được ánh xạ rõ: số điện thoại nhận đơn lấy từ User hiện tại vì Order không có snapshot riêng; mô tả sản phẩm được đặt trong `technicalSpecs` vì không có cột description. Không tuyên bố các giá trị này là snapshot độc lập.

## Việc còn lại trước nghiệm thu hoàn chỉnh

1. Chạy `database/004_electronics_physical_data_model.sql` trong MySQL Workbench để tạo database mới.
2. Chạy `scripts/import_catalog_to_physical_schema.py` ở chế độ preview; xác nhận source, target, số lượng tồn và ảnh. Chỉ chạy `--apply` khi preview hợp lệ.
3. Đặt `APP_DATABASE=electronics_ecommerce` trong `.env.app` (đã cập nhật riêng mục này), chuẩn bị lại embedding nếu thiếu/khác model, rồi chạy ứng dụng.
4. Chạy kiểm thử MySQL trên database test riêng và nghiệm thu bằng các role. Không dùng database nghiệp vụ hiện tại làm test.
5. Khi code và nghiệm thu đã khớp, cập nhật package diagram trong Visual Paradigm theo cấu trúc thực tế.

## Kết quả kiểm tra hiện tại

- `193` unit tests passed; `6` test dùng thư mục tạm bị Windows từ chối quyền truy cập (`WinError 5`) nên đã loại khỏi lượt kiểm tra sạch. Không có assertion failure trong các test đã chạy.
- `tsc --noEmit` và Python `compileall` pass; FastAPI app import được và đăng ký 17 route.
- Vite production build chưa chạy được trong môi trường này: Node không được phép spawn tiến trình esbuild (`spawn EPERM`).
- Chưa tạo database, nhập dữ liệu hay chạy MySQL integration test trong lần triển khai này.

Xem [hướng dẫn cài đặt/chuyển dữ liệu](application_setup.md), [các quyết định triển khai](implementation_decisions.md) và [kịch bản nghiệm thu](commerce_acceptance.md).
