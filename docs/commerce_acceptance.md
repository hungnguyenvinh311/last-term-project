# Nghiệm thu ứng dụng theo Physical Data Model

Hướng dẫn này dành cho phiên bản chuyển sang schema `electronics_ecommerce`. Không chạy thao tác nhập dữ liệu hoặc kiểm thử tích hợp trên schema nghiệp vụ đang dùng. Xem [application setup](application_setup.md) để tạo schema, xem trước và nhập danh mục.

## 1. Chuẩn bị

1. Chạy `database/004_electronics_physical_data_model.sql` trong MySQL Workbench.
2. Chạy lệnh import ở chế độ xem trước; kiểm tra sản phẩm, số lượng tồn và target đang trống.
3. Chỉ dùng `--apply` sau khi đã xác nhận đúng source và target; sau đó trỏ `APP_DATABASE` trong `.env.app` sang `electronics_ecommerce`.
4. Tạo tài khoản Admin đầu tiên và khởi động ứng dụng.
5. Kiểm tra `/api/health`, đăng nhập và tải trang quản trị.

## 2. Kịch bản theo vai trò

| Vai trò | Thao tác nghiệm thu | Kết quả mong đợi |
|---|---|---|
| Customer | Tìm bằng text, voice, image; lọc brand/giá/tồn; mở chi tiết và xem gợi ý | Kết quả phản ánh điều kiện; gợi ý cùng loại còn hàng |
| Customer | So sánh, thêm/xóa giỏ hàng, checkout COD hoặc online | Giá được xác nhận phía server; đơn tạo snapshot sản phẩm và hóa đơn; tồn được giữ/phân bổ |
| Customer | Hủy đơn trước khi đóng gói; xác nhận đã nhận sau khi bàn giao | Giữ hàng được giải phóng khi hủy; chỉ chủ đơn đã Dispatched mới xác nhận Delivered |
| Admin | Tạo/sửa/ngừng bán sản phẩm; sửa danh mục; tạo tài khoản và phân vai | Thay đổi được lưu/audit; người dùng chỉ thấy màn hình và API phù hợp quyền |
| Sales Staff | Ghi nhận kết quả chuyển khoản; xác nhận COD sau khi giao | Payment/PaymentEvent cập nhật; COD chưa được đánh dấu Paid trước khi giao và đối soát |
| Warehouse Staff | Nhập hàng, điều chỉnh tồn, chuyển Confirmed → Packing → Packed → Dispatched | Inventory và StockMovement cùng cập nhật; không điều chỉnh thấp hơn lượng đã cam kết |
| Manager | Lọc báo cáo theo khoảng ngày, loại và brand; xuất CSV/PDF | Doanh số chỉ tính đơn đã thanh toán; báo cáo tồn thể hiện nhập, xuất, điều chỉnh và tồn khả dụng |

## 3. Kiểm thử tự động

Chạy unit tests và kiểm tra TypeScript:

```powershell
.venv\Scripts\python.exe -m pytest tests/unit -q -p no:cacheprovider
cd View
.\node_modules\.bin\tsc.cmd --noEmit
```

Kiểm thử MySQL/API đầu-cuối chưa được thực hiện trong quá trình sửa mã để tránh ghi dữ liệu vào schema của người dùng. Sau khi có database test riêng, chạy từng luồng checkout, giữ/hết hạn tồn, payment, giao hàng và báo cáo bằng tài khoản test.

## 4. Ranh giới phiên bản

- `Order` hiện không có snapshot số điện thoại nhận hàng; số điện thoại lấy từ hồ sơ User.
- Payment gateway và shipping provider chỉ được mô phỏng. Chuyển trạng thái thanh toán do nhân viên ghi nhận; khách hàng xác nhận đã nhận hàng.
- Không có serial/IMEI, voucher, review, hoàn tiền thật hoặc kết nối API ngân hàng/vận chuyển.
- Nếu dữ liệu tồn cũ không có số lượng hợp lệ, import dừng; cần bổ sung số lượng trước khi có thể bán sản phẩm trong schema mới.
