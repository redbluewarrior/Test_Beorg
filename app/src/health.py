import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
from db import db_manager
from rabbitmq import rabbitmq_manager
import logging

logger = logging.getLogger(__name__)


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self._handle_health()
        else:
            self._handle_not_found()

    def _handle_health(self):
        db_healthy = db_manager.health_check()
        rabbitmq_healthy = rabbitmq_manager.health_check()

        status = {
            "status": "healthy" if (db_healthy and rabbitmq_healthy) else "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "database": "up" if db_healthy else "down",
                "rabbitmq": "up" if rabbitmq_healthy else "down"
            }
        }

        self.send_response(200 if status["status"] == "healthy" else 503)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(status).encode('utf-8'))

    def _handle_not_found(self):

        self.send_response(404)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"error": "Not found"}).encode('utf-8'))

    def log_message(self, format, *args):
        logger.debug(f"Health endpoint: {format % args}")


def run_health_server(port=8080):
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    logger.info(f"Health check server running on port {port}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Health server shutting down...")
        server.shutdown()