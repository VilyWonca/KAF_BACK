import logging
import weaviate
from weaviate.classes.query import MetadataQuery

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
                {"name": "title", "dataType": "text"},
                {"name": "author", "dataType": "text"},
                {"name": "text", "dataType": "text"},
                {"name": "page", "dataType": "int"},
                {"name": "published_year", "dataType": "int"},
                {"name": "language", "dataType": "text"},
            ],
            vector_index_config={
                "vectorizer": "text2vec-transformers"  # Исправленный способ
            }
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

# Тестовая функция для добавления документа
def test_add_document():
    test_document = {
        "title": "Sample Book Title",
        "author": "Author Name",
        "text": "Это пример отрывка из книги, который будет векторизован с помощью text2vec-transformers.",
        "page": 10,
        "published_year": 2025,
        "language": "en"
    }
    add_document(test_document)

def search_by_similarity(query_text: str):
    client = get_client()
    try:
        collection = client.collections.get(CLASS_NAME)
        response = collection.query.near_text(
            query=query_text,
            return_metadata=MetadataQuery(distance=True),
            distance=0.3
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


def search_hybrid(query_text: str, alpha: float = 0.9):
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



# Точка входа в программу
if __name__ == "__main__":
    create_collection()       # Создаём коллекцию (если нет)
    test_add_document()       # Добавляем тестовый документ
