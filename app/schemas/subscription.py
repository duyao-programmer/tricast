# ============================================================================
# 订阅相关 Pydantic Schema
# ============================================================================
from pydantic import BaseModel, Field


class TagInfo(BaseModel):
    """标签信息"""
    tag_key: str
    tag_name: str
    category: str
    is_default: bool
    sort_order: int = 0


class UserSubscriptionItem(BaseModel):
    """用户对单个标签的订阅状态"""
    tag_key: str
    tag_name: str
    category: str
    is_default: bool
    subscribed: bool


class SubscriptionUpdateRequest(BaseModel):
    """批量更新订阅"""
    subscriptions: list[dict[str, object]] = Field(..., description="[{tag_key: str, subscribed: bool}, ...]")


class UserSubscriptionsResponse(BaseModel):
    """用户订阅状态响应"""
    tags: list[UserSubscriptionItem]
