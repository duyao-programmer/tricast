# ============================================================================
# MessagePublishedEvent + 三级角色响应 Pydantic Schema
# ============================================================================
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


# ============================================================================
# 消息发布事件（生产者与消费者的契约）
# ============================================================================
class MessagePublishedEvent(BaseModel):
    """发布到 RabbitMQ 的消息体结构"""
    message_id: int
    title: str
    content: str
    secret_data_encrypted: str | None = None
    publisher_id: int
    published_at: str  # ISO 8601 格式


# ============================================================================
# 发布请求
# ============================================================================
class MessagePublishRequest(BaseModel):
    """单条消息发布请求"""
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    secret_data: dict | None = Field(None, description="需加密的敏感数据（JSON 对象）")


class BatchPublishRequest(BaseModel):
    """批量消息发布请求"""
    messages: list[MessagePublishRequest] = Field(..., min_length=1, max_length=10)


# ============================================================================
# 消息回执（仅管理员可见）
# ============================================================================
class ReceiptResponse(BaseModel):
    """消息在各通道的处理回执"""
    consumer_role: str
    channel: str
    received_at: str | None = None
    processing_time_ms: int | None = None

    model_config = {"from_attributes": True}


# ============================================================================
# 三级角色响应 Schema
# ============================================================================
class MessageBaseResponse(BaseModel):
    """消息基础字段（所有角色共享）"""
    id: int
    title: str
    published_at: str | None = None

    model_config = {"from_attributes": True}


class MessageRegularResponse(MessageBaseResponse):
    """普通用户（角色3）：仅标题和时间"""
    pass


class MessageAdvancedResponse(MessageBaseResponse):
    """高级用户（角色2）：标题 + 截断内容 + 发布者 + 通道"""
    content: str
    publisher: str | None = None
    channel: str | None = None  # 入站/出站通道标识

    model_config = {"from_attributes": True}


class MessageAdminResponse(MessageBaseResponse):
    """管理员（角色1）：完整字段 + 解密敏感数据 + 各通道耗时"""
    content: str
    secret_data: dict | None = None
    publisher: str | None = None
    channel: str | None = None
    receipts: list[ReceiptResponse] = []

    model_config = {"from_attributes": True}


# ============================================================================
# 耗时统计（仅管理员）
# ============================================================================
class ChannelStats(BaseModel):
    """单通道耗时统计"""
    channel: str
    count: int = 0
    min_ms: int | None = None
    max_ms: int | None = None
    avg_ms: float | None = None


class MessageStatsResponse(BaseModel):
    """消息耗时统计汇总"""
    message_id: int
    title: str
    channels: list[ChannelStats]


class PublishResponse(BaseModel):
    """发布成功响应"""
    message_id: int
    status: str
    outbox_id: int


class BatchPublishResponse(BaseModel):
    """批量发布结果"""
    total: int
    results: list[PublishResponse]
