import os
import uuid
import re
import time
from weaviate import WeaviateClient
from weaviate.connect import ConnectionParams
from weaviate.exceptions import WeaviateGRPCUnavailableError, WeaviateClosedClientError
from weaviate.classes.config import Property, DataType, Configure
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer, util

# Загрузка модели
print("[LOG] Загрузка модели SentenceTransformer 'all-MiniLM-L6-v2'...")
start_time = time.time()
MODEL = SentenceTransformer('all-MiniLM-L6-v2')
print(f"[LOG] Модель загружена за {time.time() - start_time:.2f} секунд.")

pdf_folder = "uploads"

# Проверка наличия папки uploads
if not os.path.exists(pdf_folder):
    print(f"[ERROR] Папка '{pdf_folder}' не существует. Создайте её и добавьте PDF файлы.")
else:
    print(f"[LOG] Папка '{pdf_folder}' найдена, файлов: {len(os.listdir(pdf_folder))}")

# Определение функций
def remove_uuid_prefix(filename: str) -> str:
    if len(filename) > 37 and filename[36] == '-':
        possible_uuid = filename[:36]
        try:
            uuid.UUID(possible_uuid)
            return filename[37:]
        except ValueError:
            return filename
    return filename

def parse_filename_for_title_author(pdf_filename: str):
    cleaned_name = remove_uuid_prefix(pdf_filename)
    base, ext = os.path.splitext(cleaned_name)
    parts = base.split(' ... ')
    if len(parts) == 2:
        book_title, author = parts
    else:
        book_title, author = base, "Unknown"
    author = author.rstrip('.').strip()
    book_title = book_title.strip()
    return book_title, author

def extract_pages_and_metadata(pdf_path: str):
    pages = []
    metadata = {}
    try:
        print(f"[LOG] Открытие PDF: {pdf_path}")
        reader = PdfReader(pdf_path)
        meta = reader.metadata
        metadata["book_title"] = "Unknown"
        metadata["author"] = "Unknown"
        metadata["edition_code"] = "Unknown"
        if meta.title:
            metadata["book_title"] = meta.title
        if meta.author:
            metadata["author"] = meta.author
        if "/Producer" in meta:
            metadata["edition_code"] = meta["/Producer"]
        for i, page in enumerate(reader.pages):
            page_text = page.extract_text()
            if page_text:
                pages.append({"page_number": i + 1, "text": page_text})
        print(f"[LOG] PDF успешно обработан: {pdf_path} (страниц: {len(pages)})")
    except Exception as e:
        print(f"[ERROR] Ошибка при чтении {pdf_path}: {e}")
    return pages, metadata

def clean_text(text: str) -> str:
    text = text.replace("-\n", "")
    text = text.replace("-\r\n", "")
    text = text.replace("\r\n", "").replace("\n", "")
    text = " ".join(text.split())
    return text

def split_text(text: str, max_length: int = 1000) -> list:
    chunks = []
    while len(text) > max_length:
        split_index = text.rfind(" ", 0, max_length)
        if split_index == -1:
            split_index = max_length
        chunk = text[:split_index].strip()
        chunks.append(chunk)
        text = text[split_index:].strip()
    if text:
        chunks.append(text)
    return chunks

def is_noise_sentence(sent: str) -> bool:
    if len(sent.strip()) < 30:
        return True
    if len(sent.split()) < 3:
        return True
    if re.search(r"\.{3,}", sent):  # много точек подряд
        return True
    return False

def split_text_semantic(text: str, threshold: float = 0.35) -> list:
    sentences = re.split(r'(?<=[.!?])\s+', text)
    if not sentences:
        return [text]

    # Отфильтровываем откровенный мусор
    filtered_sentences = [s for s in sentences if not is_noise_sentence(s)]
    if not filtered_sentences:
        return []

    embeddings = MODEL.encode(filtered_sentences)
    chunks = []
    current_chunk = [filtered_sentences[0]]

    for i in range(1, len(filtered_sentences)):
        prev = filtered_sentences[i-1]
        curr = filtered_sentences[i]

        sim = util.cos_sim(embeddings[i-1], embeddings[i])

        # Если текущее короткое — добавим его потом
        if 30 <= len(curr.strip()) <= 80 and len(curr.split()) <= 10:
            # но только если следующий чанк будет «нормальным»
            if i + 1 < len(filtered_sentences):
                next_sent = filtered_sentences[i + 1]
                if not is_noise_sentence(next_sent):
                    current_chunk.append(curr)
                    continue

        if sim < threshold:
            chunks.append(" ".join(current_chunk))
            current_chunk = [curr]
        else:
            current_chunk.append(curr)

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks

def main():
    # Настройка подключения к Weaviate
    print("[LOG] Настройка подключения к Weaviate...")
    connection_params = ConnectionParams(
        http={"host": "localhost",
              "port": 8080,
              "secure": False,
              "timeout": 2000},
        grpc={"host": "localhost",
              "port": 50051,
              "secure": False,
              "timeout": 2000}
    )

    client = WeaviateClient(connection_params=connection_params)
    client._skip_init_checks = True

    try:
        print("[LOG] Подключение к Weaviate...")
        client.connect()
        print("[LOG] Подключение успешно.")
    except WeaviateGRPCUnavailableError as e:
        print("[WARNING] gRPC health check не пройден, продолжаем работу.", e)
    except Exception as e:
        print("[ERROR] Ошибка подключения:", e)

    # Создание коллекции
    try:
        print("[LOG] Создание коллекции 'Document'...")
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
            vectorizer_config=[
                Configure.NamedVectors.text2vec_ollama(
                    name="text",
                    source_properties=["text"],
                    api_endpoint="http://host.docker.internal:11434",  # If using Docker, use this to contact your local Ollama instance
                    model="nomic-embed-text:latest",  # The model to use, e.g. "nomic-embed-text"
                )
            ],
        )
        print("[LOG] Коллекция 'Document' успешно создана.")
    except Exception as e:
        print("[WARNING] Ошибка создания коллекции (возможно, она уже существует):", e)

    # Получение коллекции
    document_collection = None
    try:
        print("[LOG] Получение коллекции 'Document'...")
        schema_info = client.collections.get("Document")
        if hasattr(schema_info.config, "_name") and schema_info.config._name == "Document":
            document_collection = schema_info
            print("[LOG] Коллекция 'Document' получена. Имя:", schema_info.config._name)
        else:
            print("[ERROR] Имя коллекции не соответствует ожидаемому. Ожидалось 'Document'.")
    except Exception as e:
        print("[ERROR] Ошибка получения схемы:", e)

    # Флаг для выбора семантического разбиения
    use_semantic = True

    # Обработка PDF файлов, если коллекция получена
    if document_collection is not None:
        print("[LOG] Начало обработки PDF файлов из папки:", pdf_folder)
        for filename in os.listdir(pdf_folder):
            if filename.lower().endswith(".pdf"):
                pdf_path = os.path.join(pdf_folder, filename)
                print(f"[LOG] Обработка файла: {pdf_path}")
                pages, meta = extract_pages_and_metadata(pdf_path)
                book_title_from_name, author_from_name = parse_filename_for_title_author(filename)
                meta["book_title"] = book_title_from_name
                meta["author"] = author_from_name

                for page in pages:
                    page_number = page["page_number"]
                    cleaned_text = clean_text(page["text"])
                    if use_semantic:
                        print(f"[LOG] Семантическое разбиение страницы {page_number}...")
                        chunks = split_text_semantic(cleaned_text, threshold=0.35)
                    else:
                        print(f"[LOG] Простое разбиение страницы {page_number}...")
                        chunks = split_text(cleaned_text, max_length=1000)
                    print(f"[LOG] Страница {page_number}: разбито на {len(chunks)} частей")
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
                            uuid_val = document_collection.data.insert(data_object)
                        except WeaviateClosedClientError as e:
                            print(f"[WARNING] Клиент закрыт при добавлении '{data_object['filename']}', переподключаемся...", e)
                            client._skip_init_checks = True
                            client.connect()
                            uuid_val = document_collection.data.insert(data_object)
                            print(f"[LOG] Документ '{data_object['filename']}' успешно добавлен: {uuid_val}")
                        except Exception as e:
                            print(f"[ERROR] Ошибка при добавлении документа '{data_object['filename']}':", e)
    else:
        print("[ERROR] Коллекция 'Document' недоступна, объекты не добавлены.")

    print("[LOG] Закрытие подключения к Weaviate...")
    client.close()
    print("=== Завершение работы скрипта load_book.py ===")

if __name__ == '__main__':
    main()
