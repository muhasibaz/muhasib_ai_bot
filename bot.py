import os
from openai import OpenAI
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
import chromadb

print("BOT STARTING...")

# --- ENV ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# --- AI ---
client = OpenAI(api_key=OPENAI_API_KEY)

# --- CHROMA (база знаний) ---
chroma_client = chromadb.Client()
collection = chroma_client.get_or_create_collection(name="laws")

# --- ПОИСК В ДОКУМЕНТАХ ---
def search_docs(query):
    results = collection.query(
        query_texts=[query],
        n_results=3
    )
    return results.get("documents", [[]])[0]


# --- ОБРАБОТКА СООБЩЕНИЯ ---
async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text

    try:
        docs = search_docs(user_text)
        context_text = "\n\n".join(docs) if docs else "Нет данных"

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": f"""
Ты профессиональный бухгалтер и налоговый консультант Азербайджана.

Отвечай ТОЛЬКО на основе предоставленного текста.
Если информации недостаточно — напиши: "Нет точной информации в базе".

Всегда:
- указывай статью закона (если есть)
- отвечай чётко и понятно

ТЕКСТ:
{context_text}
"""
                },
                {"role": "user", "content": user_text}
            ]
        )

        answer = response.choices[0].message.content

    except Exception as e:
        answer = f"Ошибка: {str(e)}"

    await update.message.reply_text(answer)


# --- ЗАПУСК БОТА ---
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

print("BOT RUNNING...")
app.run_polling()
