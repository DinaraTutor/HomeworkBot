import os
import uuid
import time
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Ключи берутся из переменных окружения (задаются на сервере bothost.ru)
TELEGRAM_TOKEN = os.environ.get("BOT_TOKEN")
GIGACHAT_AUTH_KEY = os.environ.get("GIGACHAT_AUTH_KEY")  # тот самый Authorization key

OAUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
API_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"

# Кэш токена, чтобы не запрашивать его на каждое сообщение
_token_cache = {"token": None, "expires_at": 0}

SYSTEM_PROMPT = """Ты — преподаватель английского языка, который проверяет письменные
домашние задания учеников (диалоги или монологи о себе).

Оцени присланный текст по рубрике, каждый критерий от 0 до 5:
- Task Achievement (раскрыта ли тема, соблюдён ли объём)
- Coherence & Cohesion (логика изложения, связки между предложениями)
- Lexical Resource (разнообразие и точность лексики)
- Grammar Range & Accuracy (грамматика)

Формат ответа строго такой:

📊 ОЦЕНКА
Task Achievement: X/5
Coherence & Cohesion: X/5
Lexical Resource: X/5
Grammar: X/5
Итого: X/20

✏️ ЧТО ИСПРАВИТЬ
(список конкретных ошибок с объяснением, коротко)

✅ ИСПРАВЛЕННЫЙ ТЕКСТ
(перепиши текст ученика полностью, без ошибок, сохраняя его смысл и стиль,
это нужно ученику для того, чтобы потом начитать текст вслух)

Пиши по-русски, кроме исправленного текста (он должен остаться на английском).
"""


def get_gigachat_token():
    """Получает токен доступа GigaChat, кэширует его до истечения срока."""
    if _token_cache["token"] and time.time() < _token_cache["expires_at"]:
        return _token_cache["token"]

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
        "RqUID": str(uuid.uuid4()),
        "Authorization": f"Basic {GIGACHAT_AUTH_KEY}",
    }
    data = {"scope": "GIGACHAT_API_PERS"}

    # verify=False используется потому, что GigaChat использует российские
    # сертификаты Минцифры, которые не входят в стандартный список доверенных
    response = requests.post(OAUTH_URL, headers=headers, data=data, verify=False)
    response.raise_for_status()
    result = response.json()

    _token_cache["token"] = result["access_token"]
    _token_cache["expires_at"] = time.time() + 25 * 60  # токен живёт ~30 минут
    return _token_cache["token"]


def ask_gigachat(student_text: str) -> str:
    token = get_gigachat_token()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    payload = {
        "model": "GigaChat",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": student_text},
        ],
        "temperature": 0.3,
    }
    response = requests.post(API_URL, headers=headers, json=payload, verify=False)
    response.raise_for_status()
    result = response.json()
    return result["choices"][0]["message"]["content"]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Пришли мне текст своего домашнего задания (диалог или "
        "монолог о себе на английском) — я проверю его и пришлю оценку "
        "с исправлениями."
    )


async def check_homework(update: Update, context: ContextTypes.DEFAULT_TYPE):
    student_text = update.message.text
    await update.message.reply_text("Проверяю, подожди немного...")

    try:
        result_text = ask_gigachat(student_text)
        await update.message.reply_text(result_text)
    except Exception as e:
        await update.message.reply_text(f"Произошла ошибка: {e}")


def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_homework))
    app.run_polling()


if __name__ == "__main__":
    main()
