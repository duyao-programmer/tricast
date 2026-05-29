# TriCast — 消息发布订阅系统

基于 React 18 + FastAPI + RabbitMQ + MySQL + Redis + Nginx 构建的消息发布/订阅演示系统。三角色权限分级、消息标签订阅、组件级视图管理。

## 快速启动

```bash
# 1. 启动所有服务（首次需拉取镜像）
docker compose up -d

# 2. 打开浏览器
# https://localhost
```

## 访问地址

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端页面 | `https://localhost` | SPA 入口 |
| API 文档 | `https://localhost/docs` | Swagger |
| RabbitMQ 管理 | `http://localhost:15672` | demo_user / demo_pass_2024 |
| 数据库管理 | `http://localhost:8080` | Adminer，服务器填 `mysql` |

## 预置账号

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | admin123 | 管理员 |
| adv_user | adv123 | 高级用户 |
| reg_user | reg123 | 普通用户 |

## 技术栈

| 组件 | 技术 | 端口 |
|------|------|------|
| 前端 | React 18 + React Router + Axios | 443 (Nginx) |
| API | FastAPI (Python 3.11) | 8000 (内部) |
| 消息队列 | RabbitMQ 3.x (aio_pika) | 5672 / 15672 |
| 数据库 | MySQL 8.0 (asyncmy) | 3307 (宿主机) |
| 缓存 | Redis 7 (redis-py) | 6379 |
| 反向代理 | Nginx (HTTPS + auth_request) | 80 / 443 |
| 认证 | JWT (HttpOnly Cookie) + bcrypt | — |
| 加密 | AES-256-CBC | — |

## 项目结构

```
demo20250527/
├── frontend/                   # React 18 SPA
│   ├── src/
│   │   ├── api/client.js       # Axios 实例（Cookie 鉴权）
│   │   ├── context/            # AuthContext, PermissionContext, ToastContext
│   │   ├── hooks/              # usePermission
│   │   ├── components/         # Layout, Sidebar, Logo, ProtectedRoute, PermissionGuard
│   │   └── pages/              # 14 个页面组件
│   ├── Dockerfile              # 多阶段构建（Node → Nginx）
│   └── package.json
├── app/
│   ├── main.py                 # FastAPI 入口 + lifespan
│   ├── config.py               # 全局配置
│   ├── database.py             # SQLAlchemy async 引擎
│   ├── models/                 # ORM（User, Message, Permission, Subscription）
│   ├── schemas/                # Pydantic Schema
│   ├── services/               # crypto, auth, rabbitmq, outbox, redis
│   ├── middleware/auth.py      # JWT Cookie 鉴权 + 角色缓存 + 黑名单
│   └── api/                    # health, auth, verify, publish, messages, admin, subscriptions, dashboard
├── docker-compose.yml          # 6 服务编排
├── nginx.conf                  # HTTPS + auth_request + CSP + charset
├── init.sql                    # 建表 + 预置数据
├── .env.example
└── scripts/
```

## API 端点

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/health` | 公开 | 健康检查 |
| POST | `/api/auth/register` | 公开 | 注册（强制 regular） |
| POST | `/api/auth/login` | 公开 | 登录（HttpOnly Cookie） |
| POST | `/api/auth/logout` | 公开 | 登出（Redis 黑名单） |
| POST | `/api/auth/change-password` | 登录 | 修改密码 |
| POST | `/api/publish` | admin | 发布消息（支持标签） |
| GET | `/api/messages` | 登录 | 消息列表（搜索+筛选+分页） |
| GET | `/api/messages/{id}` | 登录 | 消息详情 |
| GET | `/api/messages/stats` | admin | 通道耗时统计 |
| GET | `/api/messages/dead` | admin | 死信队列 |
| GET | `/api/messages/export` | admin | 导出 CSV/JSON |
| GET | `/api/messages/tags` | 登录 | 标签列表 |
| GET | `/api/subscriptions` | 登录 | 订阅管理 |
| PUT | `/api/subscriptions` | 登录 | 更新订阅 |
| GET | `/api/dashboard/stats` | 登录 | 仪表盘统计 |
| GET | `/api/user/permissions` | 登录 | 当前用户权限 |
| GET | `/api/admin/permissions` | admin | 角色权限配置 |
| PUT | `/api/admin/permissions` | admin | 更新角色权限 |
| GET | `/api/admin/users` | admin | 用户列表 |
| GET | `/api/admin/users/{id}/permissions` | admin | 用户权限详情 |
| PUT | `/api/admin/users/{id}/permissions` | admin | 用户权限覆盖 |

## 功能特性

- **HttpOnly Cookie 鉴权** — JWT 存在 Cookie，浏览器自动携带，刷新不丢失
- **Nginx auth_request 统一拦截** — 未登录自动跳转 /login
- **Redis 缓存** — 角色缓存、JWT 黑名单、死信持久化、权限缓存
- **消息标签订阅** — 8 种标签（全员/放假/食堂/宿舍/技术/行政/人事/财务），默认订阅 + 可选订阅
- **三级角色数据隔离** — 独立 Pydantic Schema 按角色返回不同字段
- **组件级权限管理** — 管理员通过 UI 控制每个角色/用户的可见组件（grant/deny）
- **仪表盘** — 统计卡片（可点击跳转）+ 标签分布 + 7天趋势
- **全文搜索** — 标题+内容关键词搜索
- **消息导出** — CSV / JSON
- **无限滚动** — 消息列表自动加载
- **密码修改** — 用户自行修改密码
- **自签名 HTTPS** — Nginx TLS 1.2/1.3
