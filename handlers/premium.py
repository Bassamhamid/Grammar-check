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
        
        if not context.args:
            await update.message.reply_text(
                "📌 لاستخدام API الخاص بك:\n"
                "1. احصل على مفتاح API من موقع openrouter.ai\n"
                "2. أرسل الأمر:\n"
                "/setapi your_api_key_here"
            )
            return
        
        api_key = context.args[0]
        if await validate_user_api(api_key):
            limiter.set_premium_user(user_id, api_key)
            await update.message.reply_text(
                "✅ تم تفعيل API الخاص بنجاح!\n"
                f"📊 الآن لديك {Config.PREMIUM_REQUEST_LIMIT} طلباً يومياً\n"
                f"📝 وحد أقصى {Config.PREMIUM_CHAR_LIMIT} حرفاً للنص"
            )
        else:
            await update.message.reply_text("❌ مفتاح API غير صالح!")
            
    except Exception as e:
        logger.error(f"Error in set_api: {str(e)}")
        await update.message.reply_text("⚠️ حدث خطأ أثناء معالجة API الخاص بك.")

async def unset_api(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        if limiter.is_premium_user(user_id):
            del limiter.premium_users[user_id]
            await update.message.reply_text("✅ تم إلغاء تفعيل API الخاص بك.")
        else:
            await update.message.reply_text("⚠️ لم يكن لديك API مفعل.")
            
    except Exception as e:
        logger.error(f"Error in unset_api: {str(e)}")
        await update.message.reply_text("⚠️ حدث خطأ أثناء إلغاء التفعيل.")

def setup_premium_handlers(application):
    """
    إعداد معالجات الميزات المميزة (Premium)
    """
    application.add_handler(CommandHandler("setapi", set_api))
    application.add_handler(CommandHandler("unsetapi", unset_api))

# للحفاظ على التوافق مع الإصدارات القديمة
def setup(application):
    setup_premium_handlers(application)
