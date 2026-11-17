# Quyết định triển khai hiện tại

Ứng dụng được tái tổ chức theo bốn package gốc: `View`, `Controller`, `Model`, `DAO`. `bootstrap.py` khởi tạo dependency và nối giao diện MVC với các hợp đồng service/DAO. Các cấu hình và adapter tích hợp nằm dưới `Model/application/config` và `Model/application/integration`; công cụ import và chuẩn bị dữ liệu nằm trong `scripts`.

## Cơ sở dữ liệu

Ứng dụng nhắm tới schema mới `electronics_ecommerce`, được tạo từ `database/004_electronics_physical_data_model.sql`. Các DAO dùng các bảng trong schema này, không tự tạo bảng và không thêm cột ngoài mô hình. Cấu hình từ chối ba tên schema cũ để tránh chạy DAO mới trên cấu trúc không tương thích. File `.env.app` hiện trỏ `APP_DATABASE` sang schema mới; những cấu hình khác được giữ nguyên.

`import_catalog_to_physical_schema.py` có chế độ preview mặc định. Chỉ lệnh có `--apply` mới chép dữ liệu danh mục vào target trống; nó không xóa hoặc cập nhật source. Tồn kho phải có giá trị không âm trong bảng tồn cũ hoặc trong thuộc tính số lượng của `technicalSpecs`; nếu thiếu, import dừng. Mô tả sản phẩm được giữ trong `technicalSpecs.description`, vì physical model không có cột mô tả riêng.

## Luồng nghiệp vụ đã mã hóa

- Tài khoản lưu role qua `Employee.role`; đăng ký công khai chỉ tạo customer. Admin quản lý tài khoản nhân viên và phân quyền.
- Checkout đọc giá và tồn trong transaction, ghi `OrderItem` snapshot, hóa đơn, thanh toán và cam kết tồn. Online giữ hàng có hạn; COD phân bổ tồn ngay. Hủy hoặc hết hạn giải phóng cam kết.
- Nhập hàng và điều chỉnh tồn cập nhật đồng thời `Inventory` và `StockMovement`. Khi bàn giao đơn, tồn thực giảm. Customer xác nhận đã nhận; COD chỉ được xác nhận sau đó.
- Ghi nhận thanh toán do nhân viên thực hiện; mỗi lần được lưu vào `PaymentEvent`. Không có kết nối gateway thật hoặc thao tác chuyển tiền tự động.
- Báo cáo đọc đơn, thanh toán, sản phẩm và sổ biến động kho. Doanh số chỉ tính đơn đã thanh toán; COD được tính sau xác nhận thu tiền.
- Search ghi `SearchQuery`, query subtype và `SearchResult`; recommendation sản phẩm tương tự không dựa trên lịch sử cá nhân. Kết quả search dùng vector và điều kiện lọc/brand/giá/tồn.

## Giới hạn do schema

Schema không có snapshot số điện thoại nhận hàng riêng trong Order, nên checkout cập nhật số điện thoại hiện tại của User; lịch sử đơn không giữ số điện thoại tại thời điểm mua. Payment và shipment là luồng mô phỏng. Serial/IMEI, voucher, review, hoàn tiền thật và tích hợp đối tác bên ngoài chưa triển khai.

## Kiểm chứng

Unit tests xác nhận hợp đồng schema, chuyển đổi dữ liệu catalogue, giải mã JSON cho embedding/thông số, tính doanh số và nghiệp vụ thanh toán. Kiểm thử MySQL đầu-cuối chỉ nên chạy trên schema kiểm thử riêng. Hướng dẫn cài đặt và nghiệm thu ở `application_setup.md` và `commerce_acceptance.md`.
