# ============================================================================
# User ORM 模型
# ============================================================================
from sqlalchemy import Column, Integer, String, Boolean, TIMESTAMP, Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime
import enum


class Base(DeclarativeBase):
    pass


class UserRole(str, enum.Enum):
    admin = "admin"
    advanced = "advanced"
    regular = "regular"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role = Column(SAEnum(UserRole), nullable=False, default=UserRole.regular)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until = Column(TIMESTAMP, nullable=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)


class FailedLoginLog(Base):
    """登录失败日志"""
    __tablename__ = "failed_login_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), nullable=False)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)
    attempted_at = Column(TIMESTAMP, default=datetime.utcnow)
