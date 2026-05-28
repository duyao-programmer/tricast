# ============================================================================
# Message + MessageReceipt + Outbox ORM 模型
# ============================================================================
from sqlalchemy import Column, Integer, String, Text, JSON, TIMESTAMP, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
import enum

from app.models.user import Base
from datetime import datetime


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    secret_data_encrypted = Column(Text, nullable=True, comment="AES-256-CBC 加密的敏感数据")
    publisher_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    published_at = Column(TIMESTAMP(timezone=False), default=lambda: datetime.utcnow())


class MessageReceipt(Base):
    __tablename__ = "message_receipts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    message_id: Mapped[int] = mapped_column(Integer, ForeignKey("messages.id"), nullable=False)
    consumer_role: Mapped[str] = mapped_column(String(20), nullable=False)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    received_at = Column(TIMESTAMP(timezone=False), default=lambda: datetime.utcnow())
    processing_time_ms = Column(Integer, nullable=True, comment="毫秒")


class OutboxStatus(str, enum.Enum):
    pending = "pending"
    published = "published"
    failed = "failed"


class Outbox(Base):
    __tablename__ = "outbox"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    aggregate_type: Mapped[str] = mapped_column(String(100), nullable=False, default="message")
    aggregate_id: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, default="message_published")
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, comment="MessagePublishedEvent 序列化")
    status = Column(String(20), nullable=False, default="pending")
    created_at = Column(TIMESTAMP, default=lambda: datetime.utcnow())
    published_at = Column(TIMESTAMP, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
