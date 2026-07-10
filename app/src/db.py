import json
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy import create_engine, Column, Integer, JSON, DateTime, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

from config import config
import logging

logger = logging.getLogger(__name__)

Base = declarative_base()


class Message(Base):

    __tablename__ = config.postgres.table

    id = Column(Integer, primary_key=True, autoincrement=True)
    payload = Column(JSON, nullable=False)
    received_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow
    )
    processed_at = Column(
        DateTime(timezone=True),
        nullable=True
    )


class DatabaseManager:
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self._connect()

    def _connect(self):
        try:
            connection_string = config.postgres.connection_string
            self.engine = create_engine(
                connection_string,
                pool_pre_ping=True,
                pool_recycle=3600,
                echo=False
            )
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )


            self._create_table()

            logger.info("Successfully connected to PostgreSQL")

        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise

    def _create_table(self):
        Base.metadata.create_all(bind=self.engine)
        logger.info(f"Table '{config.postgres.table}' is ready")

    def save_message(self, payload: Dict[str, Any]) -> Optional[int]:
        session = self.SessionLocal()
        try:
            message = Message(
                payload=payload,
                processed_at=datetime.utcnow()
            )

            session.add(message)
            session.commit()

            message_id = message.id
            logger.info(f"Message saved successfully with ID: {message_id}")
            return message_id

        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error while saving message: {e}")
            raise
        except Exception as e:
            session.rollback()
            logger.error(f"Unexpected error while saving message: {e}")
            raise
        finally:
            session.close()

    def health_check(self) -> bool:
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


db_manager = DatabaseManager()