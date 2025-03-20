import asyncio
import logging
from socketio import AsyncServer
from wv_queries import search_by_similarity, search_by_keyword, search_hybrid
from ollama_client import ask_question

# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Создаём экземпляр Socket.IO сервера с поддержкой CORS и логированием
sio = AsyncServer(async_mode="asgi", cors_allowed_origins="*", logger=True, engineio_logger=True)

# Подключение WebSocket
@sio.event
async def connect(sid, environ):
    logger.info(f"🔌 Socket подключён: {sid}")
    await sio.emit("system message", {"text": "🔌 Успешное подключение!"}, room=sid)

# Отключение WebSocket
@sio.event
async def disconnect(sid):
    logger.info(f"❌ Socket отключён: {sid}")

# Глобальный обработчик всех событий для отладки
@sio.on("*")
async def catch_all(event, sid, data):
    logger.info(f"🔥 WebSocket-событие: {event}, sid={sid}, data={data}")


# Обработчик сообщений
@sio.on("chat message")
async def chat_message(sid, data):
    try:
        logger.info(f"📥 Получено сообщение от {sid}: {data}")
        print(f"🔥 Получено сообщение: {data}")

        text = data.get("text")
        search_type = data.get("searchType")

        logger.info(f"🔍 Начинаем обработку: текст='{text}', поиск={search_type}")
        print(f"🔍 Начинаем обработку: текст='{text}', поиск={search_type}")

        # Отправляем промежуточное сообщение клиенту
        print("🚀 Отправляем 'loading answer'...")
        await sio.emit("loading answer", {"text": "Ищу похожую информацию..."}, room=sid)
        # await asyncio.sleep(.1)

        # 📌 Выполняем поиск
        results = []
        if search_type == "1":
            print("🔍 Запускаем гибридный поиск...")
            results = search_hybrid(text)
            print(f"🔍 Найдено документов: {len(results)}")
        elif search_type == "2":
            print("🔍 Запускаем поиск по схожести...")
            results = search_by_similarity(text)
            print(f"🔍 Найдено документов: {len(results)}")
        elif search_type == "3":
            print("🔍 Запускаем поиск по ключевым словам...")
            results = search_by_keyword(text)
            print(f"🔍 Найдено документов: {len(results)}")
        else:
            print("⚠️ Неизвестный тип поиска!")
            await sio.emit("chat message", "⚠️ Ошибка: неизвестный тип поиска.", room=sid)
            return

        if results:
            print(f"✅ Найдено {len(results)} документов. Передаём в Ollama...")
        else:
            print("⚠️ Weaviate не нашёл совпадений.")
            await sio.emit("chat message", "⚠️ Weaviate не нашёл совпадений.", room=sid)
            return  # Останавливаем выполнение

        print("🚀 Отправляем 'loading answer'...")
        await sio.emit("loading answer", {"text": "Генерирую ответ..."}, room=sid)
        # await asyncio.sleep(.2)

        # 📌 Генерация ответа через Ollama
        try:
            print("🧠 Передаём данные в Ollama...")
            llm_answer = await ask_question(text, results, sio, sid)
            print(f"✅ Ollama ответил: {llm_answer[:100]}...")
        except Exception as e:
            print(f"❌ Ошибка в Ollama: {e}")
            llm_answer = "⚠️ Ошибка при генерации ответа."

        # 📌 Отправляем ответ клиенту
        print(f"📤 Отправка ответа в чат: {llm_answer[:100]}...")
        await sio.emit("chat message", llm_answer, room=sid)

    except Exception as e:
        print(f"❌ Ошибка в обработке chat_message: {e}")
        await sio.emit("chat message", "⚠️ Внутренняя ошибка сервера.", room=sid)
