# Enterprise Copilot

Enterprise Copilot là ứng dụng nội bộ gồm React/Vite, FastAPI, SQLAlchemy/Alembic và PostgreSQL. Dữ liệu nghiệp vụ nằm trong PostgreSQL; tệp tải lên nằm trong volume riêng và không được public trực tiếp.

## Chạy bằng Docker Compose

Yêu cầu Docker Desktop có Compose v2.

```powershell
Copy-Item .env.example .env
# Mở .env và đặt SEED_ADMIN_PASSWORD, SEED_MANAGER_PASSWORD, SEED_EMPLOYEE_PASSWORD
docker compose up --build
```

Mở `http://localhost:8080`. Chỉ web/nginx được publish ra host. Chuỗi khởi động là:

`db healthy -> migrate (alembic upgrade head) -> seed (idempotent) -> api healthy -> web`.

Các volume có tên `postgres_data` và `uploads_data`, nên `docker compose down` không xóa dữ liệu. Muốn xóa dữ liệu local một cách có chủ đích, dùng `docker compose down -v`.

Kiểm tra nhanh:

```powershell
Invoke-WebRequest http://localhost:8080/healthz
Invoke-WebRequest http://localhost:8080/api/v1/health/live
```

## Chạy trực tiếp để phát triển

Backend yêu cầu Python 3.12+ và PostgreSQL đang chạy. Từ thư mục `backend/`:

```powershell
pip install -r requirements.txt
alembic upgrade head
python -m app.scripts.seed
uvicorn app.main:app --reload --port 8000
```

Frontend yêu cầu Node.js 20+:

```powershell
cd frontend
npm install
npm run dev
npm run typecheck
npm run test:run
npm run build
```

## Thử RAG nội bộ

Sau khi đã index tài liệu vào Qdrant, cấu hình `VOYAGE_API_KEY` và
`OPENAI_API_KEY` trong `.env`. Model trả lời mặc định là `gpt-4o-mini`, có thể
đổi qua `OPENAI_GENERATION_MODEL`. Từ thư mục gốc, chạy:

```powershell
docker compose exec api python -m app.scripts.answer_question "Chính sách nghỉ phép là gì?" --top-k 5
```

Lệnh gửi câu hỏi và nội dung các chunk tìm được tới OpenAI và trả về câu trả lời
cùng nguồn. Đây là công cụ nội bộ, chưa kiểm tra quyền truy cập tài liệu.

## Chatbot

Chatbot dành cho nhân viên tại `/app/chatbot`. Mỗi câu hỏi được xử lý độc lập;
lịch sử hội thoại được lưu trong PostgreSQL. Tạo hội thoại, gửi câu hỏi, sau đó
chọn nguồn tham khảo để mở tài liệu trong kho kiến thức.

Để chạy tính năng, cấu hình `VOYAGE_API_KEY`, `OPENAI_API_KEY`, Qdrant và
index tài liệu như hướng dẫn RAG ở trên. Sau khi cập nhật mã nguồn, xây dựng lại
và khởi động stack bằng `docker compose up --build -d`; service `migrate` chạy
`alembic upgrade head` để tạo bảng chat. Nếu chạy backend ngoài Compose, thực
hiện `alembic upgrade head` trong thư mục `backend` trước khi khởi động API.

Kiểm tra thủ công: đăng nhập bằng tài khoản nhân viên, mở Chatbot, tạo hội thoại,
đặt câu hỏi có trong tài liệu đã index, kiểm tra câu trả lời và nguồn, rồi tải lại
trang và mở lại hội thoại. Thử câu hỏi không có dữ liệu và xác nhận thông báo phù hợp.
Nếu dịch vụ RAG không sẵn sàng, giao diện cho phép gửi lại câu hỏi.

Chatbot truy xuất toàn bộ tập dữ liệu RAG, không lọc theo quyền tài liệu. Chỉ index
tài liệu có thể chia sẻ với mọi nhân viên; cần bổ sung phân quyền RAG trước khi
index tài liệu phòng ban hoặc tài liệu hạn chế.

## E2E

E2E chạy trên stack đã khởi động và dữ liệu seed:

```powershell
cd frontend
npx playwright install chromium
$env:E2E_EMPLOYEE_PASSWORD="..."
$env:E2E_MANAGER_PASSWORD="..."
npm run e2e
```

Có thể đổi URL bằng `E2E_BASE_URL`. Các flow chính kiểm tra nhân viên, giao việc, deep-link SPA và health endpoint. Test E2E không chạy trong `npm run test:run`.

## Tài liệu

- [.docs/SETUP.md](.docs/SETUP.md) — setup, reset và kiểm tra stack.
- [.docs/ARCHITECTURE.md](.docs/ARCHITECTURE.md) — kiến trúc runtime và startup.
- [.docs/DATA_ACCESS.md](.docs/DATA_ACCESS.md) — dữ liệu, authorization và persistence.
