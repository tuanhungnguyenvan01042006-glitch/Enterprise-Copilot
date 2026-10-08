from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
# Pydantic Settings là 1 thư viện giúp quản lý biến môi trường, config, validate dữ liệu,
# và ánh xạ biến môi trường vào class Settings

"""  Vai trò : 
tập trung config ở 1 nơi
validate kiểu dữ liệu ngay từ đầu
tránh lỗi do thiếu/ sai biến env
dễ đổi môi trường dev/local/prod

+ Ở đây hiểu đơn giản, Settings là class lưu tất cả các biến Môi trường, config, thay vì phải đọc trực tiếp từ file .env thì settings
giúp ánh xạ các biến môi trường vào class Settings, và nó còn thêm 1 sô tính năng : Validate kiểu dữ liệu, gtri hợp lệ 
+ Tóm lại là 1 phiên bản pro của việc sử dụng biến môi trường  : Dễ quản lý, dễ validate, dễ thay đổi môi trường dev/local/prod
"""

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),   # Khai báo các file .env để load biến môi trường, ưu tiên file đầu tiên nếu có nhiều file
        env_file_encoding="utf-8", 
        extra="ignore",
        case_sensitive=False,
    )
    app_env: str = "development"
    app_name: str = "Enterprise Copilot" 
    business_timezone: str = "Asia/Ho_Chi_Minh"
    database_url: str = Field(min_length=1)
    migration_database_url: str | None = None 
    session_cookie_name: str = "enterprise_copilot_session"
    session_cookie_secure: bool = False
    session_ttl_hours: int = Field(default=8, ge=1, le=24 * 30)
    allowed_origins: str = "http://localhost:8080,http://localhost:5173"
    upload_dir: Path = Path("./storage/uploads")
    max_upload_bytes: int = Field(default=10 * 1024 * 1024, gt=0)
    seed_admin_email: str = "admin@example.com"
    seed_admin_password: str | None = None      # Pydamic sẽ giúp ánh xạ biến môi trường vào từng trường, ngoài ra nó cx thực hiện validate kiểu dữ liệu, nếu không đúng kiểu dữ liệu, thì sẽ raise ValidationError
    seed_manager_password: str | None = None
    seed_employee_password: str | None = None


# Validate ( đảm bảo) rằng DATABASE_URL phải là PostgreSQL,
# nếu không thì raise ValueError  : Tức là các hàm Config này còn đảm bảo dữ liệu phải chuẩn
    @field_validator("database_url")
    @classmethod
    def require_postgres(cls, value: str) -> str:
        if not value.startswith(("postgresql://", "postgresql+psycopg://")):
            raise ValueError("DATABASE_URL must use PostgreSQL")
        return value

    @property
    def allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

