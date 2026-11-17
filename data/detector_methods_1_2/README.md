# Thử cách 1 (padding) và cách 2 (mô tả nhãn)

Mở `index.html` để đối chiếu bốn cấu hình trên cùng ảnh. `report.json` giữ toàn bộ khung, confidence, prompt khớp và kết quả từng sản phẩm; `report.md` là bảng số liệu. `preregistered_conditions.json` lưu bộ prompt trước inference. Các ảnh có khung nằm trong `single_boxes/` và `pair_boxes/`.

## Cách hiểu tỷ lệ

Một trường hợp đạt khi khung phù hợp vùng sản phẩm có confidence cao nhất mang đúng loại. Vùng sản phẩm và quy tắc lọc khung được giữ từ lượt audit trước. Đây **không phải mAP hay tỷ lệ bbox đạt IoU ≥ 0,5**, vì chưa có bbox thân từng vật thể được gán nhãn chính xác. Chỉ có khung đúng nhưng yếu hơn khung sai không được tính là top1 đúng; chỉ số đó được lưu riêng dưới `correctLabelAvailable`.

## 40 ảnh đơn

| Cấu hình | Tablet | Đồng hồ |
|---|---:|---:|
| Hiện tại | 6/20 = 30% | 18/20 = 90% |
| Chỉ padding | 6/20 = 30% | 18/20 = 90% |
| Chỉ prompt mới | 6/20 = 30% | 17/20 = 85% |
| Padding + prompt mới | 6/20 = 30% | 17/20 = 85% |

Tất cả ảnh đơn đều vuông nên padding tạo đúng cùng pixel, không có tác dụng hình học. Tablet có 3 cặp dùng ảnh trùng; tính theo 17 ảnh nguồn duy nhất, cả bốn cấu hình đều đúng 3/17 ≈ 17,6%. Con số 30% là theo 20 sản phẩm, không phải theo ảnh duy nhất.

Prompt mới không sửa được lỗi tablet trong thử nghiệm này. Đồng hồ ID99 vốn có nhãn watch mạnh nhất chuyển sang headphones với prompt `a pair of earphones`, confidence khoảng 0,273. Ảnh minh họa được giữ nguyên. Do đó không đề xuất đưa bộ prompt này vào hệ thống đang chạy.

## 10 ảnh ghép

Trong bộ này, một tablet đại diện và một đồng hồ đại diện mỗi loại xuất hiện trong 4 cặp với các nhóm còn lại:

| Cấu hình | Tablet | Đồng hồ |
|---|---:|---:|
| Hiện tại | 0/4 | 0/4 |
| Chỉ padding | 0/4 | 4/4 |
| Chỉ prompt mới | 0/4 | 0/4 |
| Padding + prompt mới | 0/4 | 4/4 |

Kết quả hỗ trợ padding giữ tỷ lệ cho ảnh ghép, nhất là mẫu đồng hồ đại diện. 4/4 là cùng một mẫu trong bốn cặp, **không chứng minh mọi đồng hồ đều đạt 100%**. Bổ sung prompt còn giúp nhận đúng tai nghe trong cặp tai nghe–đồng hồ khi kết hợp padding, nhưng không cải thiện tablet và không khắc phục suy giảm ở ảnh đơn ID99.

## Thiết lập cố định

- Giữ nguyên `google/owlvit-base-patch32`, ngưỡng 0,15 và tối đa 12 khung.
- So sánh baseline, padding, prompts và combined. Padding thêm nền trắng thành vuông, không co giãn vật thể; tọa độ khung được đổi lại về ảnh gốc. Khung chỉ nằm trên phần đệm không được biến thành vật thể giả sau clip tọa độ.
- Mỗi nhóm có đúng ba mô tả trong prompt bank, tổng cộng 15 mô tả. Khung lấy nhãn prompt có điểm cao nhất rồi ánh xạ về 5 nhóm nghiệp vụ. Không thêm riêng nhiều prompt cho tablet/watch hơn các nhóm khác, không đổi prompt/ngưỡng theo kết quả đang thấy.
- Kết quả baseline 40 ảnh đơn được tái sử dụng sau kiểm tra SHA của ảnh, mã detector, model, prompt và ngưỡng đều khớp. Padding trên ảnh vuông được tái sử dụng vì pixel hoàn toàn giống nhau. Các điều kiện còn lại chạy thật; có 78 lượt inference mới.
- 10 ảnh ghép được kiểm tra đủ bốn cấu hình, bao gồm chạy lại baseline. Không thay nhãn sai bằng nhãn mong đợi khi đánh giá.
- Bộ này là development benchmark đã được quan sát trước; chưa phải tập test độc lập. Padding còn đổi kích thước tương đối/ngữ cảnh trong khung, nên không khẳng định riêng biến dạng tỷ lệ là nguyên nhân duy nhất.

## Kết luận triển khai

Padding là thay đổi có ích để cân nhắc cho ảnh không vuông, sau khi kiểm thử thêm các mẫu và ảnh ngoài. Bộ prompt đang thử chưa đáng áp dụng. Chưa có thay đổi nào được đưa vào detector chạy thật; không sửa danh mục, trọng số retrieval, database hay gọi Gemini. Vấn đề tablet vẫn cần giải pháp khác, như đánh giá detector khác hoặc huấn luyện bộ phân loại/phát hiện theo 5 nhóm.

Các test ánh xạ prompt, tọa độ padding, thống kê và hồi quy toàn hệ thống đạt 157/157; kết quả code pass không có nghĩa chất lượng nhận diện đạt yêu cầu.
