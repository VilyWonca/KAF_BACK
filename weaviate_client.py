# weaviate_client.py
import weaviate
import logging

logger = logging.getLogger(__name__)

_client = None

def connect_to_weaviate():
    global _client
    if _client is None:
        _client = weaviate.Client(
            url="http://localhost:8090"
        )

        logger.info("✅ Weaviate client connected successfully")

    return _client

def close_weaviate():
    global _client
    if _client is not None:
        logger.info("🔌 Weaviate connection closed")
        _client = None
