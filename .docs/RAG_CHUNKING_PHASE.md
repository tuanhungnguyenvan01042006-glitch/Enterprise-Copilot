# Kế hoạch Phase Chunking

## Mục tiêu

Chia tài liệu Markdown đã clean thành các chunk có ngữ cảnh heading, giới hạn token rõ ràng và giữ metadata để truy xuất nguồn trước khi embedding.

## Các bước

1. **Chuẩn bị dependency và tokenizer**
   - Thêm **langchain-text-splitters** và tokenizer tương thích với **voyage-4**.
   - Đo kích thước chunk theo token, không dựa mặc định vào số ký tự.

2. **Kiểm tra nội dung trước khi chunk**
   - Xử lý placeholder nội dung động và HTML còn sót; tài liệu thiếu nội dung chính cần được đánh dấu để xem lại.
   - Giữ alt text có ích của ảnh, bỏ cú pháp ảnh trang trí.

3. **Stage 1 — chia theo heading Markdown**
   - Bắt đầu với heading H2–H4; corpus hiện không có H1.
   - Giữ heading H5/H6 trong nội dung. Thử tách theo H5 riêng với values.md để kiểm tra truy xuất từng nguyên tắc.
   - Tạo section_path theo cấu trúc heading và giữ cả nội dung trước heading đầu tiên.

4. **Bảo toàn bảng và nội dung có cấu trúc**
   - Giữ bảng ngắn nguyên vẹn.
   - Khi chia bảng dài, chia theo hàng và lặp tên cột trong mỗi phần; không cắt giữa các ô.
   - Giữ code block ngắn nguyên vẹn; chỉ đưa Mermaid vào embedding khi sơ đồ có giá trị truy xuất.

5. **Stage 2 — chia section dài**
   - Chạy RecursiveCharacterTextSplitter riêng trên từng section, không cắt qua ranh giới heading.
   - Cấu hình thử đầu tiên: chunk_size=700 tokens, chunk_overlap=80 tokens.
   - So sánh thêm size 500/700/900 và overlap 0/80. Ưu tiên ranh giới đoạn, câu, heading con, list item và hàng bảng.
   - Thêm section_path vào từng chunk con để chunk vẫn đủ ngữ cảnh khi đứng riêng.

6. **Giữ metadata và lưu preview Development**
   - Giữ metadata tài liệu: document_id, knowledge_scope, department_id, title, category, storage_key.
   - Bổ sung section_path, chunk_index, vị trí nguồn và chunk_id ổn định.
   - Nối pipeline loader → cleaner → chunker; lưu kết quả riêng tại backend/storage/processed/chunks.

7. **Kiểm tra và chốt cấu hình**
   - Kiểm tra tài liệu ngắn, dài, nhiều heading và nhiều bảng; xem chunk của communication, chat, values, expenses và mental-health.
   - Tạo 30–50 câu hỏi có section nguồn kỳ vọng; so sánh Recall@5 và MRR giữa các cấu hình.
   - Chỉ chuyển sang embedding khi chunk không rỗng, không vượt giới hạn token, giữ đúng metadata/section và truy ngược được citation.

## Cấu hình khởi đầu

- Stage 1 headings: H2–H4.
- Stage 2 chunk size: 700 tokens.
- Chunk overlap: 80 tokens.
- Kết quả Development: backend/storage/processed/chunks.
