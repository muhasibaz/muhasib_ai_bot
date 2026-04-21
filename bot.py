import os

# --- ОТКЛЮЧАЕМ телеметрию chromadb ---
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


# --- ОПРЕДЕЛЕНИЕ КАТЕГОРИИ ---
def detect_category(query):
    q = query.lower()

    tax_keywords = ["ədv", "vergi", "mənfəət", "gəlir", "əlavə dəyər vergisi"]
    labor_keywords = ["məzuniyyət", "əmək", "işçi", "əmək haqqı"]

    if any(word in q for word in tax_keywords):
        return "tax"
    if any(word in q for word in labor_keywords):
        return "labor"

    return None


# --- ЗАГРУЗКА ДОКУМЕНТОВ ---
def load_documents():
    print("Reloading knowledge base...")

    try:
        # ❗ УДАЛЯЕМ всю коллекцию
        try:
            chroma_client.delete_collection(name="laws")
        except:
            pass

        # ❗ создаём заново
        global collection
        collection = chroma_client.get_or_create_collection(name="laws")

        base_path = "data"

        for root, dirs, files in os.walk(base_path):
            for file in files:
                if file.endswith(".txt"):
                    path = os.path.join(root, file)

                    with open(path, "r", encoding="utf-8") as f:
                        text = f.read()

                    # определяем категорию
                    if "tax" in root:
                        category = "tax"
                    elif "labor" in root:
                        category = "labor"
                    else:
                        category = "other"

                    # разбиваем на чанки
                    chunk_size = 700
                    chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

                    for i, chunk in enumerate(chunks):
                        collection.add(
                            documents=[chunk],
                            ids=[f"{path}_{i}"],
                            metadatas=[{"category": category}]
                        )

        chroma_client.persist()
        print("Knowledge base loaded")

    except Exception as e:
        print(f"Error loading docs: {e}")


# --- ПОИСК ---
def search_docs(query):
    category = detect_category(query)

    if category:
        results = collection.query(
            query_texts=[query],
            n_results=3,
            where={"category": category}
        )
    else:
        results = collection.query(
            query_texts=[query],
            n_results=3
        )

    return results.get("documents", [[]])[0]


# --- ОБРАБОТКА СООБЩЕНИЙ ---
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
Ты профессиональный налоговый и бухгалтерский консультант Азербайджана.

Отвечай ТОЛЬКО на основе предоставленного текста.

Если информации недостаточно ищи во внешних проверенных источниках и на страницах сайтов www.muhasib.az и www.e-muhasib.az.

ЗАПРЕЩЕНО:
- додумывать

ОБЯЗАТЕЛЬНО:
- указывать статью закона
- отвечать кратко и по делу

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


# --- WEBHOOK (для Render) ---
port = int(os.environ.get("PORT", 10000))
webhook_url = f"{RENDER_EXTERNAL_URL}/{BOT_TOKEN}"

app.run_webhook(
    listen="0.0.0.0",
    port=port,
    url_path=BOT_TOKEN,  # 👈 ВАЖНО
    webhook_url=f"{RENDER_EXTERNAL_URL}/{BOT_TOKEN}"
)
