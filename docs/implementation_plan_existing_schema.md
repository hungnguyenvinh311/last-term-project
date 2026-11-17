# Implementation Plan — Giữ nguyên database hiện tại

Ngày cập nhật: 04/11/2026. Đây là **kế hoạch hiện hành**, thay thế phương án mở rộng database trong `implementation_plan_remaining_features.md` theo giới hạn mới của người dùng.

## 1. Giới hạn bắt buộc

- Giữ nguyên 16 bảng của `ecommerce_vn_retailer_demo`: không thêm bảng/cột, không thay kiểu dữ liệu, ENUM, PK, FK, UNIQUE hoặc CHECK.
- Giữ nguyên quan hệ Accounts–Customer và AuthSessions–Accounts. Không bỏ UNIQUE trên Accounts.customerID.
- Chỉ làm chức năng có thể biểu diễn đúng bằng các trường và quan hệ đã có. Không nhét tồn kho, voucher, review, audit, refund ledger hoặc nhiều địa chỉ vào technicalSpecs, searchCriteria, status hay file JSON để né giới hạn.
- Có thể thêm View, Controller, service, contract, DAO method hoặc DTO; đây là mã triển khai, không phải entity/bảng lưu trữ mới.
- Không tạo migration/schema mới, kể cả SchemaMigrations. Không đổi 001_catalog.sql/002_application.sql để mở rộng thiết kế.
- Giữ Search/Recommendation và nhận diện theo nhãn đã cung cấp. Không tích hợp lọc theo tồn vì database chưa có dữ liệu tồn.
- Payment/shipping tiếp tục mô phỏng. Chức năng chỉ có summary phải được mô tả là summary, không tuyên bố có lịch sử đối soát/sự kiện đầy đủ.

## 2. Phạm vi được xây dựng

| Chức năng | Dữ liệu đã có | Mức thực hiện |
|---|---|---|
| Quản lý tài khoản | Accounts, Customer, AuthSessions | Tạo tài khoản staff, quản lý trạng thái và thu hồi phiên theo quyền hiện có. Chỉ hai role customer/staff; không thêm Administrator/Sales/Warehouse/Manager vào ENUM. |
| Quản trị sản phẩm | Products | Tạo/sửa tên, brand, mô tả, thông số, giá, bảo hành dạng nội dung, ảnh và trạng thái niêm yết bằng trường hiện có; bảo toàn ID và đơn cũ. |
| Quản trị danh mục | Categories | Quản lý metadata và specificationSchema của 5 nhóm điện tử hiện tại; không mở rộng taxonomy AI hoặc đổi ý nghĩa categoryID. Không xóa danh mục đang được tham chiếu. |
| So sánh sản phẩm | Products, Categories | Hoàn thiện bảo hành, giá trị thiếu và hiển thị khác biệt cho 2–4 sản phẩm cùng loại. |
| Hồ sơ khách hàng | Customer | Cập nhật tên, ngày sinh, điện thoại, một địa chỉ mặc định; không có sổ nhiều địa chỉ. |
| Giỏ hàng/checkout | Cart, CartItems, Orders, OrderItems | Revalidate giá, sản phẩm active, địa chỉ/điện thoại; tính tiền và phí giao hàng mô phỏng theo chính sách đơn giản; lưu snapshot và tạo đơn nguyên tử. Không kiểm tra hay cam kết tồn kho. |
| Hỗ trợ đơn hàng | Customer, Orders, OrderItems, Payments, Shipments | Staff xem chi tiết liên kết, tìm/lọc đơn và hủy trước Packing. Giữ đánh dấu RefundRequired khi cần; không thực hiện hoàn tiền. |
| Đóng gói/giao hàng | Orders.status, Shipments | Bổ sung Packed và trình tự trạng thái hợp lệ, tracking/carrier/ETA/deliveredAt bằng cột hiện có; không quản lý serial hoặc xuất kho. |
| Thanh toán online demo | Payments | Giữ/cải thiện kiểm tra tham chiếu, số tiền và kết quả summary của provider mô phỏng. Không phát triển attempt ledger, callback lịch sử hoặc tra soát tài chính đầy đủ. |
| Xác nhận thu COD demo | Payments + Orders + Shipments | Chỉ xác nhận summary khi đơn COD đã giao và số tiền/tham chiếu hợp lệ; cập nhật transactionCode, paidAt, status. Không có bảng/sổ đối soát COD hoặc ghi nhận nhiều lần thu. |
| Báo cáo đơn/doanh số đơn giản | Orders, OrderItems, Products, Categories | Tổng hợp theo ngày, trạng thái, sản phẩm, brand/category hiện tại; hiển thị và xuất CSV/PDF trực tiếp, không lưu bảng báo cáo. |

Phạm vi không đáp ứng đầy đủ mọi FR trong PDF. Quyền staff hiện gộp các vai trò nội bộ; không mô tả như đã triển khai RBAC chi tiết của bốn loại nhân viên.

## 3. Kế hoạch theo thứ tự đã thống nhất

### Giai đoạn 1 — Tài khoản và quản trị danh mục

Không thực hiện phần tách bốn vai trò hoặc nhật ký nghiệp vụ vì cần thay schema/bổ sung nơi lưu.

| File tạo mới dự kiến | Trách nhiệm |
|---|---|
| `View/application/view/AccountAdminView.tsx` | Tạo staff và quản lý tài khoản trong phạm vi role hiện có. |
| `View/application/view/CatalogAdminView.tsx` | Form quản trị sản phẩm và metadata danh mục. |
| `Controller/application/controller/CatalogAdminController.py` | API staff quản trị catalogue, tách khỏi API đọc của khách. |
| `Model/application/contract/ICatalogAdministration.py` | Contract nghiệp vụ quản trị. |
| `Model/application/service/CatalogAdministrationService.py` | Validate trường hiện có, bảo hành, giá và schema thông số; archive sản phẩm thay vì xóa lịch sử. |
| `Model/application/dto/ProductUpdate.py`, `Model/application/dto/CategoryUpdate.py` | Dữ liệu request/response; không là bảng mới. |
| `DAO/contract/CategoryDAO.py`, `DAO/application/dao/CategoryDAOImpl.py` | Đọc/ghi Categories bằng cột hiện có. |

File sửa: `Controller/application/controller/StaffController.py`, `security.py` cùng thư mục; `Model/application/contract/IAccount.py`, `Model/application/service/AccountService.py`; `DAO/contract/AccountDAO.py`, `ProductDAO.py` và các implementation tương ứng; `Model/application/contract/IMediaStorage.py`, `infrastructure/application/storage/LocalMediaStorage.py`; `View/application/view/StaffView.tsx`, `MainView.tsx`; `View/application/main.tsx`, `api.ts`; `bootstrap.py`.

Ảnh quản trị được kiểm tra định dạng/kích thước và lưu vào vùng ảnh sản phẩm được phép; không cho nhập đường dẫn filesystem tùy ý. Không tự xóa ảnh nguồn cũ. Products.articleID chưa AUTO_INCREMENT nên DAO phải cấp ID và xử lý cạnh tranh bằng cơ chế hiện có của MySQL, không ALTER cột.

Thay đổi nội dung/ảnh/category phải làm vector và nhãn ảnh đăng ký cũ không còn được coi là hợp lệ. Tái sử dụng `scripts/prepare_embeddings.py`, `scripts/prepare_detection_labels.py` và các manifest AI đã có để làm mới dữ liệu dẫn xuất; không dùng chúng làm kho lưu nghiệp vụ mới. Không chỉnh trực tiếp snapshot nguồn crawl để giả đó là dữ liệu gốc mới.

Kiểm thử dự kiến: `tests/unit/test_catalogue_administration.py`, `tests/integration/test_catalogue_administration.py`, `tests/integration/test_account_administration.py`, `tests/smoke/catalogue_administration.py`.

Nghiệm thu: customer bị chặn ở API staff; mật khẩu/token không bị lộ; dữ liệu giá/thông số không hợp lệ bị từ chối; archive không phá OrderItems; cập nhật không thay snapshot đơn đã mua; thay dữ liệu ảnh không giữ nhãn/embedding cũ như còn hợp lệ.

### Giai đoạn 2 — Chỉ hoàn thiện giỏ hàng/checkout, không làm kho

Không tạo InventoryService, bảng tồn, receipt, serial, hold hay allocation. Có holdExpireAt trong Orders không đủ để xây nghiệp vụ giữ số lượng hàng khi không có nguồn số dư/cam kết kho.

File tạo mới dự kiến:

- `Model/application/contract/ICheckoutPricing.py`.
- `Model/application/service/CheckoutPricingService.py`.
- `Model/application/dto/PricingSummary.py`.
- `config/commerce.py`: mức phí ship demo cố định/cấu hình đơn giản, không phải kho voucher hay dữ liệu tồn.

File sửa: `CartService.py`, `CheckoutService.py` trong `Model/application/service/`; `ICart.py`, `ICheckout.py` trong `Model/application/contract/`; `CartDAO.py`, `OrderDAO.py` và implementation tương ứng; `CartController.py`, `OrderController.py`; `CartView.tsx`, `CheckoutView.tsx`; `bootstrap.py`.

Giữ itemSubTotal, discountAmount, shippingFee, totalAmount đã có trong Orders. Chức năng mới không tự tạo discount/voucher; discountAmount của đơn mới tiếp tục bằng 0. Phí và tổng được tính ở server, không tin số tiền client gửi. Giỏ vẫn không tạo giữ hàng. COD không gọi gateway; online tạo đơn bền vững trước khi thanh toán.

Kiểm thử: `tests/unit/test_checkout_pricing.py`, `tests/integration/test_checkout_existing_schema.py`, `tests/smoke/checkout_existing_schema.py`: giá thay đổi, sản phẩm inactive, tổng tiền/ship, retry và quyền sở hữu đơn. Không ghi nhận “còn hàng” hay “giữ hàng thành công” khi không có dữ liệu tồn.

### Giai đoạn 3 — Đơn hàng, thanh toán/giao hàng mô phỏng trên các summary hiện có

| File tạo mới dự kiến | Trách nhiệm |
|---|---|
| `View/application/view/SalesOrdersView.tsx` | Staff tìm/lọc và xem chi tiết hồ sơ–đơn–payment–shipment. |
| `View/application/view/FulfilmentView.tsx` | Confirmed → Packing → Packed → Dispatched → Delivered; hiển thị vận đơn và ETA. |
| `View/application/view/CODConfirmationView.tsx` | Xác nhận thu COD demo sau giao hàng, đối chiếu số tiền và tracking/reference. |
| `Controller/application/controller/PaymentOperationsController.py` | API staff cho thao tác summary thanh toán được phép. |
| `Model/application/dto/StaffOrderDetails.py` | DTO chi tiết phục vụ staff; không thêm bảng. |

File sửa: `ICheckout.py`, `IPayment.py`, `IFulfilment.py`, `IShippingProvider.py` trong `Model/application/contract/`; `CheckoutService.py`, `PaymentService.py`, `FulfilmentService.py`; OrderDAO/PaymentDAO/ShipmentDAO và các implementation; `StaffController.py`, `OrderController.py`; `SimulatedPaymentGateway.py`, `SimulatedShippingProvider.py`; `StaffView.tsx`, `CheckoutView.tsx`, `bootstrap.py`.

- Dùng Orders.status/Shipments.status kiểu VARCHAR để thêm Packed trong code, không thay kiểu cột hoặc tạo bảng trạng thái.
- Dùng các cột trackingNumber, carrier, estimatedDeliveryDate, deliveredAt hiện có; không lưu nhiều shipment/order vì UNIQUE(orderID) vẫn giữ nguyên.
- Hủy chỉ trước Packing. Có tiền đã thu thì giữ RefundRequired, không đánh dấu Refunded hoặc tự làm mất dấu paidAt/transactionCode.
- Thanh toán lặp với cùng kết quả đã xử lý không gây chuyển trạng thái lần hai. Kết quả mâu thuẫn bị từ chối; không xây lịch sử event/attempt giả bằng cách nối chuỗi trong transactionCode.
- COD: kiểm tra phương thức, trạng thái Delivered, số tiền server và vận đơn của đúng order; cập nhật một Payment summary trong transaction, chống ghi nhận lại. Phần này là xác nhận thu tiền demo, không phải module đối soát đầy đủ của FR35.
- Không xây xử lý số tiền đến muộn sau hold, vì không có nghiệp vụ kho/hold được triển khai. Không tự trừ tồn khi Dispatched.

Kiểm thử: `tests/integration/test_staff_order_details.py`, `tests/integration/test_fulfilment_states.py`, `tests/integration/test_cod_confirmation.py`, `tests/smoke/order_fulfilment.py`. Bao gồm Packed, chặn nhảy/lùi trạng thái, hủy sai điều kiện, COD sai số tiền/vận đơn và thao tác lặp.

### Giai đoạn 4 — Báo cáo đơn/doanh số; không có tồn kho/cảnh báo tồn

File tạo mới dự kiến:

- `View/application/view/ReportsView.tsx`.
- `Controller/application/controller/ReportController.py`.
- `Model/application/contract/IReporting.py` và `Model/application/service/ReportingService.py`.
- `DAO/contract/ReportDAO.py` và `DAO/application/dao/ReportDAOImpl.py`.
- `Model/application/dto/SalesReportData.py`.
- `Model/application/contract/IReportExport.py` và `infrastructure/application/reporting/ReportExporter.py`.

File sửa: `StaffView.tsx`, `View/application/main.tsx`, `bootstrap.py`, `requirements-app.txt` nếu cần thư viện xuất PDF.

Báo cáo được phép: số đơn theo trạng thái/ngày/phương thức; số lượng hàng bán; giá trị đơn hàng theo snapshot unitPrice và tổng đã lưu; sản phẩm bán nhiều; phân nhóm brand/category hiện tại; xuất CSV/PDF từ cùng tập dữ liệu. Phân quyền bằng role staff hiện có.

Giới hạn số liệu:

- Doanh số đơn và tiền đã thanh toán là hai thước đo riêng; không cộng COD chưa xác nhận thu vào tiền đã thu.
- Tính tổng ở đúng cấp order/item, không nhân lặp totalAmount khi JOIN nhiều OrderItems.
- Phí ship không là doanh số hàng hóa; đơn hủy không được tính vào doanh số đơn hợp lệ.
- Không có brand/category snapshot riêng: bộ lọc theo brand/category phản ánh Products hiện tại, không khẳng định là phân loại tại thời điểm bán.
- Nếu đơn cũ có discountAmount khác 0, chỉ báo cáo net toàn đơn chính xác; phân bổ giảm giá theo brand/category phải có quy tắc minh bạch hoặc bỏ thước đo net chi tiết đó, không tự nhận có snapshot phân bổ đã lưu.
- Không có ledger refund/settlement: không xây báo cáo dòng tiền lịch sử đầy đủ, lợi nhuận hay báo cáo hoàn tiền.
- Không có số dư/movement: không xây báo cáo tồn kho và cảnh báo tồn thấp.

Kiểm thử: `tests/unit/test_report_measures.py`, `tests/integration/test_sales_reports.py`, `tests/smoke/report_export.py`: dữ liệu rỗng, đơn nhiều dòng, đơn hủy, phí ship, COD chưa thu; nội dung xuất file khớp tổng; customer không lấy được báo cáo staff.

### Giai đoạn 5 — Chỉ hồ sơ và một địa chỉ mặc định

File tạo mới dự kiến: `View/application/view/ProfileView.tsx`.

File sửa: `Controller/application/controller/AccountController.py`, `Model/application/contract/IAccount.py`, `Model/application/service/AccountService.py`, `DAO/contract/CustomerDAO.py`, `DAO/application/dao/CustomerDAOImpl.py`, `View/application/main.tsx`, `CheckoutView.tsx`.

Cho phép sửa fullName, dateOfBirth, phoneNumber, shippingAddress đã có. Checkout lấy địa chỉ làm gợi ý, nhưng Orders giữ shippingAddress/recipientPhone riêng; sửa hồ sơ không thay đơn cũ. Không tạo danh sách địa chỉ trong một trường chuỗi/JSON. Email và mật khẩu không tự được mở thành luồng thay đổi phức tạp ngoài phạm vi này.

Kiểm thử: `tests/integration/test_profile_default_address.py`, `tests/smoke/profile_checkout.py`: chỉ sửa hồ sơ của mình, ngày sinh/điện thoại không hợp lệ, địa chỉ mặc định và snapshot đơn cũ.

Không tạo VoucherAdminView/VoucherService hoặc ReviewService/ReviewController. Các chức năng này cần dữ liệu lưu riêng nên bị loại khỏi kế hoạch.

## 4. Những chức năng không triển khai

| Chức năng bị loại | Lý do |
|---|---|
| Tách Administrator/Sales/Warehouse/Manager | Accounts.role hiện chỉ customer/staff; không sửa ENUM hoặc thêm bảng quyền. |
| Nhật ký nghiệp vụ/audit viewer | Không có AuditLogs; không dùng log kỹ thuật để nhận là audit ledger. |
| Nhập/kiểm kê/tồn/hold/allocation/serial/IMEI | Không có số dư, cam kết và lịch sử thiết bị. |
| Xuất kho/nhận hàng trả | Không có stock movements và dữ liệu hàng trả. |
| Hoàn tiền và tra soát đầy đủ | Một Payment summary không thay được refund/attempt/event ledger. |
| Lịch sử giao hàng/đối soát COD đầy đủ | Shipments/Payments hiện chỉ là summary; không thêm các bảng sự kiện/settlement. |
| Báo cáo/cảnh báo tồn thấp | Không có quantity nguồn để tính. |
| Nhiều địa chỉ | Customer chỉ có một shippingAddress. |
| Voucher | Orders.discountAmount là số tiền tổng, không phải dữ liệu định nghĩa/lượt dùng voucher. |
| Review | Không có nơi lưu rating/content và liên kết review với giao dịch đã giao. |

## 5. Kiến trúc, kiểm chứng và bàn giao

Giữ View → Controller → service contract/service → DAO contract/implementation → MySQL. Giữ các entity hiện có. Các lớp chức năng mới cần được mô tả là phần mở rộng code của kiến trúc MVC, không khẳng định chúng đã có đủ trong hình package/component PDF. ERD không cần thêm bảng hoặc thuộc tính theo kế hoạch này.

Trước/sau triển khai, so sánh cấu trúc information_schema (bảng, cột, kiểu, khóa/index/constraint); kết quả phải không thay đổi. Không chạy CREATE/ALTER/DROP trong code khởi động hoặc test schema-preservation. Dữ liệu nghiệp vụ vẫn được INSERT/UPDATE qua các chức năng hợp lệ.

Chạy regression tests hiện có và tests bổ sung theo từng giai đoạn. Integration test dùng database riêng có cùng schema, không tạo dữ liệu thử trong database chính. Kết quả test không được diễn đạt thành đã đáp ứng các FR bị loại ở mục 4 hoặc NFR tải lớn chưa đo.

Tài liệu bàn giao cập nhật sau khi thực hiện: `docs/application_setup.md`, `docs/design_code_mapping.md`, `docs/implementation_decisions.md`, `docs/implementation_verification.md`. Phải ghi rõ giới hạn demo: hai vai trò, không kho/voucher/review/refund ledger, và chỉ một địa chỉ mặc định.

Tại thời điểm lập kế hoạch giới hạn này: **chưa thay đổi mã nguồn ứng dụng hoặc database**.

## 6. Trạng thái thực hiện — 05/11/2026

Các nhóm chức năng được hỗ trợ bởi schema đã được triển khai. Tên file kiểm thử thực tế được gom theo chức năng trong tests/integration/test_commerce_existing_schema.py và tests/unit/test_commerce_policies.py, thay cho nhiều file dự kiến riêng trong mục 3. Nghiệm thu trình duyệt nằm ở tests/smoke/commerce_browser_smoke.py.

Các lớp giao diện, service, DAO và hợp đồng thực tế được cập nhật trong docs/design_code_mapping.md; hướng dẫn chạy/nghiệm thu và giới hạn phạm vi ở docs/commerce_acceptance.md. Chứng cứ kiểm thử ở data/test_runs. Không triển khai các mục bị loại trong mục 4, không sửa schema hiện có. Dòng “chưa thay đổi mã nguồn” phía trên mô tả thời điểm lập kế hoạch, không phải trạng thái bàn giao hiện tại.

