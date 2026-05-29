# ============================================================================
# 全局配置（从 .env 加载）
# ============================================================================
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用全局配置，自动从 .env 文件和环境变量加载"""

    # MySQL 配置
    mysql_host: str = "mysql"
    mysql_port: int = 3306
    mysql_user: str = "demo_user"
    mysql_password: str = "demo_pass_2024"
    mysql_database: str = "demo_db"
    mysql_root_password: str = "root_pass_2024"

    # RabbitMQ 配置
    rabbitmq_host: str = "rabbitmq"
    rabbitmq_port: int = 5672
    rabbitmq_user: str = "demo_user"
    rabbitmq_password: str = "demo_pass_2024"
    rabbitmq_mgmt_port: int = 15672

    # Redis 配置
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""

    # JWT 配置
    jwt_secret_key: str = "change-me-to-a-random-string-at-least-32-chars"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # AES-256 加密配置（必须恰好 32 字节）
    aes_encryption_key: str = "0123456789abcdef0123456789abcdef"

    # 消费者配置
    consume_interval_seconds: int = 10

    # 应用配置
    app_env: str = "development"
    app_debug: bool = True

    @property
    def redis_url(self) -> str:
        """构建 Redis 连接 URL"""
        pw = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{pw}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def mysql_url(self) -> str:
        """构建异步 MySQL 连接 URL（使用 asyncmy 驱动）"""
        return (
            f"mysql+asyncmy://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
            f"?charset=utf8mb4"
        )

    @property
    def rabbitmq_url(self) -> str:
        """构建 RabbitMQ 连接 URL"""
        return (
            f"amqp://{self.rabbitmq_user}:{self.rabbitmq_password}"
            f"@{self.rabbitmq_host}:{self.rabbitmq_port}/"
        )

    @property
    def aes_key_bytes(self) -> bytes:
        """获取 AES 密钥的字节形式，确保长度恰好 32 字节"""
        key = self.aes_encryption_key.encode("utf-8")
        if len(key) != 32:
            raise ValueError(f"AES 密钥必须恰好 32 字节，当前为 {len(key)} 字节")
        return key

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


# 全局配置单例
settings = Settings()
