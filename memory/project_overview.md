---
name: tricast-message-pubsub
description: TriCast — 基于 RabbitMQ + FastAPI + MySQL + Nginx 的三角色消息广播演示系统
metadata:
  type: project
---

TriCast 消息发布订阅演示系统项目。Tri = 三角色，Cast = Fanout 广播。

**技术栈**：RabbitMQ (aio_pika)、FastAPI (Python 3.11)、MySQL 8.0、Nginx、Docker

**三种角色**：
- 管理员（角色1）：发布消息，查看完整数据 + 各通道耗时统计
- 高级用户（角色2）：订阅消息，查看部分数据（content 截断50字）
- 普通用户（角色3）：订阅消息，仅查看 title + 发布时间

**核心设计决策**：
- 消费者是系统级角色代理，非真实用户 — 三个消费者协程代表三种角色从 RabbitMQ 消费并记录耗时到 message_receipts
- 事务发件箱模式（outbox 表）保证消息写入和发布的原子性
- Publisher Confirms + 手动 ACK + 死信队列
- 三级独立 Pydantic Schema 控制数据可见性，杜绝字段泄露
- AES-256-CBC 加密 secret_data
- slowapi 限流 + 登录失败锁定

**Why**: 演示消息队列发布订阅机制和角色权限分级控制

**How to apply**: 所有 API 设计遵循"消费者是系统代理"的语义，真实用户通过 API 从 messages 表查询数据；数据可见性通过独立 Pydantic Schema 按角色控制
