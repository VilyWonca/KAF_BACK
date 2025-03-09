# weaviate_client.py
import weaviate
import logging

logger = logging.getLogger(__name__)

_client = None

def connect_to_weaviate():
    global _client
    if _client is None:
        # Подставьте URL и при необходимости заголовки
        _client = weaviate.Client(
            url="http://localhost:8090"
        )
        # Если нужно проверить готовность:
        # if not _client.is_ready():
        #     raise Exception("Weaviate is not ready")

        logger.info("✅ Weaviate client connected successfully")

    return _client

def close_weaviate():
    global _client
    if _client is not None:
        # В Python-клиенте нет метода close(),
        # поэтому просто «забываем» клиент
        logger.info("🔌 Weaviate connection closed")
        _client = None
