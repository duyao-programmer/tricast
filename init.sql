-- ============================================================================
-- 消息发布订阅系统 - 数据库初始化脚本
-- ============================================================================

CREATE DATABASE IF NOT EXISTS demo_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE demo_db;

-- ============================================================================
-- 用户表
-- ============================================================================
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin', 'advanced', 'regular') NOT NULL DEFAULT 'regular',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    failed_login_attempts INT NOT NULL DEFAULT 0,
    locked_until TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 消息表
-- ============================================================================
CREATE TABLE IF NOT EXISTS messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    secret_data_encrypted TEXT COMMENT 'AES-256-CBC 加密的敏感数据',
    publisher_id INT NOT NULL,
    published_at TIMESTAMP(3) DEFAULT CURRENT_TIMESTAMP(3),
    FOREIGN KEY (publisher_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 事务发件箱表
-- ============================================================================
CREATE TABLE IF NOT EXISTS outbox (
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 消息回执表（消费者处理记录）
-- ============================================================================
CREATE TABLE IF NOT EXISTS message_receipts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    message_id INT NOT NULL,
    consumer_role ENUM('admin', 'advanced', 'regular') NOT NULL,
    channel VARCHAR(20) NOT NULL,
    received_at TIMESTAMP(3) DEFAULT CURRENT_TIMESTAMP(3),
    processing_time_ms INT COMMENT '毫秒',
    FOREIGN KEY (message_id) REFERENCES messages(id),
    UNIQUE KEY uk_msg_role (message_id, consumer_role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 登录失败日志表
-- ============================================================================
CREATE TABLE IF NOT EXISTS failed_login_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    ip_address VARCHAR(45) NOT NULL,
    attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 组件权限配置表（管理员通过 UI 管理各角色可见的组件）
-- ============================================================================
CREATE TABLE IF NOT EXISTS role_component_permissions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    role VARCHAR(50) NOT NULL COMMENT '角色名，不用ENUM以便未来扩展',
    component_key VARCHAR(100) NOT NULL COMMENT '组件唯一标识',
    allowed BOOLEAN NOT NULL DEFAULT FALSE COMMENT '是否允许该角色看到此组件',
    description VARCHAR(200) COMMENT '组件中文说明',
    UNIQUE KEY uk_role_component (role, component_key),
    INDEX idx_role (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- 预置权限数据（8个组件 × 3个角色 = 24条）
-- ============================================================================
INSERT INTO role_component_permissions (role, component_key, allowed, description) VALUES
-- 管理员
('admin', 'dashboard',              TRUE, '仪表盘首页'),
('admin', 'message_list',           TRUE, '消息列表'),
('admin', 'message_detail',         TRUE, '消息详情'),
('admin', 'message_stats',          TRUE, '耗时统计'),
('admin', 'dead_letters',           TRUE, '死信查看'),
('admin', 'publish_message',        TRUE, '发布消息'),
('admin', 'user_management',        TRUE, '用户管理'),
('admin', 'permission_management',  TRUE, '权限管理'),
-- 高级用户
('advanced', 'dashboard',           TRUE,  '仪表盘首页'),
('advanced', 'message_list',        TRUE,  '消息列表'),
('advanced', 'message_detail',      TRUE,  '消息详情'),
('advanced', 'message_stats',       FALSE, '耗时统计'),
('advanced', 'dead_letters',        FALSE, '死信查看'),
('advanced', 'publish_message',     FALSE, '发布消息'),
('advanced', 'user_management',     FALSE, '用户管理'),
('advanced', 'permission_management',FALSE, '权限管理'),
-- 普通用户
('regular', 'dashboard',            TRUE,  '仪表盘首页'),
('regular', 'message_list',         TRUE,  '消息列表'),
('regular', 'message_detail',       TRUE,  '消息详情'),
('regular', 'message_stats',        FALSE, '耗时统计'),
('regular', 'dead_letters',         FALSE, '死信查看'),
('regular', 'publish_message',      FALSE, '发布消息'),
('regular', 'user_management',      FALSE, '用户管理'),
('regular', 'permission_management',FALSE, '权限管理');

-- ============================================================================
-- 预置用户（密码通过 scripts/gen_password_hash.py 生成后替换）
-- 默认密码: admin123 / adv123 / reg123
-- 注意：以下哈希值为占位符，部署前必须运行 gen_password_hash.py 生成真实哈希
-- ============================================================================
INSERT INTO users (username, password_hash, role) VALUES
('admin',    '$2b$12$g2iiT01tj5rZEQ1ulzJV8.ei9ZN22ObfXiKPrETKn0AsztNByU8Da', 'admin'),
('adv_user', '$2b$12$xIlwxyU1EXm6V7IjttmRueGtvbztHNQTKhx7BPZeT.rW6K/I4sUnO', 'advanced'),
('reg_user', '$2b$12$YCzcqcPcWUPgjCNOqRs9Xetl7psSFckLh2CPu5cyTpxC66JBcOmim', 'regular');
