# Nhiệm vụ Agent: Rà soát Class Diagram, thiết kế MySQL và thu thập dữ liệu sản phẩm điện tử

## 1. Bối cảnh và mục tiêu

Dự án là hệ thống E-commerce có chức năng **Search by Text, Search by Image và Search by Voice**. Người dùng đã thiết kế **Class Diagram trong Visual Paradigm** và muốn triển khai cơ sở dữ liệu **MySQL** (quản lý qua MySQL Workbench), sau đó thu thập một tập dữ liệu sản phẩm điện tử nhỏ để kiểm thử hệ thống.

**Nguyên tắc ưu tiên:** Class Diagram hiện có là tài liệu thiết kế đầu vào và là nguồn tham chiếu chính. Không tự ý thay thế bằng schema mẫu hoặc tái cấu trúc toàn bộ hệ thống. Tuy nhiên, Class Diagram là mô hình hướng đối tượng, không đồng nhất hoàn toàn với lược đồ quan hệ; cần ánh xạ hợp lý, giải thích rõ mọi khác biệt.

## 2. Đầu vào Agent phải đọc

1. Tìm và đọc **Class Diagram mới nhất** trong repository/project (file Visual Paradigm, ảnh xuất, PlantUML hoặc tài liệu liên quan). Xác định chính xác phiên bản đang được sử dụng; không dựa vào sơ đồ cũ nếu có phiên bản mới.
2. Đọc schema, migration, model, code và tài liệu hiện có (nếu có) để tránh xung đột.
3. Nếu không tìm thấy Class Diagram hoặc có nhiều phiên bản mâu thuẫn, **dừng bước thay đổi schema và yêu cầu người dùng cung cấp/xác nhận**; không tự suy đoán các entity hay thuộc tính.
4. Kiểm tra MySQL Server, phiên bản, kết nối và quyền thao tác. **MySQL Workbench không đồng nghĩa với việc MySQL Server đã được cài đặt/chạy.** Không đưa mật khẩu vào source code hoặc log.

## 3. Giai đoạn A — Phân tích Class Diagram trước khi triển khai

Lập bảng đối chiếu cho **tất cả class liên quan đến dữ liệu sản phẩm**, bao gồm:

- Tên class, trách nhiệm, thuộc tính, kiểu dữ liệu, khóa định danh dự kiến.
- Quan hệ, multiplicity, kế thừa, composition/aggregation, association class nếu có.
- Class nào là **persistent entity** cần lưu DB; class nào chỉ là controller, view, service, DAO hoặc đối tượng tạm và **không nên tạo bảng**.
- Các điểm chưa phù hợp với lưu trữ hoặc crawl dữ liệu: ví dụ thông tin ảnh, nguồn gốc dữ liệu, category, brand, thông số, giá, định danh sản phẩm, quan hệ sản phẩm–ảnh.
- Những bất nhất giữa Class Diagram và code/schema hiện có.

### Quy tắc thay đổi thiết kế

- **Giữ nguyên tên, ý nghĩa, cấu trúc và quan hệ hiện có ở mức tối đa**; không thêm cột/bảng chỉ vì một schema E-commerce thông dụng thường có chúng.
- Chỉ đề xuất **tối đa 1–2 class mới** nếu có nhu cầu rõ ràng, không thể biểu diễn hợp lý bằng class/thuộc tính sẵn có. Ví dụ `ProductImage` hoặc `CrawlSource` **chỉ là ứng viên**, không phải yêu cầu bắt buộc; nếu diagram đã có cấu trúc tương đương thì tái sử dụng.
- Phân biệt **thêm class trong Class Diagram** với **thêm bảng kỹ thuật trong MySQL**: quan hệ nhiều–nhiều hoặc chiến lược ánh xạ kế thừa có thể cần bảng trung gian mà không nhất thiết là domain class mới. Mọi bảng thêm phải có lý do.
- Với kế thừa, so sánh các cách ánh xạ phù hợp (single table, joined tables, concrete tables), chọn một cách dựa trên diagram thực tế; nêu trade-off, PK/FK và ràng buộc toàn vẹn.
- Nếu cần sửa diagram, lập **change proposal** gồm: hiện trạng → vấn đề → thay đổi tối thiểu → tác động đến code/DB/crawl. **Xin xác nhận trước khi sửa Class Diagram hoặc thực hiện thay đổi phá vỡ schema hiện hữu.**

**Đầu ra bắt buộc giai đoạn A:** `docs/class_diagram_db_mapping.md` với bảng mapping class ↔ table ↔ columns, quan hệ PK/FK, kiểu dữ liệu MySQL và danh sách thay đổi được đề xuất. Không được khẳng định đã xem diagram nếu chưa đọc được file thực tế.

## 4. Giai đoạn B — Thiết kế và tạo cơ sở dữ liệu MySQL

Sau khi có schema phù hợp với Class Diagram (và được duyệt nếu có thay đổi đáng kể):

1. Tạo SQL DDL hoặc migration có thể chạy lại an toàn trong môi trường phát triển, gồm `CREATE TABLE`, PK, FK, UNIQUE, NOT NULL, indexes cần thiết.
2. Dùng `utf8mb4` để hỗ trợ tiếng Việt. Dùng `DECIMAL` cho giá, kiểu dữ liệu phù hợp cho mô tả, URL và thông số; không dùng `FLOAT` cho tiền.
3. Bảo đảm quan hệ sản phẩm–danh mục và sản phẩm–ảnh phản ánh đúng multiplicity của diagram. Nếu một sản phẩm có nhiều ảnh, mỗi ảnh phải liên kết được về đúng sản phẩm.
4. Với embedding ảnh: **không bắt buộc lưu ngay ở bước crawl**. Nếu lưu trong MySQL, đề xuất cách lưu tương thích với phiên bản MySQL đang dùng (ví dụ JSON/BLOB), ghi rõ số chiều, model và cách tính similarity ở tầng ứng dụng; không giả định MySQL có sẵn `VECTOR(n)`.
5. Không lưu trực tiếp file ảnh vào bảng nếu không có lý do; ưu tiên lưu đường dẫn file/URL và metadata. Tách dữ liệu crawl thô khỏi dữ liệu đã chuẩn hóa.
6. Tạo script import có **transaction, upsert/deduplication**, kiểm tra FK và có thể chạy lại mà không nhân đôi dữ liệu.
7. **Không xóa hoặc ghi đè dữ liệu/bảng hiện có** khi chưa được người dùng chấp thuận. Có thể chuẩn bị migration và hướng dẫn chạy trước.

**Đầu ra:** SQL/migration, cấu hình mẫu `.env.example`, hướng dẫn tạo DB và import bằng MySQL Workbench hoặc CLI.

## 5. Giai đoạn C — Chọn nguồn và crawl dữ liệu điện tử

### Quy mô

Thu thập **20–30 sản phẩm thực tế cho mỗi category**. Danh mục gợi ý: Smartphone, Laptop, Tablet, Headphones, Smartwatch; **ưu tiên category đã có trong Class Diagram** và chỉ mở rộng nếu được chấp thuận. Tổng mục tiêu khoảng 100–150 sản phẩm nếu dùng 5 category. Ưu tiên 2–3 ảnh/sản phẩm khi có sẵn và được phép sử dụng; không ép đủ số ảnh bằng cách nhân bản.

### Chọn nguồn

1. Khảo sát các nguồn có sản phẩm điện tử (API/dataset được cấp phép hoặc website công khai); ưu tiên nguồn có metadata và ảnh phù hợp, nhất quán.
2. Kiểm tra **điều khoản sử dụng, robots.txt, quyền sử dụng ảnh, giới hạn truy cập** trước khi crawl. Ghi lại nguồn, thời điểm kiểm tra và kết luận; không coi website công khai là mặc nhiên cho phép crawl/tái sử dụng ảnh.
3. Ưu tiên API chính thức hoặc nguồn cho phép tái sử dụng. Không vượt CAPTCHA, đăng nhập, rate limit, cơ chế chống bot hoặc thu thập dữ liệu cá nhân.
4. Nếu nguồn không cho phép hoặc không rõ quyền, **không crawl nguồn đó**; đề xuất nguồn thay thế và hỏi người dùng nếu cần.
5. Trước khi chạy hàng loạt, crawl thử **3–5 sản phẩm** và báo cáo độ đầy đủ/đúng của các trường dữ liệu, tình trạng ảnh, khả năng truy cập.

### Trường dữ liệu

Thu thập các trường **có trong Class Diagram/schema được duyệt**; chỉ map những trường nguồn thực sự cung cấp. Các trường mong muốn để đánh giá độ phủ (không mặc định thêm hết vào schema): tên, category, brand, model, giá và đơn vị tiền tệ, mô tả, thông số, URL sản phẩm, URL ảnh, ảnh cục bộ, thời điểm thu thập.

- Không tự bịa giá, thông số, brand hoặc mô tả khi nguồn thiếu; để `NULL`/đánh dấu thiếu theo schema.
- Phân biệt sản phẩm với biến thể (màu, RAM, dung lượng) để tránh trùng không chủ ý.
- Chuẩn hóa giá, ký tự tiếng Việt, danh mục, tên thương hiệu và đơn vị thông số.
- Lưu `source_url` và thông tin nguồn để kiểm chứng. Nếu diagram không có trường tương ứng, đề xuất nơi lưu tối thiểu và giải thích.
- Chỉ tải ảnh được phép; kiểm tra URL, định dạng, kích thước, file hỏng và ảnh trùng. Giữ nguyên nguồn gốc ảnh.
- Không cần triển khai crawler định kỳ: một lần thu thập có thể đáp ứng đồ án.

### Công nghệ

Ưu tiên **Python + requests/BeautifulSoup** cho HTML tĩnh hoặc **Scrapy** nếu cần thu thập nhiều trang. Chỉ dùng Playwright khi trang tải động và việc tự động truy cập được cho phép. Có timeout, retry có giới hạn, delay, logging và checkpoint để tránh gửi yêu cầu quá mức.

## 6. Giai đoạn D — Kiểm thử và nghiệm thu

Kiểm tra tối thiểu:

- Số lượng sản phẩm **thực tế** theo từng category, mục tiêu 20–30; nếu không đạt phải nêu rõ lý do, không tạo dữ liệu giả để đủ số lượng.
- Tỷ lệ sản phẩm có tên, category, giá, mô tả, ảnh; số URL ảnh lỗi và sản phẩm trùng.
- PK/FK hợp lệ, không có bản ghi ảnh mồ côi, không nhân đôi sau khi import lại.
- Một số truy vấn SQL minh họa: liệt kê theo category, lọc giá/brand, tìm theo tên, lấy ảnh của một sản phẩm.
- Xác nhận ảnh hiển thị được từ đường dẫn lưu trong DB.
- Chỉ đánh giá khả năng chuẩn bị dữ liệu cho Image Retrieval; **không tự nhận đã triển khai mô hình embedding/tìm kiếm ảnh** nếu chưa thực hiện.

## 7. Deliverables và thứ tự thực hiện

1. `docs/class_diagram_db_mapping.md` — phân tích diagram, mapping, các thay đổi tối thiểu và lý do.
2. `docs/crawl_source_assessment.md` — nguồn khảo sát, quyền truy cập, khả năng lấy dữ liệu và nguồn được chọn.
3. `sql/` hoặc `migrations/` — schema/migration MySQL phù hợp với diagram đã xác nhận.
4. `crawler/` — mã nguồn crawl, chuẩn hóa, tải ảnh (nếu được phép), import MySQL; tách cấu hình khỏi code.
5. `data/` — JSON/CSV đã chuẩn hóa và ảnh hợp lệ (theo quy định bản quyền và giới hạn repo).
6. `docs/setup_and_validation.md` — hướng dẫn chạy trên Windows, cài dependency, cấu hình MySQL, kiểm thử, kết quả thực tế.

**Thứ tự bắt buộc:** Đọc diagram → báo cáo mapping & đề xuất thay đổi → xin duyệt nếu cần → kiểm tra nguồn và crawl mẫu → hoàn thiện schema/script → crawl đủ dữ liệu → import → kiểm thử. Nếu thiếu file hoặc chưa có quyền truy cập nguồn, dừng đúng bước và hỏi, không tự ý bỏ qua.

## 8. Tiêu chí hoàn thành

- Cấu trúc MySQL bám sát Class Diagram hiện có, mọi khác biệt đều có giải thích.
- Không tự ý thêm quá 1–2 domain class; các thay đổi có lý do và được duyệt khi ảnh hưởng thiết kế.
- Dữ liệu thu thập là dữ liệu thực, có nguồn kiểm chứng, không bịa hoặc sao chép ảnh trái phép.
- Mục tiêu 20–30 sản phẩm/category, có ảnh và metadata đủ dùng cho demo tìm kiếm.
- Script chạy lại được, không tạo bản ghi trùng và có báo cáo kiểm thử.
- Không đưa credential vào repository, không phá dữ liệu hiện có.

**Yêu cầu báo cáo:** Trước khi sửa mã nguồn hoặc database, Agent hãy tóm tắt Class Diagram đã đọc, các bảng dự kiến, đề xuất thêm/sửa class (nếu có), nguồn crawl dự kiến và các vấn đề cần người dùng quyết định.
