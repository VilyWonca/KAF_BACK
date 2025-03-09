import os
from weaviate import WeaviateClient
from weaviate.connect import ConnectionParams
from weaviate.exceptions import WeaviateGRPCUnavailableError, WeaviateClosedClientError
from weaviate.classes.config import Property, DataType
from pypdf import PdfReader

# Папка с PDF-файлами
pdf_folder = "books"

def extract_text_from_pdf(pdf_path: str) -> str:
    text = ""
    try:
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    except Exception as e:
        print(f"Ошибка при чтении {pdf_path}: {e}")
    return text

def split_text(text: str, max_length: int = 1000) -> list:
    """
    Разбивает текст на чанки длиной не более max_length символов.
    Пытается разбить по последнему переносу строки в пределах max_length.
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

# Устанавливаем параметры подключения: HTTP на localhost:8080, gRPC на localhost:8086
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

# Инициализируем клиента Weaviate
client = WeaviateClient(connection_params=connection_params)
client._skip_init_checks = True  # Отключаем стартовые проверки (использовать с осторожностью)

# Подключаем клиента. Если gRPC health check не проходит, выводим предупреждение и продолжаем работу.
try:
    client.connect()
except WeaviateGRPCUnavailableError as e:
    print("Предупреждение: gRPC health check не пройден, продолжаем работу.", e)
except Exception as e:
    print("Ошибка подключения:", e)

# Создаем коллекцию "Document" с указанными свойствами.
# Важно: внутри Docker мы должны обращаться к трансформеру по имени "t2v-transformers", а не "localhost".
try:
    client.collections.create(
        "Document",
        properties=[
            Property(name="text", data_type=DataType.TEXT),
            Property(name="filename", data_type=DataType.TEXT)
        ],
        vectorizer="mediumnew-t2v-transformers-1",  # Проверьте, что это корректное имя модуля
        vectorizer_config={"host": "t2v-transformers", "port": 8080}
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
            pdf_text = extract_text_from_pdf(pdf_path)
            if pdf_text:
                # Разбиваем текст на чанки
                chunks = split_text(pdf_text, max_length=1000)
                print(f"Разбито на {len(chunks)} частей")
                for i, chunk in enumerate(chunks):
                    data_object = {
                        "text": chunk,
                        "filename": f"{filename}_part_{i+1}"
                    }
                    try:
                        uuid = document_collection.data.insert(data_object)
                        print(f"Документ '{filename}_part_{i+1}' успешно добавлен в Weaviate: {uuid}")
                    except WeaviateClosedClientError as e:
                        print(f"Клиент закрыт при добавлении '{filename}_part_{i+1}', переподключаемся...", e)
                        client._skip_init_checks = True
                        client.connect()
                        uuid = document_collection.data.insert(data_object)
                        print(f"Документ '{filename}_part_{i+1}' успешно добавлен в Weaviate: {uuid}")
                    except Exception as e:
                        print(f"Ошибка при добавлении документа '{filename}_part_{i+1}':", e)
            else:
                print(f"Не удалось извлечь текст из файла {filename}")
else:
    print("Коллекция 'Document' недоступна, объекты не добавлены.")

# Закрываем соединение
client.close()
