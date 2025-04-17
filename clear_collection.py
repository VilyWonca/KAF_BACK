import weaviate

client = weaviate.connect_to_local()

# Удаляем коллекцию "Document"
try:
    client.collections.delete("Document")
    print("Коллекция 'Document' успешно удалена.")
except Exception as e:
    print("Ошибка при удалении коллекции:", e)

client.close()
