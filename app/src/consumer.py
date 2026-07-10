import sys
import signal
import logging
import time
from typing import Dict, Any
from datetime import datetime

from config import config
from db import db_manager
from rabbitmq import rabbitmq_manager

import threading
from health import run_health_server

def setup_logging():

    log_level = getattr(logging, config.log_level.upper(), logging.INFO)

    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    logging.getLogger('pika').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

    return logging.getLogger(__name__)


logger = setup_logging()


def validate_message(message: Dict[str, Any]) -> bool:

    if not isinstance(message, dict):
        logger.error("Message is not a dictionary")
        return False

    if "data" not in message:
        logger.error("Message missing 'data' field")
        return False

    if "metadata" not in message:
        logger.error("Message missing 'metadata' field")
        return False

    if not isinstance(message["metadata"], dict):
        logger.error("Metadata is not a dictionary")
        return False

    if "timestamp" not in message["metadata"]:
        logger.warning("Metadata missing 'timestamp' field, but continuing")

    message["processing_time"] = datetime.utcnow().isoformat()

    return True


def process_message(message: Dict[str, Any]) -> bool:
    logger.info(f"Processing message: {message}")

    if not validate_message(message):
        logger.error("Message validation failed")
        return False

    for attempt in range(config.retry_count):
        try:
            message_id = db_manager.save_message(message)

            if message_id:
                logger.info(
                    f"Saved after attempt {attempt + 1}"
                )
                return True

        except Exception as e:
            logger.error(
                f"Attempt {attempt + 1} failed: {e}"
            )

            time.sleep(1)

    logger.error("Retry limit exceeded")
    return False


def health_check() -> bool:
    db_healthy = db_manager.health_check()
    rabbitmq_healthy = rabbitmq_manager.health_check()

    healthy = db_healthy and rabbitmq_healthy
    if not healthy:
        logger.warning(
            f"Health check failed - DB: {db_healthy}, RabbitMQ: {rabbitmq_healthy}"
        )

    return healthy


def signal_handler(sig, frame):
    logger.info(f"Received signal {sig}, shutting down...")
    rabbitmq_manager.stop_consuming()
    sys.exit(0)


def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("=" * 50)
    logger.info("Starting Message Processor Microservice")
    logger.info(f"RabbitMQ Queue: {config.rabbitmq.queue}")
    logger.info(f"PostgreSQL Table: {config.postgres.table}")
    logger.info(f"Log Level: {config.log_level}")
    logger.info(f"Retry Count: {config.retry_count}")
    logger.info("=" * 50)

    if not health_check():
        logger.error("Initial health check failed. Exiting...")
        sys.exit(1)

    try:
        rabbitmq_manager.start_consuming(process_message)
    except Exception as e:
        logger.error(f"Fatal error in main loop: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
