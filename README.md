# TriCast — 消息发布订阅系统

基于 RabbitMQ + FastAPI + MySQL + Nginx 构建的消息发布/订阅演示系统。三种角色（管理员、高级用户、普通用户）实现消息持久化、权限分级、耗时统计。Tri = 三种角色，Cast = Fanout 广播。

## 快速启动

```bash
# 1. 生成密码哈希（如已生成可跳过）
python scripts/gen_password_hash.py admin123 adv123 reg123
# 将输出的哈希值替换到 init.sql 中

# 2. 复制环境变量
cp .env.example .env

# 3. 启动所有服务
docker compose up -d

# 4. 查看日志
docker compose logs -f fastapi
```

## 访问地址

| 服务 | 地址 | 认证 |
|------|------|------|
| API 文档 (Swagger) | http://localhost/docs | JWT |
| RabbitMQ 管理 | http://localhost:15672 | demo_user / demo_pass_2024 |
| 数据库管理 (Adminer) | http://localhost:8080 | 服务器填 `mysql`，root / root_pass_2024 |
| Nginx 反向代理 | http://localhost | — |

## 预置账号

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | admin123 | 管理员（发布消息 + 完整数据 + 统计） |
| adv_user | adv123 | 高级用户（content 截断 50 字） |
| reg_user | reg123 | 普通用户（仅标题和时间） |

## 技术栈

| 组件 | 技术 | 端口 |
|------|------|------|
| 消息队列 | RabbitMQ 3.x Management (aio_pika) | 5672 / 15672 |
| Web 服务器 | Nginx (反向代理) | 80 |
| 数据库 | MySQL 8.0 | 3306（宿主机映射 3307） |
| API 框架 | FastAPI (Python 3.11) | 8000 |
| 认证 | JWT (python-jose) + bcrypt | — |
| 加密 | AES-256-CBC (cryptography) | — |
| 限流 | slowapi | — |

## 项目结构

```
demo20250527/
├── app/
│   ├── main.py              # FastAPI 入口 + lifespan 管理后台协程
│   ├── config.py            # 全局配置（.env → Pydantic Settings）
│   ├── database.py          # SQLAlchemy async 引擎 + 会话工厂
│   ├── models/
│   │   ├── user.py          # User + FailedLoginLog + UserRole 枚举
│   │   └── message.py       # Message + MessageReceipt + Outbox
│   ├── schemas/
│   │   ├── user.py          # 注册/登录请求响应
│   │   └── message.py       # MessagePublishedEvent + 三级角色响应
│   ├── services/
│   │   ├── crypto.py        # AES-256-CBC 加解密
│   │   ├── auth.py          # JWT + bcrypt 密码哈希
│   │   ├── rabbitmq.py      # 连接管理 + 发布 + 消费者（永不退出）
│   │   └── outbox.py        # 事务发件箱后台发布器
│   ├── middleware/
│   │   └── auth.py          # JWT 认证依赖注入 + 角色校验
│   └── api/
│       ├── health.py        # GET /health 健康检查
│       ├── auth.py          # POST /api/auth/register + login
│       ├── publish.py       # POST /api/publish + /batch
│       └── messages.py      # GET /api/messages + /stats
├── docker-compose.yml       # 5 服务编排
├── Dockerfile               # FastAPI 容器镜像
├── nginx.conf               # 反向代理配置
├── init.sql                 # 建表 + 预置用户
├── requirements.txt         # Python 依赖
├── .env.example             # 环境变量模板
└── scripts/
    └── gen_password_hash.py # bcrypt 哈希生成工具
```

## API 端点

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/health` | 公开 | 数据库 + RabbitMQ 连接状态 |
| GET | `/health/consumers` | 公开 | 消费者协程运行状态 |
| POST | `/api/auth/register` | 公开 (5/min·IP) | 注册，强制角色为 regular |
| POST | `/api/auth/login` | 公开 (10/min·IP) | 登录，5 次失败锁定 15 分钟 |
| POST | `/api/publish` | admin | 单条发布（事务发件箱） |
| POST | `/api/publish/batch` | admin | 批量发布（最多 10 条） |
| GET | `/api/messages` | 登录 | 消息列表（按角色返回不同字段） |
| GET | `/api/messages/{id}` | 登录 | 消息详情（按角色返回不同字段） |
| GET | `/api/messages/stats` | admin | 各通道耗时统计（min/max/avg/count） |

## 数据可见性矩阵

| 字段 | 管理员 (admin) | 高级用户 (advanced) | 普通用户 (regular) |
|------|:---:|:---:|:---:|
| id | ✅ | ✅ | ✅ |
| title | ✅ | ✅ | ✅ |
| content | ✅ 完整 | ✅ 截断 50 字 + `...[truncated]` | ❌ |
| secret_data | ✅ AES 解密后 | ❌ | ❌ |
| publisher | ✅ | ✅ | ❌ |
| published_at | ✅ | ✅ | ✅ |
| receipts (耗时列表) | ✅ | ❌ | ❌ |
| channel | ✅ | ✅ | ❌ |

## RabbitMQ 架构

```
                     ┌──────────────────────┐
                     │   Fanout Exchange    │
                     │   "msg.fanout"       │
                     │  (Publisher Confirms)│
                     └──────────┬───────────┘
                                │
         ┌──────────────────────┼──────────────────────┐
         │                      │                      │
  ┌──────▼──────┐        ┌──────▼──────┐        ┌──────▼──────┐
  │ queue.admin │        │queue.advanced│        │queue.regular│
  │  prefetch=1 │        │  prefetch=1  │        │  prefetch=1  │
  │  manual_ack │        │  manual_ack  │        │  manual_ack  │
  └──────┬──────┘        └──────┬──────┘        └──────┬──────┘
         │                      │                      │
   消费者(admin)          消费者(advanced)        消费者(regular)
         │                      │                      │
         └──────────────────────┼──────────────────────┘
                                │ NACK (requeue=False)
                         ┌──────▼──────┐
                         │   DLX       │
                         │ "msg.dlx"   │
                         └──────┬──────┘
                                │
                         ┌──────▼──────┐
                         │ queue.dead  │  ← 演示环境仅收集
                         └─────────────┘
```

- **Fanout Exchange**: 所有消息广播到全部绑定的队列
- **Publisher Confirms**: 发布端启用，RabbitMQ ACK 后才标记 outbox 为 `published`
- **消息 TTL**: 60 秒，超时未消费 → DLX
- **手动 ACK**: 回执写入成功后才 `basic_ack`，失败 `basic_nack(requeue=False)` → DLX
- **prefetch_count=1**: 每次只取一条，保证顺序处理
- **幂等性**: `message_receipts` 的 `UNIQUE(message_id, consumer_role)` 约束

## 消息处理流程

```
[管理员 POST /api/publish]
    │
    ├── 1. DB 事务: INSERT messages + INSERT outbox(pending) → COMMIT
    │
    ├── 2. Outbox 发布器 (asyncio.Task, 每 2 秒轮询)
    │       ├── SELECT pending ORDER BY id LIMIT 10
    │       ├── 逐条发布到 RabbitMQ (Publisher Confirms)
    │       ├── RabbitMQ ACK → 标记 published
    │       └── RabbitMQ NACK/超时 → retry_count++ (最多 3 次)
    │
    └── 3. 消费者协程（永不退出）
            ├── 解析 MessagePublishedEvent
            ├── 计算处理耗时
            ├── 写入 message_receipts（3 次指数退避重试）
            ├── IntegrityError → 幂等跳过
            ├── 成功 → basic_ack
            └── 失败 → basic_nack(requeue=False) → DLX → queue.dead
```

## 安全措施

| 措施 | 实现 |
|------|------|
| 注册角色限制 | 强制 regular，忽略请求中的 role 字段 |
| RabbitMQ 认证 | 自定义用户密码，禁用 guest |
| secret_data 加密 | AES-256-CBC，密钥来自环境变量 |
| JWT 认证 | HS256，密钥来自环境变量 |
| 密码哈希 | bcrypt (rounds=12) |
| 登录限流 | slowapi 按 IP 限流 |
| 暴力破解防护 | 5 次失败锁定 15 分钟，成功登录重置计数 |
| 字段泄露防护 | 三级独立 Pydantic Schema，ORM 对象不直接序列化 |
| .env 保护 | .gitignore 排除 |

## 数据一致性

| 措施 | 实现 |
|------|------|
| 事务发件箱 | messages + outbox 在同一 DB 事务提交 |
| Publisher Confirms | RabbitMQ ACK 后标记 published |
| 手动 ACK | receipt 写入成功后才 ACK |
| 死信队列 | NACK → DLX → queue.dead |
| 幂等性 | UNIQUE(message_id, consumer_role) + IntegrityError 捕获 |
| 连接重试 | 消费者异常后 3 秒自动重连 |
| DB 写入重试 | message_receipts 写入 3 次指数退避 (1s/2s/4s) |

## 环境变量 (.env)

```bash
# MySQL（宿主机映射端口 3307，容器内 3306）
MYSQL_HOST=mysql
MYSQL_PORT=3306
MYSQL_USER=demo_user
MYSQL_PASSWORD=demo_pass_2024
MYSQL_DATABASE=demo_db
MYSQL_ROOT_PASSWORD=root_pass_2024

# RabbitMQ
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
RABBITMQ_USER=demo_user
RABBITMQ_PASSWORD=demo_pass_2024

# JWT
JWT_SECRET_KEY=change-me-to-a-random-string-at-least-32-chars
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60

# AES-256（必须恰好 32 字节）
AES_ENCRYPTION_KEY=0123456789abcdef0123456789abcdef

# 消费者处理间隔（秒，演示用）
CONSUME_INTERVAL_SECONDS=10
```

## 已知局限

1. **死信队列**: 仅收集不处理，生产环境需增加监控/重试/告警
2. **pool_pre_ping**: 因 aiomysql/asyncmy 驱动 ping() 签名不兼容而禁用，连接验证依赖 DB 写入重试
3. **HTTPS**: 演示环境使用 HTTP，生产环境需在 Nginx 层启用 HTTPS
4. **注册密码强度**: 当前无强制策略，代码中保留校验接口供扩展
5. **重复发布**: Outbox 发布成功但状态更新失败时，下次轮询会重复发布，依赖消费者幂等性屏蔽
