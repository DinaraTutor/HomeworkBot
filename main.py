import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from anthropic import Anthropic

# Ключи берутся из переменных окружения (задаются на сервере bothost.ru,
# в код их вписывать не нужно — это безопаснее)
TELEGRAM_TOKEN = os.environ.get("BOT_TOKEN")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY")

client = Anthropic(api_key=ANTHROPIC_KEY)

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
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": student_text}],
        )
        result_text = response.content[0].text
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
