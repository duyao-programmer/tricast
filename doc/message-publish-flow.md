# TriCast 消息发布完整操作流程

## 概述

本文档演示在 TriCast 系统中发布一条消息并验证全链路的完整操作步骤，涵盖：登录认证 → 发布消息 → 等待消费 → 数据库验证 → RabbitMQ 验证 → 角色差异对比。

**环境要求**：Docker Desktop 已启动，TriCast 所有容器处于 healthy 状态。

---

## 一、环境检查

```bash
# 确认所有服务正常运行
docker compose ps
```

预期输出 5 个服务均为 Up / healthy 状态：`mysql`、`rabbitmq`、`adminer`、`fastapi`、`nginx`。

---

## 二、登录获取 JWT Token

### 2.1 命令行方式

```bash
curl -k -X POST https://localhost/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

### 2.2 返回示例

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "username": "admin",
  "role": "admin"
}
```

记下 `access_token` 的值，后续所有请求都需要携带。

### 2.3 Swagger 登录方式

1. 浏览器打开 `https://localhost/docs`（自签名证书点「高级 → 继续前往」）
2. 展开 `POST /api/auth/login` → "Try it out"
3. 输入 `{"username":"admin","password":"admin123"}` → "Execute"
4. 复制返回的 `access_token`
5. 点右上角 "Authorize" → 输入 `Bearer <token>` → "Authorize"

---

## 三、发布消息

### 3.1 命令行方式

```bash
# 将 YOUR_TOKEN 替换为上一步获取的 access_token
curl -k -X POST https://localhost/api/publish \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "title": "系统升级通知",
    "content": "服务器将于今晚22:00进行例行维护升级，预计持续2小时，请提前保存工作。",
    "secret_data": {"contact": "ops@example.com", "backup_plan": "已启用灾备切换"}
  }'
```

### 3.2 请求结构说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| title | string (1-200) | 是 | 消息标题 |
| content | string (1-5000) | 是 | 消息正文，未加密存储 |
| secret_data | object | 否 | 敏感数据，存储前使用 AES-256-CBC 加密 |

### 3.3 返回示例

```json
{
  "message_id": 12,
  "status": "pending",
  "outbox_id": 12
}
```

此时消息已写入 MySQL（`messages` 表 + `outbox` 表），但尚未发布到 RabbitMQ。Outbox 发布器将在 2 秒内扫描 `pending` 记录并发布。

### 3.4 Python 一键脚本

```python
import urllib.request, json, ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# 登录
login = json.dumps({"username": "admin", "password": "admin123"}).encode()
req = urllib.request.Request(
    "https://localhost/api/auth/login",
    data=login,
    headers={"Content-Type": "application/json"}
)
token = json.loads(urllib.request.urlopen(req, context=ctx).read())["access_token"]
print("登录成功")

# 发布
msg = {
    "title": "你的消息标题",
    "content": "你的消息正文内容...",
    "secret_data": {"key": "value"}
}
data = json.dumps(msg).encode()
req = urllib.request.Request(
    "https://localhost/api/publish",
    data=data,
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
)
result = json.loads(urllib.request.urlopen(req, context=ctx).read())
print(f"发布成功: message_id={result['message_id']}, outbox_id={result['outbox_id']}")
```

---

## 四、消息处理流程

```
[管理员 POST /api/publish]
    │
    ├── 1. DB 事务: INSERT messages + INSERT outbox(pending) → COMMIT
    │
    ├── 2. Outbox 发布器（asyncio.Task，每 2 秒轮询）
    │       ├── SELECT pending ORDER BY id LIMIT 10
    │       ├── 去重检查: 查询 message_receipts 是否已有该 message_id
    │       ├── 发布到 RabbitMQ Fanout Exchange (Publisher Confirms)
    │       ├── RabbitMQ ACK → 标记 published
    │       └── 失败 → retry_count++ (最多 3 次)
    │
    └── 3. 三个消费者协程（永不退出）
            ├── 解析 MessagePublishedEvent JSON
            ├── 计算处理耗时 (now - published_at)
            ├── 写入 message_receipts（3 次指数退避重试）
            ├── 唯一约束冲突 → 幂等跳过
            ├── 成功 → basic_ack
            └── 失败 → basic_nack(requeue=False) → DLX → queue.dead
```

---

## 五、验证消费结果

### 5.1 查看消息详情（命令行）

等待至少 15 秒（消费者 max 处理间隔）后：

```bash
# 登录 + 查询单条消息
TOKEN=$(curl -k -s -X POST https://localhost/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' \
  | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

curl -k https://localhost/api/messages/12 \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
```

三个消费者都处理后，返回类似：

```json
{
  "id": 12,
  "title": "系统升级通知",
  "content": "服务器将于今晚22:00进行例行维护升级，预计持续2小时，请提前保存工作。",
  "published_at": "2026-05-28T07:15:30.123000",
  "secret_data": {"contact": "ops@example.com", "backup_plan": "已启用灾备切换"},
  "publisher": "admin",
  "channel": "msg.fanout/12",
  "receipts": [
    {"consumer_role": "admin",    "channel": "admin_channel",    "processing_time_ms": 856},
    {"consumer_role": "advanced", "channel": "advanced_channel", "processing_time_ms": 858},
    {"consumer_role": "regular",  "channel": "regular_channel",  "processing_time_ms": 859}
  ]
}
```

### 5.2 查看耗时统计（仅 admin）

```bash
curl -k https://localhost/api/messages/stats \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
```

每条消息展示三通道的 min/max/avg/count：

```json
{
  "message_id": 12,
  "title": "系统升级通知",
  "channels": [
    {"channel": "admin_channel",    "count": 1, "min_ms": 856, "max_ms": 856, "avg_ms": 856.0},
    {"channel": "advanced_channel", "count": 1, "min_ms": 858, "max_ms": 858, "avg_ms": 858.0},
    {"channel": "regular_channel",  "count": 1, "min_ms": 859, "max_ms": 859, "avg_ms": 859.0}
  ]
}
```

---

## 六、MySQL 数据库验证（Adminer）

浏览器打开 `http://localhost:8080`，登录参数：

| 字段 | 值 |
|------|-----|
| 系统 | MySQL |
| 服务器 | `mysql`（不是 localhost！）|
| 用户名 | `root` |
| 密码 | `root_pass_2024` |
| 数据库 | `demo_db` |

### 6.1 查询刚发布的消息

```sql
SELECT id, title, publisher_id, published_at, created_at
FROM messages
WHERE id = 12;
```

### 6.2 查询消费回执（三个角色各一条）

```sql
SELECT consumer_role, channel, processing_time_ms, received_at
FROM message_receipts
WHERE message_id = 12
ORDER BY consumer_role;
```

预期 3 条记录：

| consumer_role | channel | processing_time_ms |
|---------------|---------|-------------------|
| admin | admin_channel | ~856 |
| advanced | advanced_channel | ~858 |
| regular | regular_channel | ~859 |

### 6.3 查询 Outbox 状态

```sql
SELECT id, aggregate_id, status, retry_count, last_error
FROM outbox
WHERE aggregate_id = 12;
```

预期 `status = 'published'`，`retry_count = 0`，`last_error = NULL`。

### 6.4 验证 secret_data 加密存储

```sql
SELECT id, title, secret_data_encrypted
FROM messages
WHERE id = 12;
```

`secret_data_encrypted` 字段存储的是 AES-256-CBC 密文（格式：`iv_b64:ciphertext_b64`），数据库中不可直接读取明文。

---

## 七、RabbitMQ 管理控制台验证

浏览器打开 `http://localhost:15672`，登录：`demo_user / demo_pass_2024`

### 7.1 查看队列

点 "Queues" 标签 → 查看四个队列：

| 队列 | Ready | Unacked | Total |
|------|-------|---------|-------|
| queue.admin | 0 | 0 | 0 |
| queue.advanced | 0 | 0 | 0 |
| queue.regular | 0 | 0 | 0 |
| queue.dead | 0 | 0 | 0 |

Total = 0 表示消息已被消费，没有积压。

### 7.2 查看 Exchange 绑定

点 "Exchanges" → `msg.fanout` → Bindings：

```
queue.admin    → 绑定到 msg.fanout
queue.advanced → 绑定到 msg.fanout
queue.regular  → 绑定到 msg.fanout
```

Fanout 模式下，发布到 `msg.fanout` 的消息会广播到全部三个队列。

### 7.3 查看死信 Exchange

点 "Exchanges" → `msg.dlx` → Bindings：

```
queue.dead → 绑定到 msg.dlx
```

处理失败或 TTL 过期的消息最终路由到这里。

---

## 八、三级角色数据可见性对比

三个账号分别查询同一条消息（以 message_id=12 为例）：

| 账号 | 密码 | 角色 | content | secret_data | publisher | receipts |
|------|------|------|:---:|:---:|:---:|:---:|
| admin | admin123 | 管理员 | 完整 | AES 解密后 | 显示 | 显示 |
| adv_user | adv123 | 高级用户 | 截断 50 字 | 不显示 | 显示 | 不显示 |
| reg_user | reg123 | 普通用户 | 不显示 | 不显示 | 不显示 | 不显示 |

### 操作方式

在 Swagger 页面上方 "Authorize" 处依次：

1. 登录 admin → `GET /api/messages/12`，看到完整内容 + secret_data + receipts
2. 点击 "Authorize" → "Logout" → 登录 adv_user → `GET /api/messages/12`，看到 content 截断 + publisher，无 secret_data 和 receipts
3. 再次 Logout → 登录 reg_user → `GET /api/messages/12`，仅看到 id + title + published_at

---

## 九、查看死信消息

当某条消息处理失败（消费者 NACK 后进入 DLX）或 TTL 超时，会被死信消费者记录：

```bash
curl -k https://localhost/api/messages/dead \
  -H "Authorization: Bearer $TOKEN" | python -m json.tool
```

```json
{
  "total": 0,
  "items": []
}
```

返回 `total: 0` 表示没有死信，所有消息都正常消费。死信消费者通过 `GET /health/consumers` 可确认其运行状态（`consumer_dead: running`）。

---

## 十、完整流程总结

```
1. POST /api/auth/login          → 获取 JWT Token
2. POST /api/publish              → 发布消息（写入 MySQL messages + outbox）
3. Outbox 发布器轮询              → 从 outbox 读取 pending → 发布到 RabbitMQ msg.fanout
4. 三个消费者并行消费            → 解析消息 → 写入 message_receipts → basic_ack
5. GET /api/messages/12           → 验证消息详情 + 消费回执
6. GET /api/messages/stats        → 查看各通道耗时统计
7. Adminer → messages + message_receipts + outbox 表 → 数据库层面确认
8. RabbitMQ → Queues/Exchanges → 消息队列层面确认
```
