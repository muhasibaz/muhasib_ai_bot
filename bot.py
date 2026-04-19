import os

# отключаем телеметрию chromadb
os.environ["ANONYMIZED_TELEMETRY"] = "False"

from openai import OpenAI
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
import chromadb

print("BOT STARTING...")

# --- ENV ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not set")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not set")

# --- AI ---
client = OpenAI(api_key=OPENAI_API_KEY)

# --- CHROMA DB ---
chroma_client = chromadb.Client(
    settings=chromadb.config.Settings(
        persist_directory="./chroma_db"
    )
)

collection = chroma_client.get_or_create_collection(name="laws")


# --- ЗАГРУЗКА ДОКУМЕНТОВ ---
def load_documents():
    if collection.count() > 0:
        return

    base_path = "data"

    try:
        for root, dirs, files in os.walk(base_path):
            for file in files:
                if file.endswith(".txt"):
                    path = os.path.join(root, file)

                    with open(path, "r", encoding="utf-8") as f:
                        text = f.read()

                    collection.add(
                        documents=[text],
                        ids=[file]
                    )

        print("Knowledge base loaded")

    except Exception as e:
        print(f"Error loading docs: {e}")


# --- ПОИСК ---
def search_docs(query):
    results = collection.query(
        query_texts=[query],
        n_results=3
    )
    return results.get("documents", [[]])[0]


# --- ОБРАБОТКА ---
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

Отвечай строго на основе текста.
Если нет точной информации — напиши: "Нет точной информации в базе".

Всегда:
- указывай статью закона
- не придумывай

ТЕКСТ:
{context_text}
"""
                },
                {"role": "user", "content": user_text}
            ]
        )

        answer = response.choices[0].message.content or "Нет ответа"

    except Exception as e:
        answer = f"Ошибка: {str(e)}"

    await update.message.reply_text(answer)


# --- ЗАПУСК ---
load_documents()

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

print("BOT RUNNING...")

# --- WEBHOOK (для Render Web Service) ---
port = int(os.environ.get("PORT", 10000))
webhook_url = f"{RENDER_EXTERNAL_URL}/{BOT_TOKEN}"

app.run_webhook(
    listen="0.0.0.0",
    port=port,
    webhook_url=webhook_url
)
