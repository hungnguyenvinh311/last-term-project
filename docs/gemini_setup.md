# Gemini — phiên âm và trích xuất điều kiện

Ứng dụng mặc định dùng Gemini cho hai tác vụ riêng, qua `ITranscription` và `IIntentExtraction`. Các service tìm kiếm, encoder CLIP, detector, DAO, recommendation và database giữ nguyên trách nhiệm. Việc đổi provider không thay embedding hoặc cần migration dữ liệu.

## Cấu hình

Tạo key tại https://aistudio.google.com/api-keys rồi điền **trực tiếp trong `.env.app`**, không đưa vào chat, frontend hoặc Git:

```dotenv
APP_TRANSCRIBE_PROVIDER=gemini
APP_INTENT_PROVIDER=gemini
APP_GEMINI_API_KEY=YOUR_KEY_HERE
APP_GEMINI_TRANSCRIBE_MODEL=gemini-3.1-flash-lite
APP_GEMINI_INTENT_MODEL=gemini-3.1-flash-lite
```

Key/model Gemini được đọc lại mỗi request. Đổi provider cần khởi động lại backend. OpenAI key cũ được giữ trong file riêng tư nhưng không dùng khi provider là Gemini; không tự fallback sang OpenAI hoặc model trả phí khác.

Model mặc định hỗ trợ audio và structured output. Google hiện liệt kê Free tier cho model này; quota và quyền dùng tùy project, không cam kết miễn phí vô hạn. Kiểm tra project đang dùng Free tier nếu mục tiêu là không trả phí. Audio và nội dung tìm kiếm dùng Gemini được gửi tới Google; điều khoản dữ liệu của Free tier nằm trong trang pricing/terms của Google.

## Luồng và file

| Thành phần | Trách nhiệm |
|---|---|
| `Model/application/ai/GeminiClient.py` | Đọc key/model riêng tư, gọi REST `generateContent`, yêu cầu JSON theo schema, chuẩn hóa lỗi; key chỉ nằm trong header |
| `GeminiSpeechTranscriberService.py` | Triển khai ITranscription; gửi audio inline base64, lấy transcript, không tóm tắt hay tự trả lời |
| `GeminiIntentExtractorService.py` | Triển khai IIntentExtraction; trích category/brand/giá/điều kiện/thông số, xác thực bằng Pydantic |
| `IntentExtractorService.py` | Bộ quy tắc dự phòng; không tự coi là kết quả của Gemini |
| `bootstrap.py` | Ghép implementation vào SearchService; controller không gọi Google trực tiếp |

Voice: ghi âm → Gemini transcript → khách kiểm tra/sửa → bấm tìm kiếm → Gemini trích điều kiện → backend lọc và xếp hạng → lưu VoiceQuery cùng kết quả.

Text: Gemini trích điều kiện → bộ lọc bắt buộc → encoder/retrieval/ranking. Image + Text: Gemini phân tích phần text; ảnh vẫn do encoder cục bộ xử lý. Image không có text không cần gọi Gemini. Recommendation không dùng Gemini hoặc lịch sử khách hàng.

Không lấy đầu ra LLM làm SQL. Schema giới hạn 5 category, giá hữu hạn không âm, đơn vị kỹ thuật và phép so sánh hợp lệ; backend áp điều kiện lên dữ liệu đã xác minh. Kết quả bị chặn, rỗng, bị cắt hoặc sai schema không được coi là thành công. Schema đúng không tự bảo đảm hiểu đúng ý nghĩa; vẫn cần đánh giá bộ query thực tế.

Nếu Gemini lỗi hoặc thiếu key khi phân tích text, dùng quy tắc hiện có và hiển thị cảnh báo trong message/criteria.intentWarning; `criteria.intentProvider` ghi `rules`. Không suy rằng câu diễn đạt phức tạp đã được hiểu đầy đủ khi fallback. Muốn chỉ dùng quy tắc: `APP_INTENT_PROVIDER=rules` và restart.

Giọng nói không có transcript giả khi lỗi. UI báo lỗi key/quyền, quota, timeout hoặc định dạng. Audio inline tối đa 12 MB để chừa dung lượng base64 trong request; hỗ trợ WebM, WAV, MP3, M4A/MP4 audio, OGG và FLAC. Phiên âm và trích ý định là hai lượt gọi cho một lần voice search; hạn mức áp dụng cho từng lượt, bao gồm các lần tìm lại bằng bộ lọc.

## Kiểm tra

Không in key hoặc raw error của nhà cung cấp:

```powershell
.\.venv-ai\Scripts\python.exe scripts/check_gemini.py
```

Lệnh trên chỉ GET thông tin model, không sinh nội dung. Sau khi key hợp lệ, có thể thử một lượt trích ý định thật (dùng quota):

```powershell
.\.venv-ai\Scripts\python.exe scripts/check_gemini.py --text "điện thoại Samsung dưới 10 triệu RAM ít nhất 8 GB"
```

Kiểm thử tự động dùng HTTP MockTransport và MySQL test riêng, không dùng key thật. Browser/encoder smoke tests giữ bộ trích quy tắc để không tiêu tốn Gemini quota. Chỉ xác nhận gọi Google thật sau khi người dùng điền key; kiểm thử mô phỏng không phải bằng chứng chất lượng phiên âm tiếng Việt.

## Tài liệu chính thức đã đối chiếu

- https://ai.google.dev/gemini-api/docs/audio
- https://ai.google.dev/gemini-api/docs/structured-output?hl=en
- https://ai.google.dev/api/generate-content
- https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite
- https://ai.google.dev/gemini-api/docs/pricing

Các trang tài liệu Google hiện có thể chuyển hướng sang `aistudio.google.com/docs`. Adapter dùng endpoint REST công khai và httpx đã có trong requirements; không cần cài SDK Google hoặc tải thêm mô hình trên máy.
