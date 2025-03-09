from weaviate import WeaviateClient
from weaviate.connect import ConnectionParams

# Настройка подключения к Weaviate
connection_params = ConnectionParams(
    http={
        "host": "localhost",
        "port": 8080,
        "secure": False,
        "timeout": 2000  # таймаут в секундах
    },
    grpc={
        "host": "localhost",
        "port": 8086,
        "secure": False,
        "timeout": 2000
    }
)

client = WeaviateClient(connection_params=connection_params)
client._skip_init_checks = True  # Используйте с осторожностью

# Подключаем клиента
try:
    client.connect()
    print("Соединение установлено.")
except Exception as e:
    print("Ошибка подключения:", e)
    exit(1)

# Удаляем коллекцию "Document"
try:
    client.collections.delete("Document")
    print("Коллекция 'Document' успешно удалена.")
except Exception as e:
    print("Ошибка при удалении коллекции:", e)

client.close()
