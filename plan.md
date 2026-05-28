# 消息发布订阅系统 - 架构规划（终版）

## 背景

基于 RabbitMQ + FastAPI + MySQL + Nginx 构建消息发布/订阅演示系统。三种角色：管理员（角色1）发布消息，高级用户（角色2）和普通用户（角色3）订阅消息。实现消息持久化、权限分级、耗时统计。

### 核心设计决策

**消费者是系统级角色代理，非真实用户。** 三个消费者协程分别代表三种角色从 RabbitMQ 消费消息并记录处理耗时到 `message_receipts` 表。真实用户通过 API 从 `messages` 表查询消息，数据可见性由 API 层的 Pydantic Schema 按角色控制。`message_receipts` 中的 `consumer_role` 字段标识是哪个角色代理消费的（值为 `admin` / `advanced` / `regular`），不关联具体用户 ID。

## 技术栈

| 组件 | 技术 | 端口 |
|------|------|------|
| 消息队列 | RabbitMQ 3.x Management (aio_pika) | 5672 / 15672 |
| Web服务器 | Nginx (反向代理) | 80 |
| 数据库 | MySQL 8.0 | 3306 |
| API框架 | FastAPI (Python 3.11) | 8000 |
| 认证 | JWT (python-jose) | - |
| 加密 | AES-256 (cryptography) | - |
| 限流 | slowapi | - |
| 数据库工具 | Adminer | 8080 |

## 项目目录结构

```
demo20250527/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 入口，lifespan 管理全部后台协程
│   ├── config.py               # 全局配置（从 .env 加载）
│   ├── database.py             # SQLAlchemy async 引擎 + 会话工厂
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py             # User ORM 模型
│   │   └── message.py          # Message + MessageReceipt + Outbox ORM 模型
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── user.py             # 用户注册/登录请求响应模型
│   │   └── message.py          # MessagePublishedEvent + 三级角色响应 Schema
│   ├── api/
│   │   ├── __init__.py
│   │   ├── auth.py             # 注册、登录接口（含限流+锁定重置）
│   │   ├── publish.py          # 消息发布接口（管理员专用）
│   │   ├── messages.py         # 消息查询接口（角色分级 Schema 分发）
│   │   └── health.py           # 健康检查端点
│   ├── services/
│   │   ├── __init__.py
│   │   ├── rabbitmq.py         # RabbitMQ 连接管理 + 发布(含 Publisher Confirms) + 消费者
│   │   ├── auth.py             # JWT 生成/验证 + bcrypt 密码哈希
│   │   ├── crypto.py           # AES-256-CBC 加解密
│   │   └── outbox.py           # 事务发件箱后台发布器
│   └── middleware/
│       ├── __init__.py
│       └── auth.py             # JWT 认证依赖注入 + 角色校验
├── scripts/
│   └── gen_password_hash.py    # 预生成 bcrypt 密码哈希（写入 init.sql 用）
├── docker-compose.yml          # 全部容器编排（含 FastAPI）
├── Dockerfile                  # FastAPI 容器镜像
├── requirements.txt            # Python 依赖
├── nginx.conf                  # Nginx 反向代理配置
├── init.sql                    # 数据库建表 + 预置用户（含 bcrypt 哈希）
├── .env.example                # 环境变量模板（含完整清单和说明）
└── .gitignore                  # 排除 .env 等敏感文件
```

## 环境变量清单（.env.example）

```bash
# ============================================================================
# MySQL 配置
# ============================================================================
MYSQL_HOST=mysql
MYSQL_PORT=3306
MYSQL_USER=demo_user
MYSQL_PASSWORD=demo_pass_2024
MYSQL_DATABASE=demo_db
MYSQL_ROOT_PASSWORD=root_pass_2024

# ============================================================================
# RabbitMQ 配置
# ============================================================================
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
RABBITMQ_USER=demo_user
RABBITMQ_PASSWORD=demo_pass_2024
RABBITMQ_MGMT_PORT=15672

# ============================================================================
# JWT 配置
# ============================================================================
JWT_SECRET_KEY=change-me-to-a-random-string-at-least-32-chars
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60

# ============================================================================
# AES-256 加密配置（必须恰好 32 字节）
# ============================================================================
AES_ENCRYPTION_KEY=change-me-to-exactly-32-bytes-key!!

# ============================================================================
# 消费者配置
# ============================================================================
# 消息处理间隔（秒），仅用于演示模拟耗时，生产环境应设为 0 或移除此逻辑
CONSUME_INTERVAL_SECONDS=10

# ============================================================================
# 应用配置
# ============================================================================
APP_ENV=development
APP_DEBUG=true
```

## RabbitMQ 架构

```
                      ┌──────────────────────┐
                      │   Fanout Exchange    │
                      │   "msg.fanout"       │
                      │  (Publisher Confirms)│
                      └──────────┬───────────┘
                                 │ (所有消息广播到全部绑定队列)
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
   ┌──────▼──────┐        ┌──────▼──────┐        ┌──────▼──────┐
   │ queue.admin │        │queue.advanced│        │queue.regular│
   │  (通道 1)   │        │  (通道 2)    │        │  (通道 3)    │
   │ prefetch=1  │        │  prefetch=1  │        │  prefetch=1  │
   │ manual_ack  │        │  manual_ack  │        │  manual_ack  │
   └──────┬──────┘        └──────┬──────┘        └──────┬──────┘
          │                      │                      │
    系统角色消费者          系统角色消费者          系统角色消费者
   (role=admin)           (role=advanced)         (role=regular)
   永不退出(try...except)  永不退出(try...except)  永不退出(try...except)
                             │
                      ┌──────▼──────┐
                      │   DLX       │
                      │ "msg.dlx"   │
                      │  (fanout)   │
                      └──────┬──────┘
                             │
                      ┌──────▼──────┐
                      │ queue.dead  │  ← 仅收集，演示环境无消费者
                      └─────────────┘    ⚠️ 生产需增加监控/重试/告警
```

- **Exchange 类型**: `fanout`，名称 `msg.fanout`
- **Publisher Confirms**: 发布端启用，RabbitMQ 确认后才标记 outbox 为 `published`
- **死信交换器**: `msg.dlx`（fanout）→ 死信队列 `queue.dead`（演示环境仅收集，不消费）
- **消息 TTL**: 每条消息 60 秒，超时未消费 → DLX
- **手动 ACK**: 消费者处理完成并写入 `message_receipts` 后才 `basic_ack`，处理失败 `basic_nack(requeue=False)` → DLX
- **prefetch_count=1**: 每次只取一条消息，保证处理完当前消息才取下一跳
- **幂等性**: `message_receipts` 的 `UNIQUE(message_id, consumer_role)` 约束
- **RabbitMQ 认证**: 自定义用户密码（通过环境变量注入），guest 账户禁用

## 消息体格式（MessagePublishedEvent）

消费者和发布者之间的契约，定义在 `schemas/message.py` 中：

```python
class MessagePublishedEvent(BaseModel):
    """发布到 RabbitMQ 的消息体结构"""
    message_id: int
    title: str
    content: str
    publisher_id: int
    published_at: str  # ISO 8601 格式，如 "2025-05-27T10:30:00.123"
```

消费者反序列化时使用 Pydantic 校验，字段缺失或类型错误直接进入死信。

## 数据库设计

### users 表
```sql
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin', 'advanced', 'regular') NOT NULL DEFAULT 'regular',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    failed_login_attempts INT NOT NULL DEFAULT 0,
    locked_until TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### messages 表
```sql
CREATE TABLE messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    secret_data_encrypted TEXT COMMENT 'AES-256-CBC 加密的敏感数据',
    publisher_id INT NOT NULL,
    published_at TIMESTAMP(3) DEFAULT CURRENT_TIMESTAMP(3),
    FOREIGN KEY (publisher_id) REFERENCES users(id)
);
```

### outbox 表
```sql
CREATE TABLE outbox (
    id INT AUTO_INCREMENT PRIMARY KEY,
    aggregate_type VARCHAR(100) NOT NULL DEFAULT 'message',
    aggregate_id INT NOT NULL,
    event_type VARCHAR(100) NOT NULL DEFAULT 'message_published',
    payload JSON NOT NULL COMMENT 'MessagePublishedEvent 序列化',
    status ENUM('pending', 'published', 'failed') NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMP NULL,
    retry_count INT NOT NULL DEFAULT 0,
    last_error TEXT NULL
);
```

### message_receipts 表
```sql
CREATE TABLE message_receipts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    message_id INT NOT NULL,
    consumer_role ENUM('admin', 'advanced', 'regular') NOT NULL,
    channel VARCHAR(20) NOT NULL,
    received_at TIMESTAMP(3) DEFAULT CURRENT_TIMESTAMP(3),
    processing_time_ms INT COMMENT '毫秒',
    FOREIGN KEY (message_id) REFERENCES messages(id),
    UNIQUE KEY uk_msg_role (message_id, consumer_role)
);
```

### failed_login_log 表
```sql
CREATE TABLE failed_login_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    ip_address VARCHAR(45) NOT NULL,
    attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 数据可见性矩阵（三个独立 Pydantic Schema）

| 字段 | 管理员(角色1) | 高级用户(角色2) | 普通用户(角色3) |
|------|:-----------:|:------------:|:------------:|
| id | ✅ | ✅ | ✅ |
| title | ✅ | ✅ | ✅ |
| content | ✅ | ✅ (前50字+`...[截断]`标记) | ❌ |
| secret_data | ✅ (AES解密后) | ❌ | ❌ |
| publisher | ✅ | ✅ | ❌ |
| published_at | ✅ | ✅ | ✅ |
| receipts(耗时列表) | ✅ | ❌ | ❌ |
| channel | ✅ | ✅ | ❌ |

Schema 定义：
- `MessageAdminResponse` — 全部字段 + 解密的 secret_data + receipts
- `MessageAdvancedResponse` — title + content(截断50字) + publisher + published_at + channel
- `MessageRegularResponse` — 仅 title + published_at

> ⚠️ 管理员查询列表时每条消息需解密 secret_data，演示规模无影响；生产环境可考虑缓存或异步解密。

## API 设计

### `GET /health`（公开）
- 返回数据库连接状态、RabbitMQ 连接状态
- 供 Docker healthcheck 使用

### `POST /api/auth/register`（限流 5次/分钟/IP）
- 请求体: `{ "username": "...", "password": "..." }`
- 角色**不可由用户指定**，强制 `regular`。请求中的 `role` 字段如有则忽略
- 管理员账户仅通过 `init.sql` 或数据库直接操作创建
- 可扩展密码强度策略（当前演示版无强制，但代码中保留校验接口）

### `POST /api/auth/login`（限流 5次/分钟/IP）
- 请求体: `{ "username": "...", "password": "..." }`
- 失败流程: 记录 `failed_login_log` → `failed_login_attempts += 1`
- 锁定策略: `failed_login_attempts >= 5` → `locked_until = NOW() + 15分钟`
- **成功登录重置**: 密码验证成功后，`failed_login_attempts = 0`，`locked_until = NULL`，防止正常用户因历史误输被永久锁定
- 返回 JWT `access_token`（含 user_id、username、role、exp）

### `POST /api/publish`（仅管理员）
- 事务发件箱模式：
  1. 开启 DB 事务
  2. `secret_data` 经 AES-256-CBC 加密 → `secret_data_encrypted`
  3. `INSERT INTO messages` → 获取 `message_id`
  4. 构造 `MessagePublishedEvent` JSON → `INSERT INTO outbox` (status=pending)
  5. 提交事务
- 后台 outbox 发布器轮询 pending 并发布到 RabbitMQ（Publisher Confirms 确认后标记 published）
- 请求体: `{ "title": "...", "content": "...", "secret_data": {...} }`

### `POST /api/publish/batch`（仅管理员）
- 同上，单次事务写入 10 条 messages + 10 条 outbox 记录
- 请求体: `{ "messages": [{...}, ...] }`（10 条）

### `GET /api/messages`（需登录）
- 按 JWT role 选择 Schema 序列化：`admin` / `advanced` / `regular`
- 分页: `?page=1&page_size=20`

### `GET /api/messages/{id}`（需登录）
- 单条消息详情，同上按角色过滤

### `GET /api/messages/stats`（仅管理员）
- 10 条消息在各通道的耗时统计（min / max / avg / count）

## 消息处理流程（事务发件箱 + Publisher Confirms + 死信）

```
[管理员 POST /api/publish/batch]
    │
    ├── 1. DB事务: INSERT messages(10条) + INSERT outbox(10条, pending) → COMMIT
    │
    ├── 2. Outbox 发布器 (asyncio.Task, 每 2 秒轮询)
    │       ├── SELECT * FROM outbox WHERE status='pending' ORDER BY id LIMIT 10
    │       ├── 逐条: await exchange.publish(msg, mandatory=True)  ← Publisher Confirms
    │       │   ├── RabbitMQ ack → UPDATE outbox SET status='published', published_at=NOW()
    │       │   └── RabbitMQ nack/超时 → UPDATE outbox SET status='failed', retry_count++, last_error=...
    │       └── 若发布成功但状态更新失败 → 下次轮询会重复发布
    │           └── ⚠️ 依赖消费者幂等性（UNIQUE约束）屏蔽重复消息，可接受但有资源浪费
    │
    ├── 消费者协程（每个队列一个，永不退出的无限循环）
    │   │
    │   │   while True:
    │   │       try:
    │   │           async with queue.iterator() as queue_iter:
    │   │               async for msg in queue_iter:
    │   │                   event = MessagePublishedEvent.parse_raw(msg.body)
    │   │                   processing_time = (now() - event.published_at).ms
    │   │                   # 插入 receipt（含重试：3次，指数退避 1s/2s/4s）
    │   │                   for attempt in range(3):
    │   │                       try:
    │   │                           INSERT INTO message_receipts ...
    │   │                           break
    │   │                       except IntegrityError:  # 唯一约束冲突 = 重复消息
    │   │                           logger.warning("重复消息，跳过")
    │   │                           break
    │   │                       except DBConnectionError:
    │   │                           if attempt < 2: await asyncio.sleep(2**attempt)
    │   │                           else: raise  # 3次全失败 → 外层 except → nack
    │   │                   await msg.ack()
    │   │                   await asyncio.sleep(CONSUME_INTERVAL_SECONDS)
    │   │       except asyncio.CancelledError:
    │   │           break  # 应用关闭，正常退出
    │   │       except Exception:
    │   │           logger.exception("消费者异常，nack 当前消息，3秒后继续")
    │   │           try: await msg.nack(requeue=False)  # 进入 DLX
    │   │           except: pass
    │   │           await asyncio.sleep(3)
    │   └────────── continue  # 永不退出，继续下一条
    │
    └── lifespan 健康监控（可选）: 检测消费者协程是否异常退出，自动重建
```

## 消费者设计（健壮性）

- `aio_pika` 异步消费者，在 `lifespan` 启动时创建，关闭时 cancel
- **永不退出原则**: 最外层 `while True` + `try...except`，任何未捕获异常都会被兜底，记录日志后 `continue`
- **DB 写入重试**: `message_receipts` 插入最多重试 3 次，指数退避（1s → 2s → 4s），全部失败后 nack 进入死信
- **幂等安全网**: `IntegrityError`（唯一约束冲突）→ 判定为重复消息，直接 ACK 跳过
- `prefetch_count=1` + 手动 ACK，确保一条处理完才取下一条
- `CONSUME_INTERVAL_SECONDS` 默认 10s，**仅用于演示模拟耗时处理，生产环境应设为 0 或移除此逻辑**
- SQLAlchemy `pool_pre_ping=True` 保证每次从连接池取出时验证连接有效性

## Outbox 发布器设计

- `asyncio.Task`，每 2 秒轮询 `outbox` 表中 `status='pending'` 的记录
- 发布时启用 **Publisher Confirms**（`mandatory=True`）:
  - 收到 RabbitMQ `ack` → 标记 `published`
  - 收到 `nack` 或超时 → 标记 `failed`，记录错误信息
- 发布成功但状态更新失败 → 下次轮询会重复发布 → 依赖消费者的幂等性屏蔽
- 失败记录的重试策略: `retry_count < 3` 时重置为 `pending` 等待下次轮询，超过 3 次保持 `failed`

## 安全措施汇总

| 措施 | 实现方式 |
|------|----------|
| 注册角色限制 | 强制 role=regular，忽略请求中的 role 字段；管理员仅 init.sql 创建 |
| RabbitMQ 认证 | 自定义用户密码，env 注入，guest 禁用 |
| secret_data 加密 | AES-256-CBC，密钥来自 `AES_ENCRYPTION_KEY` 环境变量 |
| JWT 密钥 | 环境变量 `JWT_SECRET_KEY`，`.env` 不入库 |
| 数据库密码 | 环境变量，docker-compose 引用 |
| 登录限流 | slowapi `@limiter.limit("5/minute")` 按 IP |
| 暴力破解防护 | 5次失败锁定15分钟；成功登录重置计数 |
| 字段泄露防护 | 三级独立 Pydantic Schema，ORM 对象绝不对用户直接序列化 |
| .env 保护 | `.gitignore` 排除，提供 `.env.example` |
| 密码哈希 | bcrypt 预生成密文硬编码入 init.sql（通过 `scripts/gen_password_hash.py` 生成） |
| HTTPS | 演示环境使用 HTTP；**生产环境必须在 Nginx/LB 启用 HTTPS，防止 JWT 和数据被窃听** |

## 数据一致性措施汇总

| 措施 | 实现方式 |
|------|----------|
| 事务发件箱 | messages + outbox 在同一 DB 事务提交 |
| Publisher Confirms | RabbitMQ ack 后才标记 published；nack 则标记 failed |
| 手动 ACK | 消费者 receipt 写入成功后才 ack |
| 死信队列 | nack(requeue=False) → DLX → `queue.dead` |
| 幂等性 | `UNIQUE(message_id, consumer_role)` + 消费者端 `IntegrityError` 捕获 |
| 连接重试 | DB 写入 3 次指数退避重试 + `pool_pre_ping=True` |
| 消费者健壮 | try...except 兜底，永不退出 |
| 死信积压 | ⚠️ 已知局限：演示环境死信仅收集不处理；**生产需增加监控/重试/告警** |

## Docker 编排

`docker-compose.yml` 5 个服务，启动顺序 `depends_on` + `healthcheck`：

| 服务 | 镜像 | 端口 | 说明 |
|------|------|------|------|
| mysql | mysql:8.0 | 3306 | init.sql 自动建表+预置用户 |
| rabbitmq | rabbitmq:3-management | 5672/15672 | 自定义用户，健康检查 |
| adminer | adminer | 8080 | 数据库 Web 管理 |
| fastapi | Dockerfile | 8000 | depends_on mysql+rabbitmq |
| nginx | nginx:alpine | 80 | 反向代理 → fastapi:8000 |

## 预置测试数据（init.sql）

密码通过 `scripts/gen_password_hash.py` 预生成 bcrypt 哈希，硬编码写入 init.sql：

```sql
-- 建表语句 ...
-- (users, messages, outbox, message_receipts, failed_login_log)

-- 预置用户（bcrypt 哈希由 gen_password_hash.py 生成）
INSERT INTO users (username, password_hash, role) VALUES
('admin',    '$2b$12$...预生成的哈希...', 'admin'),
('adv_user', '$2b$12$...预生成的哈希...', 'advanced'),
('reg_user', '$2b$12$...预生成的哈希...', 'regular');

-- admin 密码: admin123
-- adv_user 密码: adv123
-- reg_user 密码: reg123
```

> `scripts/gen_password_hash.py` 用法: `python scripts/gen_password_hash.py admin123 adv123 reg123`，输出三个哈希值直接复制到 init.sql。

## 验证方案

### 正常流程
1. 复制 `.env.example` → `.env`，按需修改密钥
2. 运行 `python scripts/gen_password_hash.py` 生成哈希 → 替换 `init.sql` 中的占位符
3. `docker-compose up -d` 启动全部服务
4. `docker-compose logs -f fastapi` 查看日志
5. 访问 `http://localhost:8000/docs` Swagger UI
6. 管理员登录 → `POST /api/publish/batch` 发布 10 条
7. 观察日志：outbox 发布器逐条发送 + 3 个消费者每隔 10 秒处理一条
8. 管理员 `GET /api/messages` → 全部字段 + secret_data 明文 + 各通道耗时
9. 高级用户登录 `GET /api/messages` → content 截断 50 字 + `...[截断]`标记
10. 普通用户登录 `GET /api/messages` → 仅 title + published_at
11. 管理员 `GET /api/messages/stats` → 耗时汇总
12. `http://localhost:15672` RabbitMQ 管理界面查看队列
13. `http://localhost:8080` Adminer 查看数据库

### 异常流程
1. **注册越权**: 请求体含 `role=admin` → 忽略，注册为 regular
2. **登录锁定重置**: 输错 3 次 → 正确登录 → 检查 `failed_login_attempts=0`
3. **账户锁定**: 连续 5 次错误 → 第 6 次提示锁定
4. **限流**: 6 次/分钟 → 第 6 次返回 429
5. **重复消费幂等**: 模拟重启消费者 → `message_receipts` 无重复
6. **死信验证**: 消费者模拟失败 → `queue.dead` 中有消息
7. **健康检查**: `GET /health` → 返回 DB 和 RabbitMQ 状态

## 实施顺序

1. 创建 `.env.example`、`.gitignore`
2. 创建 `scripts/gen_password_hash.py`
3. 创建 `init.sql`（建表 + 预生成密码哈希后的预置用户）
4. 创建 `docker-compose.yml`、`Dockerfile`、`nginx.conf`
5. 创建 `requirements.txt`
6. 创建 `app/config.py`
7. 创建 `app/database.py`
8. 创建 `app/models/`（user.py、message.py）
9. 创建 `app/schemas/`（user.py、message.py — 含 MessagePublishedEvent + 三级响应 Schema）
10. 创建 `app/services/crypto.py`
11. 创建 `app/services/auth.py`
12. 创建 `app/middleware/auth.py`
13. 创建 `app/services/rabbitmq.py`（含 Publisher Confirms + 消费者 with 健壮性）
14. 创建 `app/services/outbox.py`（含 Publisher Confirms）
15. 创建 `app/api/health.py`
16. 创建 `app/api/auth.py`（含限流 + 锁定 + 登录成功后重置）
17. 创建 `app/api/publish.py`
18. 创建 `app/api/messages.py`（按角色 Schema 分发）
19. 创建 `app/main.py`（lifespan 管理全部协程 + 消费者健康监控）
20. 启动验证：正常 13 步 + 异常 7 步 全部通过
