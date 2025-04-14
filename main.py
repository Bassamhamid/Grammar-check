from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import requests
import os

from telegram.ext import WebhookHandler

TELEGRAM_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

PORT = int(os.environ.get("PORT", "10000"))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أرسل لي نصًا بالعربية، وسأعطيك خيارات:\n- تصحيح نحوي\n- إعادة صياغة")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text

    keyboard = [
        [
            InlineKeyboardButton("تصحيح نحوي", callback_data=f"correct|{user_text}"),
            InlineKeyboardButton("إعادة صياغة", callback_data=f"rewrite|{user_text}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("اختر ماذا تريد أن أفعل بالنص:", reply_markup=reply_markup)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, user_text = query.data.split("|", 1)

    if action == "correct":
        prompt = f"صحح النص النحوي التالي بدون تغيير معناه:\n{user_text}"
    elif action == "rewrite":
        prompt = f"أعد صياغة النص التالي بلغة عربية فصحى سليمة مع الحفاظ على المعنى:\n{user_text}"
    else:
        await query.edit_message_text("طلب غير معروف.")
        return

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "mistralai/mistral-7b-instruct",
        "messages": [
            {"role": "system", "content": "أنت مساعد ذكي متخصص في تحسين وصياغة النصوص العربية."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 500
    }

    response = requests.post("https://openrouter.ai/api/v1/chat/completions", json=data, headers=headers)

    result = response.json()["choices"][0]["message"]["content"]

    await query.edit_message_text(f"**النتيجة:**\n{result}")

# إعداد التطبيق مع Webhook
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

# الأوامر والموجهات
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT, handle_message))
app.add_handler(CallbackQueryHandler(handle_callback))

# تشغيل البوت مع Webhook
app.run_webhook(
    listen="0.0.0.0",
    port=PORT,
    url_path=TELEGRAM_TOKEN,
    webhook_url=f"{WEBHOOK_URL}/{TELEGRAM_TOKEN}"
      )
