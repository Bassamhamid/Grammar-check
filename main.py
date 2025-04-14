from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import requests
import os
import json

# متغيرات البيئة
TELEGRAM_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
SITE_URL = os.getenv("SITE_URL", "")
SITE_TITLE = os.getenv("SITE_TITLE", "Arabic Text Bot")
PORT = int(os.environ.get("PORT", "10000"))

# دالة استدعاء نموذج OpenRouter
def query_openrouter(prompt):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": SITE_URL,
        "X-Title": SITE_TITLE
    }

    data = {
        "model": "meta-llama/llama-4-maverick:free",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ]
    }

    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        data=json.dumps(data)
    )

    response.raise_for_status()
    result = response.json()["choices"][0]["message"]["content"]
    return result

# أمر /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أرسل لي نصًا بالعربية، وسأعطيك خيارات:\n- تصحيح نحوي\n- إعادة صياغة")

# استقبال الرسائل النصية
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

# التعامل مع الضغط على الأزرار
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, user_text = query.data.split("|", 1)

    if action == "correct":
        prompt = f"""صحح الأخطاء النحوية والإملائية فقط في النص التالي، وأرسل النص المصحح فقط بدون أي شرح أو تعليقات:

{user_text}"""
    elif action == "rewrite":
        prompt = f"""أعد صياغة النص التالي بلغة عربية فصحى سليمة مع الحفاظ على نفس المعنى، وأرسل النص المعاد صياغته فقط بدون أي شرح أو تعليقات:

{user_text}"""
    else:
        await query.edit_message_text("طلب غير معروف.")
        return

    try:
        result = query_openrouter(prompt)
        await query.edit_message_text(f"**النتيجة:**\n{result}")
    except Exception as e:
        await query.edit_message_text(f"حدث خطأ أثناء الاتصال بالنموذج:\n{e}")

# إعداد التطبيق
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

# إضافة الأوامر والموجهات
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
