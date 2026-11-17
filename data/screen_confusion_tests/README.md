# Kiểm tra giả thuyết tablet/đồng hồ bị nhận thành mobile phone

Mở `index.html` để xem từng ảnh gốc/ảnh xám và toàn bộ bounding box. `report.json` giữ raw predictions, confidence, vùng đối chiếu, nhóm hình dạng và kết quả thống kê. `visual_traits_before_inference.json` lưu cách chia nhóm trước khi chạy. Ảnh đầu vào và ảnh vẽ khung nằm trong `images/` và `boxes/`.

## Kết quả 40 sản phẩm

Giữ nguyên `google/owlvit-base-patch32`, 5 prompt và ngưỡng 0,15. Có 20 tablet và 20 đồng hồ, tương ứng 37 ảnh nguồn duy nhất do ba cặp tablet dùng ảnh trùng. Có 80 lượt ảnh gốc/xám, tương ứng 74 đầu vào pixel duy nhất; không có lỗi chạy inference.

| Nhóm | N | Nhãn mạnh nhất vùng sản phẩm là phone | Có khung phone bất kỳ trong toàn ảnh |
|---|---:|---:|---:|
| Tablet | 20 | 10/20 = 50% | 14/20 = 70% |
| Đồng hồ | 20 | 2/20 = 10% | 3/20 = 15% |
| Trong đó đồng hồ vuông/chữ nhật | 9 | 2/9 = 22,2% | 3/9 = 33,3% |
| Đồng hồ tròn | 11 | 0/11 | 0/11 |

Tablet bị gán phone mạnh nhất: IDs 41, 42, 43, 44, 46, 49, 50, 51, 57, 58. Có 6 tablet được nhận đúng và 4 tablet thành laptop (47, 52, 53, 55); các ảnh có bàn phím/phụ kiện làm ngữ cảnh phức tạp hơn. Đồng hồ bị gán phone mạnh nhất là IDs 95 và 102; 18 đồng hồ còn lại có nhãn mạnh nhất đúng.

Nhóm quan sát là màn hình chữ nhật với giao diện nhiều màu gồm 27 sản phẩm: 20 tablet và 7 đồng hồ. Có 12/27 = 44,4% bị gán phone mạnh nhất; khi bỏ ảnh trùng là 12/24 = 50%. Phân nhóm giao diện là đánh giá thị giác của trợ lý, không phải nhãn chuẩn do người dùng xác nhận.

Như vậy bộ dữ liệu hiện tại chưa hỗ trợ giả thuyết tỷ lệ 90%. Có sự nhầm lẫn rõ giữa tablet và phone, còn màn hình vuông/nhiều màu không đủ để suy ra chắc chắn phone. Đây là thống kê trên ảnh danh mục hiện có, không đại diện mọi ảnh khách hàng.

## Đối chiếu bỏ màu

Ảnh xám vẫn có 13/40 trường hợp phone mạnh nhất so với 12/40 ảnh gốc. Sau khi bỏ ảnh trùng, cả hai điều kiện đều là 12/37. ID49 chuyển từ phone sang tablet; IDs56 và60 (cùng một ảnh) chuyển từ tablet sang phone. Vì vậy việc bỏ màu không giảm tỷ lệ nhầm tổng thể. Thử nghiệm này chưa chứng minh model bỏ qua màu hoàn toàn, nhưng không có cơ sở coi màu màn hình là nguyên nhân duy nhất.

## Đối chiếu tỷ lệ hình học

`pair_letterbox/index.html` và `pair_letterbox/report.json` chứa lượt chạy lại 10 ảnh ghép cũ. Hai nhánh đều dùng cùng model, prompt và ngưỡng:

| Điều kiện | Nhãn mạnh nhất đúng | Nhầm đối tượng không phải phone thành phone |
|---|---:|---:|
| Ảnh ghép ngang đưa thẳng vào processor | 8/20 | 10 |
| Đệm trắng thành vuông, giữ nguyên tỷ lệ vật thể | 12/20 | 5 |

Processor đang cài nhận `size={height:768,width:768}` và resize trực tiếp về hai chiều này. Với ảnh ghép 1200×600, tỷ lệ vật thể vì vậy thay đổi. Padding tạo đầu vào 1200×1200 trước resize, đồng thời thay đổi tỷ lệ vật thể trong toàn khung và phần nền. Kết quả hỗ trợ việc thử giữ tỷ lệ ảnh, nhưng không tách được tuyệt đối tác động hình dạng, kích thước và ngữ cảnh. Đây chỉ là đánh giá nhãn nhận diện; không chạy lại search cho nhánh padding.

Không áp dụng padding, đổi prompt, đổi model hoặc trọng số vào ứng dụng đang chạy trong nhiệm vụ này.

## Năm hướng khắc phục, theo ưu tiên đề xuất

1. **Giữ tỷ lệ ảnh bằng letterbox/padding**, rồi đổi tọa độ bbox về ảnh gốc đúng cách. Có bằng chứng cải thiện trực tiếp trên 10 ảnh ghép, nhưng cần thử thêm ảnh ngoài và nhiều mẫu sản phẩm.
2. **Cải thiện bộ mô tả nhãn và hiệu chỉnh theo lớp**: thử `tablet device`, `wristwatch with a strap`, `wireless earbuds in a charging case` cùng các mô tả tương đương, gom về 5 nhãn nghiệp vụ. Chọn trên validation tách biệt; không dùng ảnh test để chọn prompt hoặc chỉ tăng ngưỡng toàn cục. OWL-ViT nhận diện theo text query: https://huggingface.co/docs/transformers/en/model_doc/owlvit
3. **So sánh detector khác trên cùng benchmark**, chẳng hạn OWLv2 hoặc Grounding DINO. Chỉ thay khi cải thiện nhầm lớp, bỏ sót và tốc độ/RAM trên máy thực tế; tài liệu không bảo đảm chúng sẽ tốt hơn trên dữ liệu này. https://huggingface.co/docs/transformers/en/model_doc/owlv2 ; https://huggingface.co/docs/transformers/en/model_doc/grounding-dino
4. **Huấn luyện detector gọn cho đúng 5 nhóm** với bbox gán nhãn cho thân sản phẩm, bổ sung nhiều tablet/đồng hồ/earbuds, ảnh có phụ kiện và các ví dụ dễ nhầm. YOLO hỗ trợ dữ liệu tùy biến; cần chia tập theo model/ảnh nguồn và thêm ảnh độc lập, không coi 100 ảnh hiện có là đủ để chứng minh khả năng tổng quát. https://docs.ultralytics.com/tasks/detect/
5. **Kiểm tra lại crop và từ chối chốt nhãn khi mâu thuẫn**: dùng bước phân loại 5 nhóm hoặc đối chiếu độc lập; nếu chưa đồng thuận thì hiển thị các nhãn ứng viên để người dùng xác nhận. UI đã cho phép sửa loại; cải tiến thêm là tự đánh dấu nghi ngờ, thay vì mặc định tin nhãn phone có điểm cao nhất. Cách này giảm lỗi lan sang bộ lọc search, không thay thế việc nâng chất lượng detector.

Không khuyến nghị đổi trọng số cosine/keyword để sửa sai nhãn ở bước nhận diện.

## Giới hạn đo lường

Vùng đối chiếu là ROI thô được quan sát trước inference. Khung đánh giá phải có tâm trong ROI, ít nhất 70% diện tích thuộc ROI và diện tích tối thiểu 5% ROI để hạn chế logo nhỏ. Raw boxes đều được giữ lại và thống kê không lọc cũng nằm trong report. Chưa có bbox thân vật thể gán nhãn chính xác nên không báo mAP/IoU chuẩn hoặc khẳng định biết model đang dùng đặc trưng nội bộ nào.

Các thử nghiệm chỉ đọc ảnh/dữ liệu, không gọi Gemini hay thay database/danh mục. Chạy lại phải dùng thư mục output mới để giữ kết quả trước đó.
