# Implementation Plan — Các chức năng thương mại còn lại

> **Đã được thay thế:** theo yêu cầu mới, không thêm bảng/cột/ràng buộc. Chỉ triển khai theo [kế hoạch giữ nguyên schema](implementation_plan_existing_schema.md). Phương án mở rộng bên dưới được giữ để tham khảo, không phải phạm vi đang được phép triển khai; không thực hiện các migration hoặc 22 bảng được đề xuất ở đây.

Ngày lập: 04/11/2026. Trạng thái: **đề xuất để xem xét; chưa triển khai mã nguồn hoặc migration**.

Tài liệu gốc: [design_03_06_HungNV.pdf](../../design_03_06_HungNV.pdf), đặc biệt Bảng 2.2, 2.5, 2.6; mục 2.2.2, 2.7; Chương 4 và BR01–BR12 tại Phụ lục A. Kế hoạch này tiếp nối bản demo đã có; không dùng hiện trạng cũ trong `implementation_plan.md` để mô tả hệ thống hôm nay.

## 1. Phạm vi và hiện trạng

- Database ứng dụng: `ecommerce_vn_retailer_demo`, hiện có 16 bảng: 14 bảng lõi và `Accounts`, `AuthSessions` đã được bổ sung trước đó.
- Đã có danh mục đọc, so sánh, giỏ hàng, checkout cơ bản, lịch sử đơn, thanh toán/giao hàng mô phỏng, tài khoản và chức năng AI.
- Search/Recommendation giữ luồng đã thống nhất. Chỉ tích hợp dữ liệu tồn khả dụng và cơ chế cập nhật biểu diễn khi danh mục thay đổi; không mở lại việc chọn mô hình AI.
- Các dịch vụ thanh toán và vận chuyển tiếp tục là mô phỏng, nhưng cần có sự kiện, kiểm tra tham chiếu, chống xử lý lặp, tra soát và kết quả nghiệp vụ như tài liệu.
- Không triển khai mua hàng từ nhà cung cấp, bảo hành đầy đủ, quy trình phê duyệt đổi trả trực tuyến, tính thuế hay phân tích lợi nhuận. Nhân viên chỉ ghi nhận kết quả trả hàng đã được phê duyệt bên ngoài.
- Giữ dữ liệu sản phẩm, ID, ảnh, embedding, nguồn dữ liệu và các database cũ. Không DROP bảng, xóa schema hay thay đổi PDF/LaTeX trong công việc này.

## 2. Có tuân thủ thiết kế PDF không?

**Tuân thủ kiến trúc và các nghiệp vụ của PDF; cần bổ sung thiết kế lớp/bảng cho các nghiệp vụ chưa được thể hiện trong Chương 4.** Không thể khẳng định các lớp mới dưới đây đã có sẵn trong hình package/component hay ERD hiện tại.

| Thành phần | Quy tắc triển khai |
|---|---|
| View | Giữ `MainView`, `CartView`, `CheckoutView`, `StaffView`; thêm các màn hình con theo chức năng. View chỉ gọi HTTP, không truy vấn DB hay trực tiếp gọi provider. |
| Controller | Giữ các controller hiện có; thêm controller khi cần một nhóm chức năng mới. Kiểm tra dữ liệu HTTP, xác thực/quyền và gọi service contract. |
| Model/service | Thực hiện quy tắc kho, trạng thái đơn, tính tiền, voucher, hoàn tiền và báo cáo. Không đặt SQL trong service. |
| Model/entity | Giữ 16 entity hiện có; bổ sung entity tương ứng các bản ghi nghiệp vụ mới được duyệt. Không tự truy cập DB. |
| Model/contract | Khai báo các interface cho service/provider/giao dịch. Không để controller phụ thuộc tên DAOImpl. |
| DAO | Mỗi nhóm dữ liệu có DAO interface và implementation riêng. DAO chứa SQL, khóa dòng, đọc/ghi và ánh xạ dữ liệu; không tự quyết định toàn bộ luồng checkout/thanh toán. |
| Infrastructure | Provider mô phỏng, lưu trữ và adapter giao dịch; không phụ thuộc View. |
| `bootstrap.py` | Nơi khởi tạo và tiêm dependency; bổ sung các component mới ở đây. |

Phụ thuộc chính: `View → Controller → service contract/service → DAO contract → DAO implementation → MySQL`. Entity/DTO không import Controller hoặc DAOImpl. Các service dùng contract khi gọi nhau; không tạo phụ thuộc vòng.

### 2.1. Ranh giới giao dịch cần làm rõ trong mã hiện có

Hiện `OrderDAOImpl.createWithItems` đang chứa một phần quyết định nghiệp vụ. Khi bổ sung kho/voucher, sẽ đưa quyết định về service và giữ DAO làm thao tác dữ liệu.

- Tạo `Model/application/contract/IUnitOfWork.py` và `infrastructure/application/persistence/MySQLUnitOfWork.py`; sửa `DAO/application/dao/connection.py` để các DAO tham gia **cùng một transaction**, không commit riêng khi một service gọi service khác.
- Tạo `Model/application/contract/IOrderLifecycle.py` và `Model/application/service/OrderLifecycleService.py` để phối hợp chuyển trạng thái đơn với giữ/phân bổ/giải phóng/xuất kho và nghĩa vụ hoàn tiền.
- `OrderLifecycleService` dùng OrderDAO, Inventory contract, các DAO tài chính cần thiết và Unit of Work. Nó không gọi ngược CheckoutService, PaymentService hoặc FulfilmentService.
- CheckoutService, PaymentService và FulfilmentService gọi IOrderLifecycle. InventoryService không gọi ngược các service này.
- Gọi provider **ngoài transaction đang khóa kho**. Ghi nhận đơn/hold hoặc yêu cầu tài chính bền vững trước, sau đó mới gọi mô phỏng provider; kết quả được áp dụng bằng một transaction khác.
- Nhật ký nghiệp vụ thành công được ghi cùng transaction với thay đổi nghiệp vụ. Không lưu mật khẩu, token gốc hoặc dữ liệu thẻ trong nhật ký.

Đây là thành phần thiết kế bổ sung để thực hiện các quy tắc giao dịch của mục 4.2.3, không phải lớp đã có trong sơ đồ PDF.

## 3. Những quyết định không được thay ngầm

| Vấn đề | Phương án lập kế hoạch |
|---|---|
| Customer–Account | Database hiện có FK + UNIQUE trên `Accounts.customerID`: Customer 1 — Account 0..1. Chưa tự bỏ UNIQUE. Nếu chọn Customer 1 — Account 0..*, phải xác nhận việc các tài khoản dùng chung hồ sơ, giỏ hàng, đơn và địa chỉ; bổ sung migration tương ứng sau khi chốt. |
| Nhân viên và Customer | Giữ liên kết hiện tại trong giai đoạn đầu để không làm hỏng dữ liệu. Tách hồ sơ nhân viên khỏi Customer là một thay đổi thiết kế khác, không gộp ngầm vào phân quyền. |
| Số vai trò/tài khoản | Đề xuất một vai trò chính trên mỗi account: `customer`, `administrator`, `sales`, `warehouse`, `manager`. Chưa cần thêm bảng Role/Permission nếu phạm vi không yêu cầu nhiều vai trò cho một tài khoản. |
| Tài khoản `staff` cũ | Không tự chuyển tất cả thành Administrator. Rà soát và ánh xạ vai trò có kiểm soát, giữ ít nhất một tài khoản có thể quản trị. |
| Tồn kho ban đầu | Tồn kho lấy từ số liệu nhập thử/nhân viên, không suy ra từ website bán lẻ hay AI. Có seed demo riêng, ghi rõ số liệu và serial mô phỏng; không gọi đó là tồn kho thực hoặc IMEI nhà sản xuất đã xác minh. |
| Serial/IMEI | Chỉ bắt buộc với SKU được đánh dấu quản lý theo thiết bị; không ép mọi phụ kiện phải có IMEI. |
| Đơn cũ chưa có kho | Không tự sinh stock movement/serial để hợp thức hóa lịch sử. Xác định mốc áp dụng nghiệp vụ mới; rà soát đơn chưa hoàn tất trước khi bật giữ/xuất kho. |
| Voucher khi hủy đơn | Đề xuất giải phóng lượt đang giữ khi đơn chưa xác nhận bị hủy/hết hạn. Lượt đã sử dụng không tự phục hồi sau hoàn tiền nếu chưa có quy tắc được duyệt. |
| Nhận xét sản phẩm | Đề xuất một review trên một OrderItem đã giao; một khách có thể review các lần mua khác nhau. Không tự bổ sung quy trình kiểm duyệt phức tạp. |

## 4. Thứ tự phát triển và file dự kiến

Trong các bảng dưới đây, “Tạo” là file chưa có; “Sửa” là tái sử dụng file hiện có. Đây là danh sách dự kiến, không phải thông báo các file đã được tạo.

### Giai đoạn 1 — Phân quyền và quản trị danh mục

#### 1A. Vai trò, quyền và quản lý tài khoản nhân viên

Actor: Administrator; các vai trò nhân viên khi đăng nhập. UC14, UC16; FR02, FR27, phần quyền của FR28.

| Loại | File dự kiến | Nội dung |
|---|---|---|
| Tạo | `Model/application/security/permissions.py` | Ma trận quyền cố định theo 5 vai trò; quyền riêng cho quản trị danh mục, bán hàng, kho, báo cáo và tài khoản. |
| Tạo | `View/application/view/AccountAdminView.tsx` | Tạo tài khoản nhân viên, đổi vai trò và khóa/mở theo quyền. |
| Sửa | `Model/application/entity/Account.py`, `Model/application/contract/IAccount.py`, `Model/application/service/AccountService.py` | Mở rộng vai trò và nghiệp vụ quản trị; đăng ký công khai vẫn chỉ tạo customer. |
| Sửa | `DAO/contract/AccountDAO.py`, `DAO/application/dao/AccountDAOImpl.py` | Ghi vai trò, kiểm tra tài khoản và thu hồi phiên khi cần. |
| Sửa | `Controller/application/controller/security.py`, `AccountController.py`, `StaffController.py` cùng thư mục | Thay kiểm tra `staff=True` bằng quyền nghiệp vụ; giữ kiểm tra chủ sở hữu dữ liệu. |
| Sửa | `View/application/api.ts`, `View/application/main.tsx`, `View/application/view/StaffView.tsx` | Kiểu role mới, menu và bố cục màn hình theo quyền; backend vẫn là nơi quyết định quyền. |
| Sửa | `scripts/create_staff.py`, `bootstrap.py` | Tạo nhân viên với vai trò rõ ràng và nối các dependency. |

Kiểm thử mới: `tests/unit/test_permissions.py`, `tests/integration/test_staff_access.py`, `tests/smoke/staff_access.py`.

Nghiệm thu: customer không gọi được API staff; warehouse không sửa giá/hoàn tiền; sales không điều chỉnh kho; manager không đổi role; không vô hiệu hóa quản trị viên cuối cùng; thay đổi quyền có hiệu lực với các phiên đang mở.

#### 1B. Sản phẩm, danh mục, thông số, giá và bảo hành

Actor: Administrator. UC12; FR04–05, FR36.

| Loại | File dự kiến | Nội dung |
|---|---|---|
| Tạo | `View/application/view/CatalogAdminView.tsx` | Tạo/sửa SKU, danh mục, brand, thông số, giá VND, bảo hành và trạng thái niêm yết. |
| Tạo | `Controller/application/controller/CatalogAdminController.py` | API quản trị tách khỏi API đọc của khách hàng. |
| Tạo | `Model/application/contract/ICatalogAdministration.py`, `Model/application/service/CatalogAdministrationService.py` | Kiểm tra dữ liệu theo category schema; cập nhật và archive sản phẩm đã được tham chiếu. |
| Tạo | `Model/application/dto/ProductUpdate.py`, `Model/application/dto/CategoryUpdate.py` | Hợp đồng dữ liệu cập nhật, không nhận embedding do trình duyệt gửi. |
| Tạo | `DAO/contract/CategoryDAO.py`, `DAO/application/dao/CategoryDAOImpl.py` | Đọc/ghi danh mục và schema thông số. |
| Sửa | `Product.py`, `Category.py` trong `Model/application/entity/`; `DAO/contract/ProductDAO.py`, `DAO/application/dao/ProductDAOImpl.py` | Ánh xạ trường mới và bổ sung thao tác quản trị; không xóa dữ liệu lịch sử. |
| Sửa | `Model/application/service/ProductService.py`, `scripts/prepare_embeddings.py`, `scripts/prepare_detection_labels.py` | Hiển thị bảo hành chuẩn; làm mới/invalidate biểu diễn và nhãn ảnh đã đăng ký khi dữ liệu nguồn thay đổi. Tái sử dụng công cụ AI hiện có. |
| Sửa | `View/application/view/MainView.tsx`, `Model/application/service/ProductService.py` | Hoàn thiện so sánh FR08: hàng bảo hành, thông số cùng đơn vị, giá trị thiếu được ghi rõ và điểm khác biệt được làm nổi bật. |
| Sửa | `View/application/view/StaffView.tsx`, `bootstrap.py` | Gắn màn hình và service mới. |

Không tạo bảng Brands riêng trong phương án tối thiểu: tiếp tục chuẩn hóa trường `Products.brand`. Chỉ thêm bảng nếu chốt thêm nghiệp vụ riêng của thương hiệu.

Kiểm thử mới: `tests/unit/test_catalogue_administration.py`, `tests/integration/test_catalogue_administration.py`, `tests/smoke/catalogue_administration.py`.

Nghiệm thu: giá/thông số không hợp lệ bị từ chối; archive không phá OrderItems; sửa sản phẩm không thay snapshot đơn cũ; đổi ảnh/thông số làm biểu diễn cũ không còn được dùng như biểu diễn hợp lệ. Ảnh mới chưa cập nhật label registry không được nhận nhãn của ảnh cũ.

#### 1C. Nhật ký thao tác quan trọng

Actor: Administrator; các thao tác của staff được ghi lại. UC14; FR28.

| Loại | File dự kiến | Nội dung |
|---|---|---|
| Tạo | `Model/application/entity/AuditLog.py` | Actor, thời điểm, loại thao tác, tham chiếu và trước/sau. |
| Tạo | `Model/application/contract/IAudit.py`, `Model/application/service/AuditService.py` | Ghi/đọc nhật ký với giới hạn quyền và lọc trường nhạy cảm. |
| Tạo | `DAO/contract/AuditDAO.py`, `DAO/application/dao/AuditDAOImpl.py` | Lưu và truy vấn nhật ký. |
| Tạo | `View/application/view/AuditView.tsx` | Tra cứu theo người, thời gian, đối tượng và thao tác. |
| Sửa | `StaffController.py`, `StaffView.tsx`, `bootstrap.py` | API xem nhật ký và nối component. Các service quản trị/kho/tài chính gọi IAudit khi thực hiện thay đổi. |

Kiểm thử: `tests/integration/test_audit_atomicity.py`: transaction lỗi không để lại nhật ký “thành công”; thay đổi giá/role có before/after và actor; dữ liệu nhạy cảm không bị lưu.

### Giai đoạn 2 — Kho và checkout

#### 2A. Nhập hàng, kiểm kê, số lượng khả dụng và thiết bị

Actor: Warehouse Staff. UC10; FR19, FR29–30, nền tảng cho FR07 và FR36.

| Loại | File dự kiến | Nội dung |
|---|---|---|
| Tạo | `View/application/view/InventoryView.tsx`, `Controller/application/controller/InventoryController.py` | Nhập hàng, ghi serial/IMEI, kiểm kê có lý do, xem Q/H/A/V và lịch sử biến động. |
| Tạo | `Model/application/contract/IInventory.py`, `Model/application/service/InventoryService.py` | Các quy tắc tồn, kiểm tra thiết bị và ghi nhận nhập/điều chỉnh một lần. |
| Tạo | `InventoryBalance.py`, `StockCommitment.py`, `StockMovement.py`, `GoodsReceipt.py`, `GoodsReceiptItem.py`, `DeviceIdentifier.py` trong `Model/application/entity/` | Các bản ghi kho mới. |
| Tạo | `Model/application/dto/InventoryChange.py`, `Model/application/dto/StockSummary.py` | Dữ liệu nhập/kiểm kê và số dư trả về. |
| Tạo | `DAO/contract/InventoryDAO.py`, `DAO/application/dao/InventoryDAOImpl.py` | Truy cập nhóm bảng kho; khóa số dư SKU, kiểm tra tính duy nhất và truy vấn lịch sử. |
| Sửa | `ProductService.py`, `ProductDAOImpl.py`, `Product.py`, `MainView.tsx` ở các thư mục hiện có | Hiển thị/lọc tồn khả dụng từ kho; không dùng `isActive` để thay thế số lượng hàng. |
| Sửa | `Model/application/normalization.py`, `Model/application/retrieval/CandidateRetriever.py` | Áp dụng điều kiện tồn bắt buộc từ dữ liệu nghiệp vụ, không thay logic embedding/ranking. |
| Sửa | `Model/application/dto/SearchCriteria.py`, `Model/application/contract/IProduct.py`, `Controller/application/controller/ProductController.py`, `Controller/application/controller/SearchRoutesService.py`, `View/application/view/MainView.tsx` | Truyền điều kiện chỉ còn hàng/số lượng khả dụng qua hợp đồng dữ liệu; không suy ra tồn từ ảnh hoặc nhãn. |

Quy tắc: `V = Q − H − A`, mọi số dư không âm. Nhập tăng Q; kiểm kê không được hạ Q dưới H+A. Cart không tạo cam kết kho.

SKU chưa có số dư kho được hiển thị là chưa xác minh, không tự gán một số dương. Bộ lọc tồn chỉ áp dụng theo điều kiện nghiệp vụ tương ứng; không chặn so sánh một sản phẩm active chỉ vì hết hàng, theo BR05. Thay đổi số lượng kho không bắt buộc tạo lại embedding hình ảnh/văn bản.

Kiểm thử: `tests/unit/test_inventory_rules.py`, `tests/integration/test_inventory_receipts.py`, `tests/integration/test_inventory_concurrency.py`.

Nghiệm thu: nhập trùng mã thao tác không tăng kho lần hai; serial trùng bị chặn; kiểm kê thiếu hàng so với cam kết tạo tình huống cần xử lý, không tự xóa cam kết.

#### 2B. Giữ hàng online, phân bổ COD và hết hạn

Actor: Customer; job hết hạn là thành phần nội bộ, không phải actor mới. UC04, UC18; FR11–13, FR17–18, FR31.

| Loại | File dự kiến | Nội dung |
|---|---|---|
| Tạo | `IUnitOfWork.py`, `MySQLUnitOfWork.py`, `IOrderLifecycle.py`, `OrderLifecycleService.py` tại các đường dẫn mục 2.1 | Phối hợp nguyên tử đơn, snapshot và cam kết kho. |
| Tạo | `Model/application/jobs/OrderExpiryJob.py`, `scripts/run_maintenance.py` | Kiểm tra hold đến hạn từ DB, phục hồi sau restart; CLI dùng cùng logic với job ứng dụng. |
| Tạo | `Model/application/contract/IClock.py`, `infrastructure/application/clock/SystemClock.py` | Thời gian UTC có thể thay thế trong test; không phụ thuộc đồng hồ đếm ngược của trình duyệt. |
| Tạo | `config/commerce.py` | Chính sách 15 phút, chu kỳ quét tối đa 30 giây, quy tắc vùng phục vụ và cấu hình giao hàng demo. |
| Sửa | `ICheckout.py`, `CheckoutService.py`, `OrderDAO.py`, `OrderDAOImpl.py`, `CartDAO.py`, `CartDAOImpl.py`, `Order.py`, `OrderItem.py` ở các thư mục hiện có | Revalidate giá/địa chỉ/tồn, tạo snapshot và giữ/phân bổ trong một transaction; chuyển quyết định nghiệp vụ ra khỏi DAO. |
| Sửa | `OrderController.py`, `CheckoutView.tsx`, `CartView.tsx`, `bootstrap.py` tại thư mục hiện có | Xác nhận giá thay đổi, trạng thái hold và hủy; khởi động job và DI. |

Online: tạo `Pending Payment` và hold 15 phút trước gọi provider. COD: tạo `Confirmed`, phân bổ trực tiếp và giữ `Unpaid COD`. Retry không gia hạn hold. Hết hạn/hủy giải phóng một lần. Hàng vật lý chưa bị trừ ở bước này.

Tên có khoảng trắng là nhãn nghiệp vụ trong PDF. Mã trạng thái lưu/trao đổi được chuẩn hóa nhất quán, ví dụ `PendingPayment`, `UnpaidCOD`, `RefundPending`; không trộn nhãn hiển thị với mã API. Cần chuyển đổi dữ liệu `AwaitingPayment` cũ có kiểm chứng.

Kiểm thử: `tests/integration/test_checkout_stock.py`, `tests/integration/test_hold_expiry.py`, `tests/integration/test_order_recovery.py`.

Nghiệm thu: 10 đơn vị/50 checkout đồng thời có tối đa 10 cam kết hợp lệ; lỗi giữa chừng không tạo đơn/hold mồ côi; restart không gia hạn hold; hết hạn được phản ánh trong 60 giây; COD không bị job hết hạn online hủy.

### Giai đoạn 3 — Đóng gói, thanh toán và giao hàng

#### 3A. Đóng gói, serial, xuất kho và hàng trả đã được duyệt

Actor: Warehouse Staff, Shipping Provider mô phỏng. UC09, UC21; FR19, FR21, FR32, FR34.

| Loại | File dự kiến | Nội dung |
|---|---|---|
| Tạo | `View/application/view/FulfilmentView.tsx`, `View/application/view/ReturnReceiptView.tsx` | Chọn thiết bị, Packing/Packed/Dispatch; ghi nhận hàng trả theo phê duyệt ngoài hệ thống. |
| Tạo | `OrderItemDevice.py`, `ReturnReceipt.py`, `ReturnItem.py`, `ReturnItemDevice.py` trong `Model/application/entity/` | Lịch sử liên kết thiết bị–đơn và kết quả kiểm tra hàng trả. |
| Tạo | `Model/application/contract/IReturnReceipt.py`, `Model/application/service/ReturnReceiptService.py`, `DAO/contract/ReturnDAO.py`, `DAO/application/dao/ReturnDAOImpl.py` | Ghi nhận số lượng được nhận lại, hàng bán được và hàng cách ly, liên kết đơn/thiết bị cũ. |
| Sửa | `IFulfilment.py`, `FulfilmentService.py`, `OrderLifecycleService.py`, `InventoryService.py`, `InventoryDAO.py`, `InventoryDAOImpl.py` ở các thư mục trên | Kiểm tra cam kết/serial, ghi Packed, xuất Q và A cùng lúc; lưu liên kết lịch sử thiết bị. |
| Sửa | `StaffController.py`, `InventoryController.py`, `Order.py`, `StaffView.tsx`, `bootstrap.py` | API/màn hình theo đúng quyền, trạng thái và lịch sử. |

Không trừ Q ở Packing hoặc Packed. Chỉ Dispatched mới trừ Q và A cùng lúc, đúng một lần. Thiếu vận đơn thì không dispatch. Hàng trả chỉ tăng Q sau khi đã nhận và được xác nhận bán được; không tự hoàn tiền vì có hàng trả.

Kiểm thử: `tests/integration/test_packing_dispatch.py`, `tests/integration/test_device_identifiers.py`, `tests/integration/test_return_receipts.py`. Kiểm tra xuất lặp, serial bị dùng cho hai đơn, thiếu serial, trả trùng và thiết bị cách ly.

#### 3B. Thanh toán, kết quả chưa rõ/đến muộn và hoàn tiền

Actor: Customer, Sales Staff, Payment Provider mô phỏng. UC05, UC19–20, UC18; FR15–16, FR33.

| Loại | File dự kiến | Nội dung |
|---|---|---|
| Tạo | `View/application/view/PaymentOperationsView.tsx`, `View/application/view/PaymentProviderView.tsx` | Sales tra soát/hoàn tiền; trang provider mô phỏng thao tác thanh toán, không thu thập thẻ thật. |
| Tạo | `Controller/application/controller/PaymentOperationsController.py`, `Controller/application/controller/ProviderEventController.py` | API nghiệp vụ sales và nhận callback mô phỏng đã xác thực. |
| Tạo | `PaymentAttempt.py`, `PaymentEvent.py`, `Refund.py` trong `Model/application/entity/` | Từng lần thanh toán, sự kiện nhận được và nghĩa vụ/kết quả hoàn tiền. |
| Tạo | `Model/application/contract/IRefund.py`, `Model/application/service/RefundService.py`, `DAO/contract/RefundDAO.py`, `DAO/application/dao/RefundDAOImpl.py` | Yêu cầu hoàn tiền và xử lý kết quả độc lập với trạng thái hủy đơn. |
| Tạo | `Model/application/dto/ProviderEvent.py`, `Model/application/dto/RefundOutcome.py` | Hợp đồng sự kiện/refund đã chuẩn hóa, không lộ cấu trúc provider vào entity/service khác. |
| Tạo | `infrastructure/application/simulation/SimulatedProviderStore.py` | Nhật ký mô phỏng bền vững trong `data/simulation/`; tra soát sau restart không dựa vào trí nhớ của tiến trình. |
| Sửa | `IPayment.py`, `IPaymentGateway.py`, `PaymentService.py`, `PaymentDAO.py`, `PaymentDAOImpl.py`, `PaymentOutcome.py`, `SimulatedPaymentGateway.py` ở các thư mục hiện có | Authorize/query/refund/verify event; giữ Payments là summary và lưu attempt/event riêng. |
| Sửa | `OrderLifecycleService.py`, `OrderController.py`, `CheckoutView.tsx`, `StaffView.tsx`, `bootstrap.py` | Xử lý tiền đến sau hết hạn/hủy; hiển thị nghĩa vụ hoàn tiền và trạng thái thực tế. |

Timeout là `Unknown`, không là decline. Không thu lần nữa khi attempt còn Unknown. Tiền đến muộn: đơn Cancelled luôn đi hoàn tiền; đơn Expired chỉ xác nhận sau khi phân bổ lại thành công, nếu không thì hoàn tiền. Callback trùng chỉ có một hiệu lực. Tổng hoàn tiền không vượt số tiền đã được xác minh thu và chưa hoàn.

Luồng provider mô phỏng phải đi qua cùng hợp đồng xác minh sự kiện; không cho client chỉ gửi `status=Paid` để đổi trạng thái. Nhật ký provider mô phỏng tách khỏi sổ nghiệp vụ ứng dụng. Sự kiện hợp lệ được ghi bền vững trước acknowledgement và có thể áp dụng lại an toàn sau restart.

Kiểm thử: `tests/integration/test_payment_attempts.py`, `tests/integration/test_payment_reconciliation.py`, `tests/integration/test_refunds.py`, `tests/integration/test_provider_idempotency.py`, `tests/integration/test_payment_crash_recovery.py`.

#### 3C. Vận đơn, sự kiện giao hàng và đối soát COD

Actor: Warehouse Staff, Sales Staff, Shipping Provider mô phỏng. UC09, UC22–23; FR21–22, FR35.

| Loại | File dự kiến | Nội dung |
|---|---|---|
| Tạo | `View/application/view/ShippingProviderView.tsx`, `View/application/view/CODSettlementView.tsx` | Mô phỏng sự kiện carrier; màn hình Sales kiểm tra đối soát COD. |
| Tạo | `ShipmentEvent.py`, `CODSettlement.py` trong `Model/application/entity/` | Sự kiện vận chuyển và đối soát tiền COD. |
| Tạo | `Model/application/contract/ICODSettlement.py`, `Model/application/service/CODSettlementService.py`, `DAO/contract/CODSettlementDAO.py`, `DAO/application/dao/CODSettlementDAOImpl.py` | Kiểm tra số tiền, order và shipment trước ghi nhận thu COD. |
| Tạo | `Controller/application/controller/ProviderSimulationController.py`, `Model/application/contract/IProviderSimulation.py`, `Model/application/service/ProviderSimulationService.py` | Cổng thao tác mô phỏng có quyền; phát sự kiện provider qua đường xác minh chung, không cập nhật trực tiếp bảng Orders. |
| Sửa | `IShippingProvider.py`, `IFulfilment.py`, `FulfilmentService.py`, `ShipmentDAO.py`, `ShipmentDAOImpl.py`, `ShipmentStatus.py`, `SimulatedShippingProvider.py` ở các thư mục hiện có | Gửi đủ người nhận/điện thoại/kiện hàng/phương thức/COD; lưu sự kiện và không lùi trạng thái. |
| Sửa | `ProviderEventController.py`, `PaymentOperationsController.py`, `CheckoutView.tsx`, `StaffView.tsx`, `bootstrap.py` | Callback, staff fallback có audit, theo dõi đơn và đối soát. |

Delivered không tự làm payment COD thành Paid. Một settlement chỉ có hiệu lực sau khi khớp tham chiếu và số tiền. Có thể dùng chức năng staff fallback khi không nhận được sự kiện, nhưng phải kiểm tra quyền và lưu nguồn cập nhật.

Kiểm thử: `tests/integration/test_shipment_events.py`, `tests/integration/test_cod_settlement.py`, `tests/smoke/payment_shipping_simulation.py`.

#### 3D. Hỗ trợ đơn hàng của nhân viên bán hàng

Actor: Sales Staff. UC08, UC18; FR13–14.

| Loại | File dự kiến | Nội dung |
|---|---|---|
| Tạo | `View/application/view/SalesOrdersView.tsx`, `Model/application/dto/StaffOrderDetails.py` | Danh sách/chi tiết đơn liên kết hồ sơ người mua, item snapshot, payment/attempt/refund và shipment trong quyền được cấp. |
| Sửa | `StaffController.py`, `ICheckout.py`, `CheckoutService.py`, `OrderDAO.py`, `OrderDAOImpl.py`, `OrderLifecycleService.py`, `StaffView.tsx`, `bootstrap.py` ở các thư mục hiện có | API chi tiết cho staff, tìm/lọc đơn và hủy trước Packing theo quyền Sales; tái sử dụng cùng luồng giải phóng/refund, không giả mạo customerID để gọi API khách hàng. |

Kiểm thử: `tests/integration/test_sales_order_support.py`: sales thấy đúng dữ liệu liên kết và hủy đúng điều kiện; warehouse/manager không mặc nhiên có quyền hủy/hoàn tiền; khách hàng không đọc được đơn của người khác qua đường staff.

### Giai đoạn 4 — Báo cáo và cảnh báo tồn thấp

Actor: Manager; Warehouse Staff xem số liệu kho trong quyền được giao. UC11; FR20, FR26.

| Loại | File dự kiến | Nội dung |
|---|---|---|
| Tạo | `View/application/view/ReportsView.tsx`, `View/application/view/LowStockAlertsView.tsx`, `Controller/application/controller/ReportController.py` | Bộ lọc thời gian/brand/category, bảng/biểu đồ và tải CSV/PDF. |
| Tạo | `Model/application/contract/IReporting.py`, `Model/application/service/ReportingService.py`, `DAO/contract/ReportDAO.py`, `DAO/application/dao/ReportDAOImpl.py` | Truy vấn và tổng hợp số liệu theo BR12, giới hạn quyền. |
| Tạo | `Model/application/dto/SalesReportData.py`, `Model/application/dto/InventoryReportData.py` | Kết quả báo cáo và thời điểm/bộ lọc áp dụng; không phải bảng dữ liệu mới. |
| Tạo | `Model/application/entity/LowStockAlert.py`, `Model/application/contract/ILowStockAlerts.py`, `Model/application/service/LowStockAlertService.py`, `DAO/contract/LowStockAlertDAO.py`, `DAO/application/dao/LowStockAlertDAOImpl.py` | Cảnh báo theo ngưỡng V; chống tạo cảnh báo lặp khi SKU vẫn ở cùng trạng thái thiếu hàng. |
| Tạo | `Model/application/contract/IReportExport.py`, `infrastructure/application/reporting/ReportExporter.py` | Xuất CSV/PDF từ cùng dữ liệu báo cáo. |
| Sửa | `InventoryService.py`, `OrderLifecycleService.py`, `StaffView.tsx`, `bootstrap.py`, `requirements-app.txt` nếu cần thư viện PDF | Kiểm tra ngưỡng sau thay đổi kho/cam kết và nối chức năng báo cáo. |

Doanh số hàng hóa: đơn đã xác nhận, không hủy, theo ngày đặt; trừ giảm giá hàng, không cộng ship. Tiền thực thu/hoàn: theo ngày kết quả được xác minh. Tồn: theo thời điểm snapshot; biến động: theo thời điểm phát sinh. Không trình bày tiền COD chưa đối soát là tiền đã thu, không gọi doanh số là lợi nhuận.

Không tạo bảng SalesReport/InventoryReport chỉ để sao chép dữ liệu nguồn; báo cáo được tính từ đơn, payment/refund/settlement và sổ kho. Cảnh báo hiển thị trong ứng dụng; chưa cần gửi email/SMS thật.

Kiểm thử: `tests/unit/test_report_measures.py`, `tests/integration/test_reporting.py`, `tests/integration/test_low_stock_alerts.py`, `tests/smoke/report_export.py`.

Nghiệm thu: dữ liệu rỗng, đơn hủy, giảm giá, ship, COD chưa thu, refund khác ngày, movement lặp; CSV và PDF khớp tổng; user không có quyền không lấy được báo cáo; bổ sung hàng giải quyết cảnh báo cũ và cho phép cảnh báo đợt thiếu mới.

### Giai đoạn 5 — Địa chỉ, voucher và review

#### 5A. Sổ địa chỉ và phí giao hàng

Actor: Customer. UC17, UC03–04; FR03, FR10–12.

| Loại | File dự kiến | Nội dung |
|---|---|---|
| Tạo | `View/application/view/AddressBookView.tsx`, `Model/application/entity/CustomerAddress.py` | Nhiều địa chỉ, người nhận/điện thoại và chọn mặc định. |
| Tạo | `Model/application/contract/IAddressBook.py`, `Model/application/service/AddressBookService.py`, `DAO/contract/AddressDAO.py`, `DAO/application/dao/AddressDAOImpl.py` | Quyền sở hữu địa chỉ, chuyển địa chỉ mặc định và archive. |
| Tạo | `Model/application/contract/IDeliveryPricing.py`, `Model/application/service/DeliveryPricingService.py` | Tính phí và kiểm tra vùng/phương thức theo cấu hình demo; không gọi dịch vụ vận chuyển thật. |
| Sửa | `AccountController.py`, `CartController.py`, `OrderController.py`, `CheckoutService.py`, `CartService.py`, `CheckoutView.tsx`, `CartView.tsx`, `StaffView.tsx`/điều hướng khách hàng, `bootstrap.py` | Chọn địa chỉ, cập nhật ước tính và lưu snapshot cuối; bổ sung DTO địa chỉ/phí vào hợp đồng HTTP. |

Địa chỉ trong đơn là snapshot; sửa/xóa địa chỉ trong sổ không thay đơn cũ. Dữ liệu địa chỉ mặc định cũ được backfill một lần, không tạo trùng khi chạy lại migration.

Kiểm thử: `tests/integration/test_address_book.py`, `tests/integration/test_delivery_pricing.py`, `tests/smoke/address_checkout.py`.

#### 5B. Voucher và tính tiền cuối cùng

Actor: Administrator và Customer. UC13, UC03–04; FR10, FR24–25.

| Loại | File dự kiến | Nội dung |
|---|---|---|
| Tạo | `View/application/view/VoucherAdminView.tsx`, `Controller/application/controller/VoucherController.py` | Quản trị voucher và API kiểm tra mã cho khách hàng. |
| Tạo | `Voucher.py`, `VoucherProduct.py`, `VoucherRedemption.py` trong `Model/application/entity/` | Voucher, sản phẩm áp dụng và lượt giữ/sử dụng. |
| Tạo | `Model/application/contract/IVoucher.py`, `Model/application/service/VoucherService.py`, `DAO/contract/VoucherDAO.py`, `DAO/application/dao/VoucherDAOImpl.py`, `Model/application/dto/PricingSummary.py` | Kiểm tra hiệu lực/điều kiện, chống vượt lượt và tính giảm giá. |
| Sửa | `CartService.py`, `CheckoutService.py`, `OrderLifecycleService.py`, `OrderDAOImpl.py`, `CartView.tsx`, `CheckoutView.tsx`, `StaffView.tsx`, `bootstrap.py` ở các thư mục tương ứng | Áp mã tùy chọn, ước tính lại và chốt số tiền bằng dữ liệu server; lưu snapshot voucher. |

Voucher không bắt buộc. Mã sai phải có lý do và cho phép bỏ mã. Lượt giữ/sử dụng phải cùng transaction với order/hold; trả lại lượt đang giữ khi đơn hết hạn/hủy theo chính sách. Tổng tiền `itemSubTotal − discountAmount + shippingFee`, không âm. Giảm giá được phân bổ vào item snapshot để báo cáo theo brand/category không bị sai; không tin số tiền giảm do client gửi.

Kiểm thử: `tests/unit/test_voucher_rules.py`, `tests/integration/test_voucher_concurrency.py`, `tests/integration/test_checkout_pricing.py`.

#### 5C. Đánh giá sản phẩm sau giao hàng

Actor: Customer. UC07; FR23 (Could trong PDF).

| Loại | File dự kiến | Nội dung |
|---|---|---|
| Tạo | `View/application/view/ProductReviewSection.tsx`, `Controller/application/controller/ReviewController.py` | Hiển thị nhận xét và gửi review từ sản phẩm/đơn đủ điều kiện. |
| Tạo | `Model/application/entity/Review.py`, `Model/application/contract/IReview.py`, `Model/application/service/ReviewService.py`, `DAO/contract/ReviewDAO.py`, `DAO/application/dao/ReviewDAOImpl.py` | Kiểm tra đơn của người gửi đã Delivered, rating 1–5 và giới hạn một review/order item. |
| Sửa | `MainView.tsx`, `CheckoutView.tsx`, `bootstrap.py` tại thư mục hiện có | Gắn phần nhận xét và liên kết đánh giá trong đơn đã giao. |

Kiểm thử: `tests/integration/test_verified_purchase_reviews.py`, `tests/smoke/product_review.py`: chặn khách chưa mua, đơn chưa giao, đơn của người khác và review trùng; không dùng review làm dữ liệu cá nhân hóa recommendation.

## 5. Database: bảng mới dự kiến

**Cần thêm bảng và thuộc tính.** Dưới đây là phương án quan hệ đủ lưu các nghiệp vụ đã yêu cầu, không phải cam kết rằng ERD hiện tại đã có chúng. Có thể gộp tên lớp/DAO theo nhóm chức năng, nhưng không gộp nhiều giao dịch lịch sử vào một trường trạng thái duy nhất.

Tất cả ID mới dùng kiểu khớp FK hiện có; tiền dùng DECIMAL, thời điểm UTC dùng DATETIME, không dùng FLOAT cho tiền. Tên SQL trên Windows có thể hiển thị chữ thường.

| Giai đoạn | Bảng mới đề xuất | Khóa và thuộc tính chính | Quan hệ/mục đích |
|---|---|---|---|
| 1 | `AuditLogs` | `auditID` PK; actorType User/System, `actorAccountID` FK nullable cho job hệ thống; action, entityType/entityReference, beforeData/afterData JSON, createdAt | Accounts 0..1 — AuditLogs 0..*. Thao tác người dùng bắt buộc có account; thao tác tự động ghi rõ nguồn System/job. Tham chiếu đối tượng được audit là tham chiếu đa loại có kiểm soát, không giả vờ là FK đến mọi bảng. |
| 2 | `InventoryBalances` | `articleID` PK/FK; physicalQty Q, heldQty H, allocatedQty A, reorderThreshold, version, updatedAt | Products 1 — InventoryBalances 0..1. V tính từ Q−H−A, không có một cột V cho phép sửa độc lập. |
| 2 | `StockCommitments` | commitmentID PK; orderID/articleID FK; quantity, kind Hold/Allocation, status, expiresAt, createdAt | UNIQUE(orderID, articleID). Chuyển hold sang allocation trên cùng cam kết; giữ bản ghi khi released/consumed. |
| 2 | `GoodsReceipts` | receiptID PK; receiptReference UNIQUE; supplierDocumentReference, createdByAccountID FK, createdAt | Một phiếu nhập có nhiều dòng. Nhà cung cấp chưa cần tài khoản/bảng quản trị procurement. |
| 2 | `GoodsReceiptItems` | receiptItemID PK; receiptID/articleID FK; quantity; UNIQUE(receiptID,articleID) | Dòng nhập làm căn cứ số lượng và thiết bị. |
| 2 | `StockMovements` | movementID PK; articleID FK; eventKey UNIQUE; movementType, quantityDelta, balanceBefore/After, reason, actorAccountID FK, receiptItemID/orderItemID FK tùy loại, createdAt | Lịch sử nhập/kiểm kê/xuất/trả. FK `returnItemID` được bổ sung khi có bảng ReturnItems ở giai đoạn 3. |
| 2 | `DeviceIdentifiers` | deviceID PK; articleID/receiptItemID FK; serialNumber UNIQUE khi có, imei UNIQUE khi có; status, createdAt | Nhận diện từng thiết bị của SKU quản lý serial. Không dùng articleID để thay cho serial của từng chiếc. |
| 3 | `OrderItemDevices` | bindingID PK; orderItemID/deviceID FK; bindingStatus, packedAt, dispatchedAt, releasedAt | Lưu lịch sử gắn thiết bị với dòng đơn; UNIQUE(orderItemID,deviceID). Ràng buộc unique có điều kiện bằng cột generated nullable cho device đang được gắn hiệu lực, kết hợp khóa dòng khi bind. Hàng trả có thể gắn lại sau nhưng không xóa liên kết cũ. |
| 3 | `ReturnReceipts` | returnID PK; orderID FK; approvalReference UNIQUE, receivedByAccountID FK, createdAt | Ghi nhận phiếu trả đã được duyệt bên ngoài. |
| 3 | `ReturnItems` | returnItemID PK; returnID/orderItemID FK; quantity, sellableQuantity, quarantinedQuantity, inspectionReason | Không trả vượt lượng đã giao trừ lượng đã nhận trả trước đó; chỉ phần sellable tạo tăng Q. |
| 3 | `ReturnItemDevices` | (returnItemID,deviceID) PK/FK; orderItemDeviceID FK | Serial trả phải thuộc dòng đơn đã giao; giữ liên kết lịch sử thiết bị. |
| 3 | `PaymentAttempts` | attemptID PK; paymentID FK; requestReference UNIQUE, providerTransactionCode UNIQUE khi có, amount, currency, status, createdAt, verifiedAt | Payments 1 — PaymentAttempts 0..*. Summary Payment vẫn duy nhất/order. |
| 3 | `Refunds` | refundID PK; attemptID FK; refundReference UNIQUE, amount, currency, reason, status, requestedByAccountID FK khi là thao tác staff, requestedAt, verifiedAt | Gắn hoàn tiền với lần thu đã xác minh; nhiều refund có thể thuộc một attempt nhưng tổng không vượt tiền có thể hoàn. |
| 3 | `PaymentEvents` | paymentEventID PK; providerEventReference UNIQUE; attemptID/refundID FK tùy loại, eventType, amount/currency, occurredAt, receivedAt, appliedAt, payloadDigest | Sự kiện đã xác thực, đúng tham chiếu; mỗi event thanh toán/refund phải trỏ đúng một loại đối tượng. Chống ghi nhận hiệu lực hai lần và phục hồi sau lỗi. |
| 3 | `ShipmentEvents` | shipmentEventID PK; shippingID FK; providerEventReference UNIQUE; status, source Provider/Staff, actorAccountID FK khi staff, occurredAt, receivedAt | Shipments 1 — ShipmentEvents 0..*. Không chỉ ghi đè trạng thái cuối rồi mất lịch sử. |
| 3 | `CODSettlements` | settlementID PK; orderID UNIQUE/FK; shippingID FK; providerReference UNIQUE; expectedAmount, receivedAmount, status, verifiedByAccountID FK, receivedAt, verifiedAt | Đối chiếu đúng đơn/vận đơn và số tiền; bản ghi nhận được nhưng chưa khớp chưa được làm Payment thành Paid. |
| 4 | `LowStockAlerts` | alertID PK; articleID FK; thresholdSnapshot, availableSnapshot, status, createdAt, resolvedAt | Một cảnh báo mở/SKU; dùng unique cột generated cho cảnh báo Active để chống spam, cho phép đợt cảnh báo sau khi đã bổ sung hàng. |
| 5 | `CustomerAddresses` | addressID PK; customerID FK; recipientName/Phone, addressLine, serviceAreaCode, isDefault, isActive, createdAt | Customer 1 — CustomerAddresses 0..*. Đảm bảo tối đa một địa chỉ mặc định hoạt động/customer. |
| 5 | `Vouchers` | voucherID PK; code UNIQUE, discountType/value, minimumSubtotal, maximumDiscount, validFrom/To, usageLimit, perCustomerLimit, isActive | Điều kiện giảm giá; không xóa voucher đã được đơn tham chiếu. |
| 5 | `VoucherProducts` | (voucherID,articleID) PK/FK | Quan hệ n–n voucher và SKU đủ điều kiện; chính sách toàn danh mục phải được biểu diễn rõ, không suy đoán từ dữ liệu thiếu. |
| 5 | `VoucherRedemptions` | redemptionID PK; voucherID/customerID/orderID FK, orderID UNIQUE; status Reserved/Consumed/Released, reservedAt, consumedAt/releasedAt | Một voucher/đơn trong phạm vi demo; khóa voucher và kiểm tra lượt khi checkout. Một customer có nhiều lượt qua các đơn. |
| 5 | `Reviews` | reviewID PK; orderItemID UNIQUE/FK, customerID/articleID FK; rating, content, createdAt, updatedAt | Ownership và articleID phải khớp OrderItem/Order gốc; chỉ đơn Delivered được review. |

Tổng phương án hiện tại: **22 bảng nghiệp vụ mới**. Thêm một bảng kỹ thuật `SchemaMigrations(version PK, checksum, appliedAt)` để quản lý migration, không đưa bảng kỹ thuật này thành actor/use case nghiệp vụ. Nếu giữ toàn bộ đề xuất thì database tăng từ 16 lên **39 bảng**, chưa tính bất kỳ phương án Role/Permission riêng nào vì chưa đề xuất tạo chúng. Đây là hệ quả của việc mở rộng đến đầy đủ các FR kho/tài chính, cần được duyệt cùng ERD trước triển khai.

### 5.1. Bảng hiện có cần bổ sung hoặc chuẩn hóa

| Bảng | Dự kiến thay đổi | Lý do |
|---|---|---|
| `Accounts` | Mở rộng role; giữ accountID/email/passwordHash/isActive và quan hệ hiện có trong lúc chưa chốt cardinality mới. | Phân quyền FR27. Không tự bỏ UNIQUE(customerID). |
| `AuthSessions` | Giữ quan hệ accountID; dùng cơ chế thu hồi hiện có khi khóa/đổi quyền. | Không cần thêm loại phiên đăng nhập khác chỉ vì có nhiều vai trò. |
| `Products` | Thêm `warrantyMonths` nullable, `requiresSerialTracking` boolean và `version` cho cập nhật cạnh tranh; tiếp tục warrantyTerms và embedding hiện có. | Bảo hành có cấu trúc, xác định SKU cần serial và tránh ghi đè sửa giá. Không thêm một stockQty độc lập với InventoryBalances. |
| `Categories` | Giữ specificationSchema; kiểm tra dữ liệu và chuẩn hóa schema qua service. | Không tạo lại Categories hoặc bảng thông số chỉ để đổi tên. |
| `Orders` | Dùng holdExpireAt hiện có; chuẩn hóa trạng thái Pending Payment/Confirmed/Packing/Packed/Dispatched/Delivered/Cancelled/Expired; thêm shippingMethod, delivery snapshot có cấu trúc, voucherCodeSnapshot nullable, updatedAt/confirmedAt/packedAt/dispatchedAt/cancelledAt khi cần. | Lưu tiến trình và thông tin tại thời điểm mua; không tạo cột expiry trùng nghĩa. |
| `OrderItems` | Thêm discountAmount, brandSnapshot, categoryIDSnapshot (FK tới Categories), categoryNameSnapshot, warrantyMonthsSnapshot nullable; giữ giá/spec/warranty snapshot hiện có và kiểm tra tổng dòng đơn. | Báo cáo theo brand/category lúc mua, phân bổ giảm giá và bảo hành; Product đổi thông tin không làm thay đổi số liệu đơn cũ. |
| `Payments` | Giữ UNIQUE(orderID); chuẩn hóa status, thêm updatedAt nếu cần. Từng attempt/refund lưu bảng con. | Không bỏ quan hệ một summary/order để thay bằng ghi đè thông tin các lần thu. |
| `Shipments` | Giữ UNIQUE(orderID); thêm shippingMethod, codCollectionAmount, recipient/parcel snapshot, createdAt/updatedAt nếu cần. | Vận đơn đủ dữ liệu và có lịch sử riêng. Không tự đổi sang nhiều shipment/order trong phạm vi này. |
| `Cart` | Có thể thêm selectedVoucherID FK nullable ở giai đoạn 5; địa chỉ dùng để ước tính có thể là dữ liệu request, không tạo cam kết kho. | Giỏ lưu lựa chọn, checkout vẫn revalidate tất cả. |
| `Customer` | Giữ shippingAddress cũ trong quá trình chuyển đổi; tạo sổ địa chỉ từ dữ liệu hiện có theo migration/backfill rõ ràng. | Không xóa địa chỉ cũ trước khi kiểm tra dữ liệu mới. |
| Các bảng Search | Không đổi cấu trúc chỉ để triển khai các chức năng thương mại này. | Giữ hệ thống AI đã thống nhất. |

Chưa cần bảng OrderStatus cho danh sách trạng thái cố định, bảng Report để sao chép kết quả, hoặc bảng Brands nếu chỉ lưu tên chuẩn hóa. Không thêm dữ liệu mới vào technicalSpecs để giả làm sổ kho, thanh toán, voucher hay quyền truy cập.

## 6. Migration dự kiến và bảo toàn dữ liệu

Các file dưới đây **chưa được tạo hoặc chạy**:

| File dự kiến | Nội dung |
|---|---|
| `database/migrations/003_access_catalogue_audit.sql` | AuditLogs; role; các trường quản trị/bảo hành; hạ tầng SchemaMigrations. |
| `database/migrations/004_inventory_checkout.sql` | Bảng kho, receipt/serial, cam kết, movement; chuẩn hóa trường checkout. |
| `database/migrations/005_payment_fulfilment.sql` | Liên kết thiết bị/đơn, hàng trả, attempt/event/refund, COD, shipment events và các FK bổ sung. |
| `database/migrations/006_reporting_alerts.sql` | LowStockAlerts và index phục vụ báo cáo. |
| `database/migrations/007_addresses_vouchers_reviews.sql` | Địa chỉ, voucher, redemption, review; snapshot giảm giá. |
| `scripts/migrate_business.py` | Runner mới đọc version/checksum, preflight trạng thái schema và chạy từng migration có ghi nhận. |
| `scripts/seed_commerce_demo.py` | Seed có namespace/mã DEMO cho hoạt động nghiệp vụ, tách khỏi sản phẩm crawl; không chạy ngầm lúc app khởi động. |

`scripts/migrate.py` hiện chỉ tạo các bảng lõi và không xử lý ALTER, vì vậy không giả định runner cũ đã đủ dùng cho giai đoạn mở rộng. File `001_catalog.sql`/`002_application.sql` được giữ làm lịch sử; không sửa chúng để giả vờ migration mới đã chạy trên dữ liệu hiện có.

Trình tự: snapshot/backup → preflight schema/dữ liệu → thử trên database kiểm thử riêng → backfill có kiểm chứng → kiểm tra FK/unique/tổng tiền/số lượng → mới áp dụng lên database chính theo phạm vi được duyệt. DDL MySQL có implicit commit; không tuyên bố có thể rollback toàn bộ ALTER bằng một transaction Python. Có hướng dẫn phục hồi từ backup và đối chiếu migration dở dang, không dùng DROP để chạy lại.

Trước migration phải rà soát: vai trò staff cũ; order AwaitingPayment sang Pending Payment; Payment Pending có transactionCode chưa rõ kết quả; đơn chưa có cam kết/serial; warranty/delivery snapshot; giá trị null. Không tạo lịch sử tài chính hoặc tồn kho giả để lấp chỗ trống. Không dùng schema `ecommerce_electronics_demo` cũ làm đích triển khai.

## 7. Luồng phối hợp sau mở rộng

| Tác vụ | Luồng code dự kiến |
|---|---|
| Sửa giá | CatalogAdminView → CatalogAdminController → ICatalogAdministration → CatalogAdministrationService → ProductDAO + AuditDAO trong Unit of Work; sau commit invalidate biểu diễn liên quan. |
| Nhập kho | InventoryView → InventoryController → IInventory/InventoryService → InventoryDAO + AuditDAO → đánh giá ngưỡng cảnh báo. |
| Đặt online | CheckoutView → OrderController → ICheckout/CheckoutService → OrderLifecycleService + InventoryService + DAOs trong một transaction tạo order/hold → IPayment/PaymentService yêu cầu provider sau commit. |
| Thanh toán thành công | Provider mô phỏng → ProviderEventController → IPayment/PaymentService xác minh và ghi event → OrderLifecycleService chuyển hold thành allocation và xác nhận đơn trong transaction. |
| Hủy/hết hạn | OrderController hoặc OrderExpiryJob → IOrderLifecycle → khóa order/commitment → giải phóng một lần, giữ lịch sử; nếu có tiền thì tạo nghĩa vụ refund. |
| Đóng gói/xuất giao | FulfilmentView → StaffController → IFulfilment/FulfilmentService → IOrderLifecycle + IInventory + IShippingProvider → bind thiết bị, kiểm tra vận đơn, ghi movement khi dispatch. |
| Hoàn tiền | PaymentOperationsView → PaymentOperationsController → IRefund/RefundService → RefundDAO ghi yêu cầu → provider mô phỏng → callback xác minh → cập nhật kết quả refund. |
| Đối soát COD | CODSettlementView → PaymentOperationsController → ICODSettlement/CODSettlementService → so khớp Order/Shipment/Payment và ghi settlement một lần. |
| Báo cáo | ReportsView → ReportController → IReporting/ReportingService → ReportDAO → DTO → IReportExport nếu yêu cầu tải file. |
| Voucher | CartView/CheckoutView → controller tương ứng → CartService/CheckoutService → IVoucher/VoucherService; final pricing và lượt sử dụng được chốt cùng order/commitment. |

Không để View gọi DAO, simulator sửa trực tiếp Orders, hoặc entity tự tính và ghi tồn kho. Các interface và lớp mới cần được bổ sung vào package/component diagram và ERD khi thống nhất kế hoạch; chưa sửa hình trong bước lập kế hoạch này.

## 8. Nghiệm thu và tài liệu bàn giao

1. Mỗi giai đoạn phải có chức năng UI, API, service contract, DAO và migration tương ứng; không chỉ tạo các lớp rỗng theo tên trong kế hoạch.
2. Unit tests tập trung vào quyết định nghiệp vụ; integration tests chạy MySQL kiểm chứng transaction, cạnh tranh, FK và tính duy nhất; browser smoke kiểm chứng hành trình thật.
3. Các integration test nghiệp vụ sử dụng schema riêng được nhận diện rõ, dữ liệu fixture riêng; không ghi đơn/thanh toán giả vào database chính khi chạy test tự động. Không tự động xóa schema cũ để dọn test.
4. Bộ test hiện có, bao gồm Search/Recommendation và nhận diện ảnh theo nhãn cung cấp, phải tiếp tục pass sau mỗi thay đổi liên quan. Không thay threshold/nhãn để làm test thương mại pass.
5. Đo NFR theo phạm vi phù hợp, gồm quyền sở hữu dữ liệu, nhập trùng sự kiện, mất kết nối/restart và bất biến Q/H/A/V. Chưa có đo tải TP1/TP2 thì không báo đạt các chỉ tiêu tải lớn trong PDF.
6. Cập nhật `docs/design_code_mapping.md`, `docs/application_setup.md`, `docs/implementation_decisions.md`, `docs/implementation_verification.md` và sơ đồ sau khi giai đoạn được triển khai/nghiệm thu; ghi rõ khác biệt so với phiên bản thiết kế cũ.
7. Với các bảng/lớp đề xuất mới, cần duyệt phạm vi và điều chỉnh sơ đồ thiết kế trước phần code phụ thuộc. Việc lập file kế hoạch này chưa thay đổi schema, quyền tài khoản, dữ liệu tồn hay trạng thái đơn.

## 9. Truy vết yêu cầu

| FR | Giai đoạn thực hiện hoặc giữ lại |
|---|---|
| FR01–02 | Giữ đăng ký/đăng nhập; giai đoạn 1 mở rộng quyền và tài khoản staff. |
| FR03 | 5A: nhiều địa chỉ, hồ sơ tiếp tục dùng AccountService. |
| FR04–05 | 1B: quản trị danh mục/bảo hành; snapshot giữ khi checkout. |
| FR06 | Giữ Search đã triển khai. |
| FR07 | Giữ bộ lọc hiện có; 2A tích hợp tồn khả dụng. |
| FR08 | Giữ so sánh 2–4 sản phẩm; 1B/2A bổ sung bảo hành và dữ liệu hiển thị liên quan. |
| FR09 | Giữ CRUD cart, không giữ hàng chỉ vì thêm giỏ. |
| FR10 | 2B/5A/5B: tính lại và chốt tiền, phí giao hàng, discount. |
| FR11–12 | 2B: kiểm tra và tạo đơn/hold/snapshot trước provider; 5A/5B hoàn thiện địa chỉ/voucher. |
| FR13–14 | 2B/3A/3B: hủy có giải phóng/refund, hỗ trợ đơn theo quyền; giữ xem đơn của khách. |
| FR15–16 | 3B: attempt, sự kiện, tra soát và xử lý một lần. |
| FR17–18 | 2B: hold online, allocation COD và xác nhận sau thanh toán. |
| FR19 | 2A/3A: nhận serial tại nhập, bind khi đóng gói. |
| FR20 | 4: cảnh báo tồn thấp dựa trên biến động từ giai đoạn 2–3. |
| FR21–22 | 3C: vận đơn và sự kiện giao hàng. |
| FR23 | 5C: review sau giao hàng. |
| FR24–25 | 5B: quản trị và sử dụng voucher. |
| FR26 | 4: báo cáo và CSV/PDF. |
| FR27–28 | 1A/1C, tiếp tục ghi audit trong các giai đoạn sau. |
| FR29–30 | 2A: nhận hàng và điều chỉnh kho. |
| FR31 | 2B: giải phóng hold; 3B đối soát kết quả đến muộn. |
| FR32 | 3A: Packed và xuất kho một lần tại dispatch. |
| FR33 | 3B: nghĩa vụ và kết quả refund độc lập trạng thái hủy. |
| FR34 | 3A: ghi nhận kết quả hàng trả được duyệt ngoài hệ thống. |
| FR35 | 3C: đối soát COD. |
| FR36 | Giữ trang chi tiết; 1B/2A bổ sung bảo hành có cấu trúc và lượng khả dụng. |

Các FR-AIS01–05 và FR-AIR01–05 giữ trong phạm vi AI đã thống nhất; dữ liệu niêm yết/tồn khả dụng và cập nhật biểu diễn phải được nối đúng khi các chức năng thương mại mở rộng được triển khai.
