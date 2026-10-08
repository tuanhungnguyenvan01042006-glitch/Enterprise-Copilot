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
