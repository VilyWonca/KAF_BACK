import os
from weaviate import WeaviateClient
from weaviate.connect import ConnectionParams
from weaviate.exceptions import WeaviateGRPCUnavailableError, WeaviateClosedClientError
from weaviate.classes.config import Property, DataType, Configure
from pypdf import PdfReader
import weaviate

# Папка с PDF-файлами
pdf_folder = "books"

def extract_text_pages(pdf_path: str) -> list:
    """
    Извлекает текст из PDF-файла постранично.
    Возвращает список кортежей (page_number, page_text).
    """
    pages = []
    try:
        reader = PdfReader(pdf_path)
        for i, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text()
            if page_text:
                pages.append((i, page_text))
    except Exception as e:
        print(f"Ошибка при чтении {pdf_path}: {e}")
    return pages

def split_text(text: str, max_length: int = 1000) -> list:
    """
    Разбивает текст на чанки длиной не более max_length символов.
    Старается разбить по последнему переносу строки в пределах max_length.
    """
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

def parse_filename_for_book_and_author(filename: str) -> tuple:
    """
    Ожидается, что имя файла имеет вид:
        'Название книги ... Автор.pdf'
    Функция возвращает кортеж (title__book, author).

    Если формат не совпадает, в качестве автора возвращается пустая строка,
    а в качестве названия — имя файла без расширения.
    """
    filename_no_ext = os.path.splitext(filename)[0]  # убираем расширение
    parts = filename_no_ext.split("...")
    if len(parts) == 2:
        book_title = parts[0].strip()
        book_author = parts[1].strip()
    else:
        book_title = filename_no_ext
        book_author = ""
    return book_title, book_author


# Инициализируем клиента Weaviate
client = weaviate.connect_to_local()
client._skip_init_checks = True  # Отключаем стартовые проверки (использовать с осторожностью)

# Подключаем клиента. Если gRPC health check не проходит, выводим предупреждение и продолжаем работу.
try:
    client.connect()
except WeaviateGRPCUnavailableError as e:
    print("Предупреждение: gRPC health check не пройден, продолжаем работу.", e)
except Exception as e:
    print("Ошибка подключения:", e)

# Создаём коллекцию "Document" с полями: text, filename, title__book, author, page_number
try:
    client.collections.create(
        "Document",
        properties=[
            Property(name="text", data_type=DataType.TEXT),
            Property(name="filename", data_type=DataType.TEXT),
            Property(name="title__book", data_type=DataType.TEXT),
            Property(name="author", data_type=DataType.TEXT),
            Property(name="page_number", data_type=DataType.INT)
        ],
        vectorizer_config=[
                Configure.NamedVectors.text2vec_ollama(
                    name="text",
                    source_properties=["text"],
                    api_endpoint="http://host.docker.internal:11434",  # If using Docker, use this to contact your local Ollama instance
                    model="nomic-embed-text:latest",  # The model to use, e.g. "nomic-embed-text"
                )
            ]
    )
    print("Коллекция 'Document' успешно создана.")
except Exception as e:
    print("Ошибка создания коллекции (возможно, она уже существует):", e)

# Получаем коллекцию "Document" через схему
document_collection = None
try:
    schema_info = client.collections.get("Document")
    print("Тип schema_info:", type(schema_info))
    print("schema_info:", schema_info)

    if hasattr(schema_info.config, "_name") and schema_info.config._name == "Document":
        document_collection = schema_info
        print("Коллекция 'Document' получена. Имя:", schema_info.config._name)
    else:
        print("Имя коллекции не соответствует ожидаемому. Ожидалось 'Document'.")
except Exception as e:
    print("Ошибка получения схемы:", e)

# Если коллекция получена, обрабатываем PDF-файлы и вставляем объекты по частям.
if document_collection is not None:
    for filename in os.listdir(pdf_folder):
        if filename.lower().endswith(".pdf"):
            pdf_path = os.path.join(pdf_folder, filename)
            print(f"Обработка файла: {pdf_path}")

            # Получаем название книги и автора из имени файла
            book_title, book_author = parse_filename_for_book_and_author(filename)

            # Извлекаем текст из PDF постранично
            pages = extract_text_pages(pdf_path)
            if pages:
                for page_num, page_text in pages:
                    # Разбиваем текст страницы на чанки
                    chunks = split_text(page_text, max_length=1000)
                    print(f"Страница {page_num}: разбито на {len(chunks)} частей")
                    # Вставляем каждый чанк в Weaviate
                    for i, chunk in enumerate(chunks):
                        data_object = {
                            "text": chunk,
                            "filename": f"{filename}_page_{page_num}_part_{i+1}",
                            "title__book": book_title,
                            "author": book_author,
                            "page_number": page_num
                        }
                        try:
                            uuid = document_collection.data.insert(data_object)
                            print(f"Документ '{filename}_page_{page_num}_part_{i+1}' успешно добавлен в Weaviate: {uuid}")
                        except WeaviateClosedClientError as e:
                            print(f"Клиент закрыт при добавлении '{filename}_page_{page_num}_part_{i+1}', переподключаемся...", e)
                            client._skip_init_checks = True
                            client.connect()
                            uuid = document_collection.data.insert(data_object)
                            print(f"Документ '{filename}_page_{page_num}_part_{i+1}' успешно добавлен в Weaviate: {uuid}")
                        except Exception as e:
                            print(f"Ошибка при добавлении документа '{filename}_page_{page_num}_part_{i+1}':", e)
            else:
                print(f"Не удалось извлечь текст из файла {filename}")
else:
    print("Коллекция 'Document' недоступна, объекты не добавлены.")

# Закрываем соединение
client.close()
