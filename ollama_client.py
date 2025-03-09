# ollama_client.py
import httpx
import logging
from typing import List, Dict, Optional
import json

logger = logging.getLogger(__name__)

# Определяем Document как словарь
Document = Dict[str, any]

async def ask_question(
    user_query: str,
    documents: List[Document],
    sio,            # Экземпляр socket.io (AsyncServer)
    socket_id: Optional[str] = None
) -> str:
    if documents:
        context_parts = []
        for doc in documents:
            # Если doc – словарь, берем ключ "properties", иначе пытаемся получить атрибут properties
            if isinstance(doc, dict):
                props = doc.get("properties", {})
            else:
                props = getattr(doc, "properties", {})
            title = props.get("book_title")
            page = props['page_number'] if "page_number" in props else ""
            text = props.get("text", "")
            context_parts.append(f'Название книги: "{title}" страница {(int(page) - 1)}\nОтрывок из этой страницы: {text}')
        context = "\n\n".join(context_parts)
        prompt = (
            f"Сейчас я тебе предоставлю отрывки из книг так или иначе отвечающих на мой вопрос"
            f"Вот отрывки из книг:\n{context}\n\n"
            f"Используя только эти отрывки ответь мне мой вопрос: {user_query}. В ответе обязательно используй цитаты из подходящих фрагментов."
            f"В конце своего ответа обязательно укажи автора книги, название книги и страницу.\n\n"
        )
    else:
        prompt = (
            f"Я не смог найти информацию в достоверных источниках, но вот что я об этом думаю:\n\n"
            f"Вопрос: {user_query}\n\nОтвет:"
        )

    # Выводим сформированный prompt для отладки
    logger.info(f"Сформированный prompt:\n{prompt}")

    full_response = ""

    try:
        async with httpx.AsyncClient() as client:
            async with client.stream(
                    "POST",
                    "http://localhost:11434/api/chat",
                    json={
                        "model": "owl/t-lite",
                        "messages": [{"role": "user", "content": prompt}],
                        "stream": True
                    }
            ) as resp:
                async for chunk in resp.aiter_text():
                    # Если в чанке может быть несколько JSON-объектов, разделённых переводом строки:
                    for line in chunk.splitlines():
                        if not line.strip():
                            continue
                        try:
                            data = json.loads(line)
                            # Извлекаем значение поля content из объекта message
                            content = data.get("message", {}).get("content", "")
                            full_response += content
                            # event_data = {"text": full_response}
                            # if socket_id:
                            #     await sio.emit("partial answer", event_data, room=socket_id)
                            # else:
                            #     await sio.emit("partial answer", event_data)
                        except json.JSONDecodeError as e:
                            logger.error(f"Ошибка разбора JSON: {e}")
        return full_response
    except Exception as e:
        logger.error(f"Ошибка при генерации ответа: {e}")
        raise


    # curl -X POST http://localhost:11434/api/generate -H "Content-Type: application/json" -d "{\"model\":\"owl/t-lite:latest\", \"prompt\":\"Why is the sky blue?\"}"