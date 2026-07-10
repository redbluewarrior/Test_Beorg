import pika
import json
import time
from typing import Optional, Callable, Dict, Any
from pika.exceptions import AMQPConnectionError, ChannelClosedByBroker

from config import config
import logging

logger = logging.getLogger(__name__)


class RabbitMQManager:

    def __init__(self):
        self.connection = None
        self.channel = None
        self._connect()

    def _connect(self):
        try:
            params = pika.ConnectionParameters(
                host=config.rabbitmq.host,
                port=config.rabbitmq.port,
                credentials=pika.PlainCredentials(
                    config.rabbitmq.user,
                    config.rabbitmq.password
                ),
                heartbeat=600,
                blocked_connection_timeout=300
            )

            self.connection = pika.BlockingConnection(params)
            self.channel = self.connection.channel()

            self.channel.queue_declare(
                queue=config.rabbitmq.queue,
                durable=True,
                exclusive=False,
                auto_delete=False
            )

            self.channel.basic_qos(prefetch_count=1)

            logger.info(f"Connected to RabbitMQ. Queue: {config.rabbitmq.queue}")

        except AMQPConnectionError as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error connecting to RabbitMQ: {e}")
            raise

    def start_consuming(self, callback: Callable[[Dict[str, Any]], bool]):
        if not self.channel:
            logger.error("Channel not available. Cannot start consuming.")
            return

        def _callback(ch, method, properties, body):
            try:
                message = json.loads(body.decode('utf-8'))
                logger.info(f"Received message: {message}")

                success = callback(message)

                if success:
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                    logger.info("Message processed successfully, ACK sent")
                else:
                    ch.basic_nack(
                        delivery_tag=method.delivery_tag,
                        requeue=True
                    )
                    logger.warning("Message processing failed, NACK sent")

            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON message: {e}")
                ch.basic_nack(
                    delivery_tag=method.delivery_tag,
                    requeue=True
                )
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                ch.basic_nack(
                    delivery_tag=method.delivery_tag,
                    requeue=True
                )

        self.channel.basic_consume(
            queue=config.rabbitmq.queue,
            on_message_callback=_callback,
            auto_ack=False
        )

        logger.info("Started consuming messages. Waiting for messages...")

        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            logger.info("Consumer interrupted by user")
            self.stop_consuming()
        except Exception as e:
            logger.error(f"Error in consuming loop: {e}")
            self.stop_consuming()
            raise

    def stop_consuming(self):
        try:
            if self.channel:
                self.channel.stop_consuming()
            if self.connection and not self.connection.is_closed:
                self.connection.close()
            logger.info("Stopped consuming messages")
        except Exception as e:
            logger.error(f"Error stopping consumer: {e}")

    def health_check(self) -> bool:
        try:
            if not self.connection or self.connection.is_closed:
                self._connect()
            return True
        except Exception as e:
            logger.error(f"RabbitMQ health check failed: {e}")
            return False



rabbitmq_manager = RabbitMQManager()