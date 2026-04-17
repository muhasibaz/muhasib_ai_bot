from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from openai import OpenAI
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def ask_ai(question):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Ты эксперт по бухгалтерии и налогам Азербайджана"},
            {"role": "user", "content": question}
        ]
    )
    return response.choices[0].message.content

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    answer = ask_ai(text)
    await update.message.reply_text(answer)

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT, handle))

app.run_polling()
