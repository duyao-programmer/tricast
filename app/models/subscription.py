# ============================================================================
# MessageTag + UserSubscription + MessageTagLink ORM 模型
# ============================================================================
from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from app.models.user import Base


class MessageTag(Base):
    __tablename__ = "message_tags"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tag_key: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    tag_name: Mapped[str] = mapped_column(String(50), nullable=False)
    category: Mapped[str] = mapped_column(String(20), nullable=False, default="department")
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(default=0)


class UserSubscription(Base):
    __tablename__ = "user_subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    tag_key: Mapped[str] = mapped_column(ForeignKey("message_tags.tag_key", ondelete="CASCADE"), nullable=False)
    subscribed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class MessageTagLink(Base):
    __tablename__ = "message_tag_links"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    message_id: Mapped[int] = mapped_column(ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    tag_key: Mapped[str] = mapped_column(ForeignKey("message_tags.tag_key", ondelete="CASCADE"), nullable=False)
