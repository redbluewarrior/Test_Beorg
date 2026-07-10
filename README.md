# Микросервис обработки сообщений

## Обзор

Микросервис для обработки сообщений из RabbitMQ и сохранения их в PostgreSQL с обеспечением надежности и отказоустойчивости.

## Технологии

- Python 3.11+
- RabbitMQ 3.12+
- PostgreSQL 15+
- SQLAlchemy
- Pika
- Docker

## Структура проекта

```
app/
├── src/
│   ├── config.py          # Управление конфигурацией
│   ├── consumer.py        # Логика обработки сообщений
│   ├── db.py              # Операции с БД
│   ├── health.py          # Health check эндпоинт
│   └── rabbitmq.py        # Подключение к RabbitMQ
├── .env.example           # Шаблон переменных окружения
├── docker-compose.yml     # Оркестрация Docker
├── Dockerfile             # Определение контейнера
└── requirements.txt       # Зависимости Python
```

## Быстрый старт

### Требования

- Docker 24.0+
- Docker Compose 2.20+

### Установка

```bash
# Клонирование репозитория
git clone <repository-url>
cd message-processor

# Копирование конфигурации окружения
cp app/.env.example .env

# Запуск сервисов
docker-compose up -d --build

# Просмотр логов
docker-compose logs -f app
```

### Отправка тестового сообщения

```bash
# Через веб-интерфейс RabbitMQ
# Откройте http://localhost:15672 (guest:guest)
# Перейдите в очереди и опубликуйте сообщение

# Или через командную строку
docker-compose exec app python -c "
import pika, json
params = pika.ConnectionParameters('rabbitmq')
conn = pika.BlockingConnection(params)
ch = conn.channel()
ch.basic_publish(
    exchange='',
    routing_key='messages_queue',
    body=json.dumps({
        'data': {'test': 'message'},
        'metadata': {'timestamp': 1234567890}
    })
)
conn.close()
"
```

### Проверка данных

```bash
# Подключение к PostgreSQL
docker-compose exec postgres psql -U postgres -d messages_db

# Запрос сообщений
SELECT * FROM messages ORDER BY id DESC LIMIT 10;
```

## Конфигурация

Все настройки через переменные окружения:

| Переменная | Описание | Значение по умолчанию |
|------------|----------|----------------------|
| RABBITMQ_HOST | Хост RabbitMQ | rabbitmq |
| RABBITMQ_PORT | Порт RabbitMQ | 5672 |
| RABBITMQ_USER | Имя пользователя RabbitMQ | guest |
| RABBITMQ_PASS | Пароль RabbitMQ | guest |
| RABBITMQ_QUEUE | Имя очереди | messages_queue |
| POSTGRES_HOST | Хост PostgreSQL | postgres |
| POSTGRES_PORT | Порт PostgreSQL | 5432 |
| POSTGRES_USER | Имя пользователя PostgreSQL | postgres |
| POSTGRES_PASS | Пароль PostgreSQL | postgres |
| POSTGRES_DB | Имя БД | messages_db |
| POSTGRES_TABLE | Имя таблицы | messages |
| LOG_LEVEL | Уровень логирования (DEBUG/INFO/ERROR) | INFO |
| RETRY_COUNT | Количество попыток повторной обработки | 3 |

## Схема БД

```sql
CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    payload JSON NOT NULL,
    received_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP WITH TIME ZONE
);
```

## Формат сообщения

Ожидаемая структура JSON:

```json
{
    "data": {
        /* любые данные */
    },
    "metadata": {
        "timestamp": 1234567890 /* секунды */
    }
}
```

## API эндпоинты

### Health Check

```bash
GET /health

# Ответ
{
    "status": "healthy",
    "timestamp": "2024-01-15T10:30:45.123456",
    "services": {
        "database": "up",
        "rabbitmq": "up"
    }
}
```

## Команды Docker

```bash
# Запуск всех сервисов
docker-compose up -d

# Остановка сервисов
docker-compose down

# Перезапуск приложения
docker-compose restart app

# Просмотр логов
docker-compose logs -f app

# Удаление томов (сброс БД)
docker-compose down -v
```

## Мониторинг

- RabbitMQ Management: http://localhost:15672 (guest:guest)
- Health Check: http://localhost:8080/health
- PostgreSQL: docker-compose exec postgres psql -U postgres -d messages_db

## Сценарий работы

1. Сервис подключается к RabbitMQ и объявляет очередь
2. При получении сообщения извлекается JSON
3. Выполняется валидация структуры данных
4. Данные сохраняются в PostgreSQL
5. При успехе отправляется ACK
6. При ошибке отправляется NACK с возвратом в очередь
7. Реализована логика повторных попыток

## Обработка ошибок

- Невалидный JSON: отклонение без возврата в очередь
- Ошибка валидации: отклонение без возврата в очередь
- Ошибка БД: NACK с возвратом в очередь для повторной попытки
- Потеря соединения: автоматическое переподключение

## Разработка

### Локальный запуск без Docker

```bash
# Создание виртуального окружения
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# или .venv\Scripts\activate  # Windows

# Установка зависимостей
pip install -r app/requirements.txt

# Настройка окружения
export RABBITMQ_HOST=localhost
export POSTGRES_HOST=localhost
# ... остальные переменные

# Запуск
python app/src/main.py
```

### Добавление зависимостей

1. Добавить в `app/requirements.txt`
2. Пересобрать: `docker-compose up -d --build app`

## Тестирование

```bash
# Отправка тестового сообщения
docker-compose exec app python tests/send_test_message.py

# Проверка обработки
docker-compose logs app --tail 50

# Проверка БД
docker-compose exec postgres psql -U postgres -d messages_db -c \
"SELECT COUNT(*) FROM messages;"
```

## Устранение неполадок

### Проблемы с подключением

```bash
# Проверка статуса сервисов
docker-compose ps

# Просмотр логов
docker-compose logs rabbitmq
docker-compose logs postgres

# Перезапуск сервисов
docker-compose restart
```

### Проверка очереди

```bash
# Список очередей
docker-compose exec rabbitmq rabbitmqctl list_queues

# Очистка очереди
docker-compose exec rabbitmq rabbitmqctl purge_queue messages_queue
```

### Сброс БД

```bash
# Удаление и пересоздание таблицы
docker-compose exec postgres psql -U postgres -d messages_db -c \
"DROP TABLE IF EXISTS messages;"
# Таблица будет создана автоматически при перезапуске
docker-compose restart app
```

