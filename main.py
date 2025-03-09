import logging
import uvicorn
from fastapi import FastAPI
from socket_manager import sio
from socketio import ASGIApp

# Инициализация FastAPI и интеграция WebSocket
app = FastAPI()
socket_app = ASGIApp(sio, other_asgi_app=app)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Логирование запуска сервера
logger.info("🚀 Сервер FastAPI + Socket.IO запущен...")


# Простая REST точка входа
@app.get("/")
def read_root():
    logger.info("📥 Запрос на корневой эндпоинт `/`")
    return {"message": "Hello from FastAPI + Socket.IO"}


# Функция запуска сервера
def start():
    try:
        logger.info("🚀 Запускаем сервер на 0.0.0.0:5041...")
        uvicorn.run(socket_app, host="0.0.0.0", port=5041)
    except Exception as e:
        logger.error(f"❌ Ошибка запуска сервера: {e}")


if __name__ == "__main__":
    start()
