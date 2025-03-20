import os
import sys
import shutil
import subprocess
from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse
from typing import List

router = APIRouter()

UPLOAD_DIR = "uploads"
BOOKS_DIR = "books"

@router.post("/uploads")
async def upload_files(files: List[UploadFile] = File(...)):
    try:
        # Создаем необходимые директории, если их нет
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        os.makedirs(BOOKS_DIR, exist_ok=True)

        # 1. Сохраняем все загруженные файлы в папку uploads
        for file in files:
            upload_path = os.path.join(UPLOAD_DIR, file.filename)
            with open(upload_path, "wb") as buffer:
                buffer.write(await file.read())

        # 2. Запускаем скрипт load_book.py, который векторизует все файлы из uploads
        #    Используем sys.executable, чтобы гарантированно вызвать Python из текущего окружения
        script_path = os.path.join(os.path.dirname(__file__), "load_book.py")
        subprocess.run([sys.executable, script_path], check=True)

        # 3. Переносим все файлы из uploads в books, оставляя uploads пустой
        for filename in os.listdir(UPLOAD_DIR):
            src_path = os.path.join(UPLOAD_DIR, filename)
            dst_path = os.path.join(BOOKS_DIR, filename)
            shutil.move(src_path, dst_path)

        return JSONResponse(status_code=200, content={"status": "ok"})

    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})
