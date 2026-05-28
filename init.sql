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
-- 预置用户（密码通过 scripts/gen_password_hash.py 生成后替换）
-- 默认密码: admin123 / adv123 / reg123
-- 注意：以下哈希值为占位符，部署前必须运行 gen_password_hash.py 生成真实哈希
-- ============================================================================
INSERT INTO users (username, password_hash, role) VALUES
('admin',    '$2b$12$g2iiT01tj5rZEQ1ulzJV8.ei9ZN22ObfXiKPrETKn0AsztNByU8Da', 'admin'),
('adv_user', '$2b$12$xIlwxyU1EXm6V7IjttmRueGtvbztHNQTKhx7BPZeT.rW6K/I4sUnO', 'advanced'),
('reg_user', '$2b$12$YCzcqcPcWUPgjCNOqRs9Xetl7psSFckLh2CPu5cyTpxC66JBcOmim', 'regular');
