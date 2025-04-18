import weaviate

client = weaviate.connect_to_local()

collection = client.collections.get("Document")

with open("chunks.txt", "w", encoding="utf-8") as f:
    for item in collection.iterator():
        text = item.properties.get("text", "")
        if text:
            f.write(text.strip() + "\n\n")  # два энтера между чанками

print("✅ Все тексты успешно сохранены в chunks.txt")


client.close()