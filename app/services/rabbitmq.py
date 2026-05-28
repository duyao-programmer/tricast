# ============================================================================
# RabbitMQ 连接管理 + 发布(含 Publisher Confirms) + 消费者
# ============================================================================
import asyncio
import aio_pika
from aio_pika import ExchangeType, Message, DeliveryMode
from aio_pika.abc import AbstractRobustExchange, AbstractRobustQueue
from app.config import settings
from loguru import logger

# ============================================================================
# 交换机和队列名称常量
# ============================================================================
EXCHANGE_NAME = "msg.fanout"
DLX_EXCHANGE_NAME = "msg.dlx"
QUEUE_ADMIN = "queue.admin"
QUEUE_ADVANCED = "queue.advanced"
QUEUE_REGULAR = "queue.regular"
QUEUE_DEAD = "queue.dead"


async def setup_rabbitmq_infrastructure() -> aio_pika.RobustConnection:
    """
    初始化 RabbitMQ 连接并声明所有交换机和队列

    声明顺序：
    1. 死信交换机 msg.dlx（fanout）
    2. 死信队列 queue.dead 绑定到 msg.dlx
    3. 业务交换机 msg.fanout（fanout）
    4. 三个消费者队列（queue.admin / queue.advanced / queue.regular），
       每个队列绑定 msg.fanout，并设置 DLX + 消息 TTL
    """
    connection = await aio_pika.connect_robust(
        settings.rabbitmq_url,
        timeout=30,
    )

    async with connection.channel() as channel:
        # 1. 死信交换机
        dlx_exchange = await channel.declare_exchange(
            DLX_EXCHANGE_NAME,
            ExchangeType.FANOUT,
            durable=True,
        )

        # 2. 死信队列
        dead_queue = await channel.declare_queue(
            QUEUE_DEAD,
            durable=True,
        )
        await dead_queue.bind(dlx_exchange)

        # 3. 业务交换机
        exchange = await channel.declare_exchange(
            EXCHANGE_NAME,
            ExchangeType.FANOUT,
            durable=True,
        )

        # 4. 三个消费者队列
        dlx_arguments = {
            "x-dead-letter-exchange": DLX_EXCHANGE_NAME,
            "x-message-ttl": 60000,  # 60 秒 TTL
        }

        for queue_name in (QUEUE_ADMIN, QUEUE_ADVANCED, QUEUE_REGULAR):
            queue = await channel.declare_queue(
                queue_name,
                durable=True,
                arguments=dlx_arguments,
            )
            await queue.bind(exchange)

    logger.info("RabbitMQ 基础设施初始化完成：交换机、队列、DLX 已就绪")
    return connection


async def publish_message(event_json: str) -> bool:
    """
    发布消息到 msg.fanout 交换机（含 Publisher Confirms）

    Args:
        event_json: MessagePublishedEvent 序列化的 JSON 字符串

    Returns:
        bool: 发布是否被 RabbitMQ 确认
    """
    connection = await aio_pika.connect_robust(
        settings.rabbitmq_url,
        timeout=30,
    )

    async with connection.channel() as channel:
        exchange = await channel.get_exchange(EXCHANGE_NAME)

        message = Message(
            body=event_json.encode("utf-8"),
            delivery_mode=DeliveryMode.PERSISTENT,
            content_type="application/json",
        )

        await exchange.publish(
            message,
            routing_key="",
            mandatory=True,  # Publisher Confirms: 确保至少有一个队列接收
        )

    logger.debug("消息已发布到 RabbitMQ")
    return True


async def consume_queue(
    queue_name: str,
    consumer_role: str,
    callback,
    shutdown_event: asyncio.Event,
):
    """
    消费者协程：从指定队列消费消息，永不退出

    Args:
        queue_name: 队列名称
        consumer_role: 消费者角色（admin/advanced/regular）
        callback: 消息处理回调函数 async def(msg_body, consumer_role)
        shutdown_event: 关闭信号
    """
    logger.info("消费者 [{}/{}] 启动", consumer_role, queue_name)

    while not shutdown_event.is_set():
        try:
            connection = await aio_pika.connect_robust(
                settings.rabbitmq_url,
                timeout=30,
            )

            async with connection.channel() as channel:
                await channel.set_qos(prefetch_count=1)

                # passive=True: 仅检查队列是否存在，不重新声明（避免参数冲突）
                queue = await channel.declare_queue(
                    queue_name,
                    durable=True,
                    passive=True,
                )

                async with queue.iterator() as queue_iter:
                    async for raw_message in queue_iter:
                        if shutdown_event.is_set():
                            break

                        try:
                            await callback(raw_message.body, consumer_role)
                            await raw_message.ack()
                            logger.debug(
                                "消费者 [{}/{}] 已 ACK 消息",
                                consumer_role, queue_name,
                            )
                        except Exception as exc:
                            logger.exception(
                                "消费者 [{}/{}] 处理失败，NACK 进入死信: {}",
                                consumer_role, queue_name, exc,
                            )
                            try:
                                await raw_message.nack(requeue=False)
                            except Exception:
                                pass

                        # 演示用处理间隔
                        if settings.consume_interval_seconds > 0:
                            await asyncio.sleep(settings.consume_interval_seconds)

        except asyncio.CancelledError:
            logger.info("消费者 [{}/{}] 收到取消信号", consumer_role, queue_name)
            break
        except Exception as exc:
            logger.exception(
                "消费者 [{}/{}] 异常退出，3 秒后重连: {}",
                consumer_role, queue_name, exc,
            )
            await asyncio.sleep(3)

    logger.info("消费者 [{}/{}] 已关闭", consumer_role, queue_name)
