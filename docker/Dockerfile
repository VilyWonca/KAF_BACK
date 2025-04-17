FROM python:3.9-slim-buster

WORKDIR /app

# Копируем список зависимостей и устанавливаем их
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . /app/

EXPOSE 8000

# Запуск сервера (можете заменить на команду для запуска через uvicorn)
CMD ["python", "app/main.py"]
