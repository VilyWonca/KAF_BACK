import logger.logger_config as logger_config
import logging

# Устанавливаем уровень логирования для указанных логгеров
for logger_name in (
    "socketio",
    "socketio.server",
    "engineio",
    "engineio.server",
    "uvicorn",
    "uvicorn.error",
    "uvicorn.access",
):
    logging.getLogger(logger_name).setLevel(logging.ERROR)

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from socket_manager import sio
from socketio import ASGIApp

# Импортируем router из client_load_book
from load_book.client_load_book import router as upload_router

# Инициализация FastAPI
app = FastAPI()

# Разрешаем CORS для всех источников
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # Разрешены запросы с любых источников
    allow_credentials=True,
    allow_methods=["*"],        # Разрешаем все HTTP-методы
    allow_headers=["*"],        # Разрешаем все заголовки
)

# Интеграция с Socket.IO
socket_app = ASGIApp(sio, other_asgi_app=app)

# Подключаем router для загрузки файлов с префиксом /api
app.include_router(upload_router, prefix="/api")

# Создаем логгер
logger = logging.getLogger(__name__)
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
