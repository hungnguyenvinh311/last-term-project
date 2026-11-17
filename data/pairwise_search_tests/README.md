# Thử nghiệm 10 cặp nhãn ảnh

Mở `index.html` để xem ảnh và kết quả từng cặp. Ảnh ghép gốc nằm trong `images/`, ảnh kèm toàn bộ bounding box nằm trong `detections/`. `report.json` lưu các nhãn, tọa độ, confidence và top 5 kết quả thực tế; `report.md` là bảng tóm tắt.

## Kết quả thật

| Nhóm nguồn | Số lượt | Nhãn mạnh nhất đúng | Search từ nhận diện đạt | Đối chiếu vùng/loại đã biết đạt |
|---|---:|---:|---:|---:|
| Điện thoại | 4 | 4 | 4 | 4 |
| Laptop | 4 | 4 | 4 | 4 |
| Tablet | 4 | 0 | 0 | 4 |
| Tai nghe | 4 | 0 | 0 | 4 |
| Đồng hồ | 4 | 0 | 0 | 4 |
| Tổng | 20 | 8 | 8 | 20 |

Trong 20 đối tượng cần kiểm tra, có 10 lượt mà nhãn mạnh nhất sai và 2 lượt không có vùng nhận diện phù hợp. Có 9/20 lượt xuất hiện ít nhất một nhãn đúng trong đúng ô ảnh, nhưng chỉ 8/20 có nhãn mạnh nhất đúng. Ví dụ ở `laptop__tablet`, nhãn điện thoại có confidence khoảng 0,622 còn nhãn tablet đúng chỉ khoảng 0,188. Nhãn đúng yếu hơn này được giữ trong báo cáo, không bị thay vào lượt search chính để làm test đạt.

Các lượt search chính dùng nguyên vùng và loại mà detector dự đoán. Khi detector gán tablet/đồng hồ thành điện thoại, backend vẫn giới hạn kết quả theo loại điện thoại đã được gửi; đây là lỗi phân loại trước truy xuất. Không có lượt nào trả sản phẩm ngoài loại được gửi trong 18 lượt search chính thực hiện được.

Các lượt đối chiếu dùng hình chữ nhật chứa ảnh nguồn và loại đúng đã biết khi ghép. Cả 20 lượt đều trả đúng nhóm và tìm thấy sản phẩm nguồn trong top 5. Kết quả này cho thấy retrieval hoạt động trên bộ đối chiếu có vùng/loại đúng, **không có nghĩa toàn bộ hệ thống nhận diện đạt 20/20**.

## Phạm vi và giới hạn

- 5 sản phẩm đại diện được chọn tự động bằng articleID nhỏ nhất đang hoạt động trong mỗi nhóm: 1, 21, 41, 61, 81. Không có ưu tiên ID nào trong thuật toán search.
- Mỗi nhóm ghép với 4 nhóm còn lại, tạo 10 cặp không lặp. Chỉ có một bố cục trái/phải và một sản phẩm cho mỗi nhóm.
- Ảnh query chỉ chứa hai ảnh nguồn đặt trên nền trắng. Không vẽ nhãn, ID hoặc đáp án lên ảnh query. Bounding box chỉ xuất hiện trên bản minh họa riêng.
- Vùng được ghép có tọa độ đã biết, nhưng chưa gán bounding box chính xác cho thân từng vật thể. Đối chiếu vị trí yêu cầu tâm khung nằm trong đúng ô và ít nhất 80% diện tích khung thuộc ô đó; đây không phải đánh giá object-box IoU tiêu chuẩn.
- Ảnh nguồn vốn đã có trong danh mục, nên tìm thấy sản phẩm nguồn trong top 5 là kiểm tra nhất quán, chưa phải đánh giá ảnh khách hàng độc lập.
- Detector dùng `google/owlvit-base-patch32`, ngưỡng 0,15, giữ nguyên 5 prompt đang chạy. Không điều chỉnh prompt/ngưỡng hoặc sửa nhãn sau khi xem kết quả để biến lỗi thành pass.
- Không gọi Gemini; không thay trọng số, dữ liệu danh mục hoặc lịch sử tìm kiếm demo. Các lượt search được ghi trong database test riêng `ecommerce_test_pair_24d3e1833d` và database này được giữ lại.

## Nhận xét

Nút thắt rõ nhất trong bộ thử này là phân loại/khả năng phát hiện của detector: tablet và chiếc đồng hồ đại diện thường thành điện thoại; tai nghe true-wireless có lượt bị bỏ sót. Một số hình quảng cáo còn bị nhận diện thêm các biểu tượng nhỏ. Cần thử nghiệm riêng cách mô tả nhãn cho tablet, earbuds và wristwatch, cùng các sản phẩm đại diện khác, trước khi quyết định thay model hoặc ngưỡng. Không nên tiếp tục đổi trọng số retrieval để chữa nhãn nhận diện sai.

## Chạy lại

```powershell
.\.venv-ai\Scripts\python.exe scripts/pairwise_image_search.py --output data/pairwise_search_tests_run2
```

Dùng thư mục mới: script từ chối ghi đè ảnh và kết quả cũ. Bộ kiểm thử phần mềm hiện đạt 136 test; con số này kiểm tra logic và bộ đánh giá, không thay thế kết quả thử nghiệm nhận diện 8/20 ở trên.
