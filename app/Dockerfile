FROM python:3.11-alpine


RUN apk add --no-cache \
    gcc \
    musl-dev \
    postgresql-dev \
    libffi-dev


WORKDIR /app


COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


COPY src/ ./src/


RUN addgroup -g 1001 -S appuser && \
    adduser -u 1001 -S appuser -G appuser
USER appuser


CMD ["python", "-u", "src/consumer.py"]