import os
from dataclasses import dataclass
from pika import PlainCredentials
from dotenv import load_dotenv

load_dotenv()

@dataclass
class RabbitMQConfig:
    host: str
    port: int
    user: str
    password: str
    queue: str

    @property
    def connection_params(self) -> dict:
        return {
            'host': self.host,
            'port': self.port,
            'credentials': self._get_credentials()
        }

    def _get_credentials(self):

        return PlainCredentials(self.user, self.password)


@dataclass
class PostgresConfig:
    host: str
    port: int
    user: str
    password: str
    database: str
    table: str

    @property
    def connection_string(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


@dataclass
class AppConfig:
    rabbitmq: RabbitMQConfig
    postgres: PostgresConfig
    log_level: str
    retry_count: int

    @classmethod
    def from_env(cls) -> 'AppConfig':
        return cls(
            rabbitmq=RabbitMQConfig(
                host=os.getenv('RABBITMQ_HOST', 'localhost'),
                port=int(os.getenv('RABBITMQ_PORT', '5672')),
                user=os.getenv('RABBITMQ_USER', 'guest'),
                password=os.getenv('RABBITMQ_PASS', 'guest'),
                queue=os.getenv('RABBITMQ_QUEUE', 'messages_queue')
            ),
            postgres=PostgresConfig(
                host=os.getenv('POSTGRES_HOST', 'localhost'),
                port=int(os.getenv('POSTGRES_PORT', '5432')),
                user=os.getenv('POSTGRES_USER', 'postgres'),
                password=os.getenv('POSTGRES_PASS', 'postgres'),
                database=os.getenv('POSTGRES_DB', 'messages_db'),
                table=os.getenv('POSTGRES_TABLE', 'messages')
            ),
            log_level=os.getenv('LOG_LEVEL', 'INFO'),
            retry_count=int(os.getenv('RETRY_COUNT', '3'))
        )


config = AppConfig.from_env()