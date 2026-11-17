# Schema mới và quan hệ Customer–Accounts

Ngày thực hiện: 05/11/2026.

Schema đang dùng: **ecommerce_relationship_review**. Có 16 bảng và 100 sản phẩm; dữ liệu ứng dụng được sao chép đầy đủ từ ecommerce_vn_retailer_demo, đối chiếu số dòng và SHA-256 dữ liệu từng bảng. Các khóa ngoại đều tham chiếu trong schema mới và không có dòng mồ côi. .env.app và cấu hình mặc định đã chuyển sang tên mới.

## Quan hệ đã kiểm tra

**Customer 1 — 0..1 Accounts**: một customer có tối đa một account; một account bắt buộc thuộc đúng một customer.

- Customer.customerID là primary key.
- Accounts.accountID là primary key riêng của account.
- Accounts.customerID là **FOREIGN KEY + UNIQUE + NOT NULL**.
- UNIQUE chặn account thứ hai cùng customerID; FOREIGN KEY chặn customerID không tồn tại; NOT NULL bắt buộc account có customer.
- Customer không bắt buộc có dòng account tham chiếu đến mình, do đó đầu Accounts là 0..1, không phải 1..1 bắt buộc ở cả hai phía.

Đã thử trực tiếp bằng transaction rồi rollback: tạo customer chưa có account được; tạo account thứ nhất được; account thứ hai bị lỗi unique 1062; account tham chiếu customer không tồn tại bị lỗi FK 1452. Không giữ dữ liệu thử trong schema.

## Xem trong MySQL Workbench

1. Refresh khung SCHEMAS để thấy ecommerce_relationship_review.
2. Chọn Database → Reverse Engineer, chọn kết nối và schema mới.
3. Chọn các bảng cần xem, đưa customer và accounts vào EER Diagram.
4. Mở bảng accounts, kiểm tra Indexes có unique index trên customerID và Foreign Keys tham chiếu customer.customerID. Không cần sửa primary key để ép cách hiển thị của đường nối.

Nếu ký hiệu đường nối trong bản vẽ vẫn gây hiểu nhầm, ràng buộc UNIQUE trên customerID và phép thử insert mới là bằng chứng về số account được phép. Kiểu đường identifying/non-identifying không đồng nghĩa với composition/aggregation trong UML.

## Schema đã xóa và sao lưu

Theo xác nhận của người dùng, đã xóa 33 schema ecommerce_* cũ, kể cả ecommerce_vn_retailer_demo và ecommerce_electronics_demo. Chỉ giữ ecommerce_relationship_review trong nhóm e-commerce.

Không xóa auto_smart_hub, hotel, smart_tech_hub hoặc bốn schema hệ thống information_schema/mysql/performance_schema/sys.

Hai bản SQL sao lưu dữ liệu chính nằm trong **database/backups/before_schema_cleanup_20261105_010430/**. File cleanup_receipt.json tại đó ghi tên từng schema đã xóa, số dòng/hash dữ liệu, kích thước/hash file SQL và danh sách schema còn lại. Thư mục backup được bỏ qua bởi Git vì có dữ liệu tài khoản/phiên.

Chứng cứ kiểm tra quan hệ: data/test_runs/relationship_review_schema.json. Chứng cứ sao chép và xóa: data/test_runs/schema_cleanup_report.json. Các báo cáo kiểm thử cũ có thể nhắc tên schema đã xóa; chạy lại pytest sẽ tạo schema kiểm thử mới theo cơ chế cũ.
