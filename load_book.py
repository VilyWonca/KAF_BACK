import os
from weaviate import WeaviateClient
from weaviate.connect import ConnectionParams
from weaviate.exceptions import WeaviateGRPCUnavailableError, WeaviateClosedClientError
from weaviate.classes.config import Property, DataType
from pypdf import PdfReader

pdf_folder = "books"


def extract_pages_and_metadata(pdf_path: str):
    pages = []
    metadata = {}
    try:
        reader = PdfReader(pdf_path)
        # Извлекаем метаданные, если они есть
        meta = reader.metadata
        metadata["book_title"] = meta.title if meta.title else os.path.basename(pdf_path)
        metadata["author"] = meta.author if meta.author else "Unknown"
        metadata["edition_code"] = meta.get("/Producer", "Unknown")

        for i, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text:
                pages.append({"page_number": i + 1, "text": page_text})
    except Exception as e:
        print(f"Ошибка при чтении {pdf_path}: {e}")
    return pages, metadata


def split_text(text: str, max_length: int = 1000) -> list:
    chunks = []
    while len(text) > max_length:
        split_index = text.rfind("\n", 0, max_length)
        if split_index == -1:
            split_index = max_length
        chunk = text[:split_index].strip()
        chunks.append(chunk)
        text = text[split_index:].strip()
    if text:
        chunks.append(text)
    return chunks


# Настройка подключения Weaviate
connection_params = ConnectionParams(
    http={"host": "localhost",
          "port": 8080,
          "secure": False,
          "timeout": 2000},
    grpc={"host": "localhost",
          "port": 8086,
          "secure": False,
          "timeout": 2000}
)

client = WeaviateClient(connection_params=connection_params)
client._skip_init_checks = True

try:
    client.connect()
except WeaviateGRPCUnavailableError as e:
    print("Предупреждение: gRPC health check не пройден, продолжаем работу.", e)
except Exception as e:
    print("Ошибка подключения:", e)

# Создаем коллекцию "Document" с дополнительными свойствами
try:
    client.collections.create(
        "Document",
        properties=[
            Property(name="text", data_type=DataType.TEXT),
            Property(name="filename", data_type=DataType.TEXT),
            Property(name="book_title", data_type=DataType.TEXT),
            Property(name="page_number", data_type=DataType.INT),
            Property(name="edition_code", data_type=DataType.TEXT),
            Property(name="author", data_type=DataType.TEXT)
        ],
        vectorizer="mediumnew-t2v-transformers-1",  # убедитесь, что это корректное имя модуля
        vectorizer_config={"host": "t2v-transformers", "port": 8080}
    )
    print("Коллекция 'Document' успешно создана.")
except Exception as e:
    print("Ошибка создания коллекции (возможно, она уже существует):", e)

# Получаем коллекцию "Document" через схему
document_collection = None
try:
    schema_info = client.collections.get("Document")
    if hasattr(schema_info.config, "_name") and schema_info.config._name == "Document":
        document_collection = schema_info
        print("Коллекция 'Document' получена. Имя:", schema_info.config._name)
    else:
        print("Имя коллекции не соответствует ожидаемому. Ожидалось 'Document'.")
except Exception as e:
    print("Ошибка получения схемы:", e)

# Если коллекция получена, обрабатываем PDF-файлы и вставляем объекты с метаданными
if document_collection is not None:
    for filename in os.listdir(pdf_folder):
        if filename.lower().endswith(".pdf"):
            pdf_path = os.path.join(pdf_folder, filename)
            print(f"Обработка файла: {pdf_path}")
            pages, meta = extract_pages_and_metadata(pdf_path)
            for page in pages:
                page_number = page["page_number"]
                # Разбиваем текст страницы на чанки
                chunks = split_text(page["text"], max_length=1000)
                print(f"Страница {page_number}: разбито на {len(chunks)} частей")
                for i, chunk in enumerate(chunks):
                    data_object = {
                        "text": chunk,
                        "filename": f"{filename}_page_{page_number}_part_{i + 1}",
                        "book_title": meta.get("book_title", "Unknown"),
                        "page_number": page_number,
                        "edition_code": meta.get("edition_code", "Unknown"),
                        "author": meta.get("author", "Unknown")
                    }
                    try:
                        uuid = document_collection.data.insert(data_object)
                        print(f"Документ '{data_object['filename']}' успешно добавлен: {uuid}")
                    except WeaviateClosedClientError as e:
                        print(f"Клиент закрыт при добавлении '{data_object['filename']}', переподключаемся...", e)
                        client._skip_init_checks = True
                        client.connect()
                        uuid = document_collection.data.insert(data_object)
                        print(f"Документ '{data_object['filename']}' успешно добавлен: {uuid}")
                    except Exception as e:
                        print(f"Ошибка при добавлении документа '{data_object['filename']}':", e)
else:
    print("Коллекция 'Document' недоступна, объекты не добавлены.")

client.close()
