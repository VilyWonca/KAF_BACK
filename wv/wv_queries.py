import logging
import weaviate
from weaviate.classes.query import MetadataQuery
from weaviate.classes.config import Configure

# Настройки логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# URL Weaviate
WEAVIATE_URL = "http://localhost:8080"
CLASS_NAME = "Document"

# Функция создания клиента Weaviate
def get_client():
    return weaviate.connect_to_local(skip_init_checks=True)

# Функция для создания коллекции (если её нет)
def create_collection():
    client = get_client()
    try:
        existing_collections = client.collections.list_all()
        if CLASS_NAME in existing_collections:
            logger.info(f"📚 Коллекция {CLASS_NAME} уже существует.")
            return

        client.collections.create(
            name=CLASS_NAME,
            description="Collection for storing book excerpts with semantic search",
            properties=[
                {"name": "author", "dataType": "text"},
                {"name": "title", "dataType": "text"},
                {"name": "page", "dataType": "int"},
                {"name": "published_year", "dataType": "int"},
                {"name": "text", "dataType": "text"},
                {"name": "language", "dataType": "text"},
            ],
            vectorizer_config=[
                Configure.NamedVectors.text2vec_ollama(
                    name="text_vector",
                    source_properties=["text"],
                    api_endpoint="http://host.docker.internal:11434",  # If using Docker, use this to contact your local Ollama instance
                    model="nomic-embed-text:latest",  # The model to use, e.g. "nomic-embed-text"
                )
            ]
        )
        logger.info(f"✅ Коллекция {CLASS_NAME} успешно создана.")
    except Exception as e:
        logger.error(f"❌ Ошибка при создании коллекции: {e}")
    finally:
        client.close()  # Закрываем соединение

# Функция добавления документа
def add_document(document: dict):
    client = get_client()
    try:
        collection = client.collections.get(CLASS_NAME)
        collection.data.insert(document)
        logger.info("✅ Документ успешно добавлен.")
    except Exception as e:
        logger.error(f"❌ Ошибка при добавлении документа: {e}")
    finally:
        client.close()  # Закрываем соединение

def search_by_similarity(query_text: str):
    client = get_client()
    try:
        collection = client.collections.get(CLASS_NAME)
        response = collection.query.near_text(
            query=query_text,
            return_metadata=MetadataQuery(distance=True),
            distance=0.6
        )
        for o in response.objects:
            print(o.metadata.distance)
        return response.objects
    except Exception as e:
        logger.error(f"❌ Ошибка при семантическом поиске: {e}")
        return []

def search_by_keyword(query_text: str, limit: int = 6) -> list:
    client = get_client()
    try:
        collection = client.collections.get(CLASS_NAME)
        response = collection.query.bm25(
            query=query_text,
            limit=limit,
            return_metadata=MetadataQuery(score=True),
        )
        for o in response.objects:
            print(o.metadata.score)
        return response.objects
    except Exception as e:
        logger.error(f"❌ Ошибка при поиске по ключевым словам: {e}")
        return []


def search_hybrid(query_text: str, alpha: float = 0.7):
    client = get_client()
    try:
        collection = client.collections.get(CLASS_NAME)
        response = collection.query.hybrid(
            query=query_text,
            alpha=alpha,
            limit = 10,
            return_metadata=MetadataQuery(score=True, explain_score=True)
        )
        for o in response.objects:
            print(o.metadata.score, o.metadata.explain_score)
        return response.objects
    except Exception as e:
        logger.error(f"❌ Ошибка при гибридном поиске: {e}")
        return []


if __name__ == "__main__":
    create_collection()       # Создаём коллекцию (если нет)
