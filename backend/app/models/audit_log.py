"""
Audit log là nhật ký ghi lại các hoạt động quan trọng xảy ra trong hệ thống, nhằm biết:

Ai thực hiện?
Thực hiện hành động gì?
Trên đối tượng nào?
Thành công hay thất bại?
Khi nào xảy ra?
Chi tiết liên quan là gì?

* Thực tế nó chính là lưu Request(thực hiện 1 chức năng/API call nào đấy) (giống như 1 lịch sử giao dịch) của User
+ Tuy nhiên ko phải mọi Request của User đều bị ghi vào, mfa chỉ những Thao tác nghiệp vụ quan trọng mới được ghi vào 

* Tại sao lại cần Audit Log : 
+ Bảo mật, truy vết sự cố
+ Khôi phục, nâng cao trách nghiệm (ai làm j cũng bị ghi lại)

* Bài học : Database của 1 project ko chỉ lưu các model (bảng) dùng cho quá trình thực hiện chức năng, mà còn lưu các bảng dữ liệu phục vụ Security
"""

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_logs_created_at", "created_at"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    actor_id: Mapped[str | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    # người thực hiện hành động 
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    # Hành động đó là gì : Login success, task created,...
    entity_type: Mapped[str | None] = mapped_column(String(50))
    entity_id: Mapped[str | None] = mapped_column(String(80))
    # Đối tượng bị tác động, vdu : Task, document, user,... (model)
    result: Mapped[str] = mapped_column(String(20), nullable=False)
    # kết quả của hành động : Success / Failure
    request_id: Mapped[str] = mapped_column(String(80), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

