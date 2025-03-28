import httpx
import logging
from typing import List, Dict, Optional
import json

logger = logging.getLogger(__name__)

Document = Dict[str, any]

async def ask_question(
    user_query: str,
    documents: List[Document],
    sio,
    socket_id: Optional[str] = None
) -> str:
    # Формирование prompt на основе документов
    if documents:
        context_parts = []
        for doc in documents:
            props = doc.get("properties", {}) if isinstance(doc, dict) else getattr(doc, "properties", {})
            title = props.get("book_title")
            author = props.get("author")
            page = props.get("page_number", "")
            try:
                page_num = int(page) if page != "" else 1
            except ValueError:
                page_num = 1
            text = props.get("text", "")
            context_parts.append(
                f'Автор: {author} Название книги: "{title}" страница {page_num}\nОтрывок из этой страницы: {text}'
            )
        context = "\n\n".join(context_parts)
        prompt = (
            f"Сейчас я тебе предоставлю отрывки из книг так или иначе отвечающих на мой вопрос."
            f"Вот отрывки из книг:\n{context}\n\n"
            f"Твоя задача выбрать самые релевантные отрывки и, используя только эти их ответь мне мой вопрос: {user_query}. Также тебе нельзя использовать другую литературу, которой нет в представленных отрвыках "
            f"В ответе обязательно используй цитаты из подходящих фрагментов, также используй markdown-разметку в своем ответе."
            f"Пиши только на русском языке."
            f"В конце своего ответа обязательно укажи автора книги, название книги и страницы отрывков, которые ты использовал для ответа.\n"
            f"Если ты не находишь релевантную информацию для ответа, сообщи об этом пользователю\n\n"
        )
    else:
        prompt = (
            f"Я не смог найти информацию в достоверных источниках, но вот что я об этом думаю:\n\n"
            f"Вопрос: {user_query}\n\nОтвет:"
        )

    logger.info(f"Сформированный prompt:\n{prompt}")
    full_response = ""

    try:
        # Устанавливаем таймаут в 60 секунд на случай медленной обработки
        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
            async with client.stream(
                "POST",
                "http://localhost:11434/api/chat",
                json={
                    "model": "mistral-nemo:latest",
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": True
                }
            ) as resp:
                async for chunk in resp.aiter_text():
                    for line in chunk.splitlines():
                        if not line.strip():
                            continue
                        try:
                            data = json.loads(line)
                        except json.JSONDecodeError as e:
                            logger.error(f"Ошибка разбора JSON: {e}. Строка: {line}")
                            continue

                        content = data.get("message", {}).get("content", "")
                        full_response += content

                        if socket_id:
                            try:
                                await sio.emit("partial answer", {"text": full_response}, to=socket_id)
                            except Exception as sio_e:
                                logger.error(f"Ошибка при отправке через Socket.IO: {sio_e}")
        return full_response
    except Exception as e:
        logger.error(f"Ошибка при генерации ответа: {e}")
        # Отправляем сообщение об ошибке клиенту, если socket_id указан
        if socket_id:
            try:
                await sio.emit("chat message", {"text": "⚠️ Ошибка при генерации ответа."}, to=socket_id)
            except Exception as sio_e:
                logger.error(f"Ошибка при отправке сообщения об ошибке через Socket.IO: {sio_e}")
        raise
