from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from utils.limits import limiter
from utils.openrouter import validate_user_api
from config import Config
import logging

logger = logging.getLogger(__name__)

async def set_api(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        args = context.args
        
        if not args:
            await update.message.reply_text(
                "📌 لاستخدام API الخاص بك:\n"
                "1. احصل على مفتاح API من موقع openrouter.ai\n"
                "2. أرسل الأمر كالتالي:\n"
                "/setapi <api_key>"
            )
            return
        
        api_key = args[0]
        if await validate_user_api(api_key):
            limiter.set_premium_user(user_id, api_key)
            await update.message.reply_text(
                "✅ تم تفعيل API الخاص بنجاح!\n"
                f"📊 الآن لديك {Config.USER_API_LIMIT} طلباً يومياً\n"
                "⚡ يمكنك استخدام البوت بدون قيود النظام الأساسي"
            )
        else:
            await update.message.reply_text("❌ مفتاح API غير صالح!")
            
    except Exception as e:
        logger.error(f"Error in set_api: {str(e)}")
        await update.message.reply_text("⚠️ حدث خطأ أثناء معالجة طلبك.")

def setup(application):
    application.add_handler(CommandHandler("setapi", set_api))
