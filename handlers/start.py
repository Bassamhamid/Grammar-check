from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from utils.limits import limiter
from handlers.subscription import check_subscription, send_subscription_message
from config import Config
import time
import logging

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not await check_subscription(update, context):
            await send_subscription_message(update, context)
            return
        
        user_id = update.effective_user.id
        is_premium = limiter.is_premium_user(user_id)
        user_data = limiter.db.get_user(user_id)
        request_count = user_data.get('request_count', 0)
        
        current_time = time.time()
        reset_time = user_data.get('reset_time', current_time + (Config.PREMIUM_RESET_HOURS * 3600 if is_premium else Config.RESET_HOURS * 3600))
        time_left = max(0, reset_time - current_time)
        hours_left = max(0, int(time_left // 3600))
        
        welcome_msg = (
            "✨ مرحباً بك في بوت التصحيح النحوي ✨\n\n"
            "📋 خطة الاستخدام الحالية:\n"
            f"- عدد الطلبات اليومية: {Config.PREMIUM_REQUEST_LIMIT if is_premium else Config.REQUEST_LIMIT}\n"
            f"- الطلبات المتبقية: {Config.PREMIUM_REQUEST_LIMIT - request_count if is_premium else Config.REQUEST_LIMIT - request_count}\n"
            f"- الحد الأقصى للنص: {Config.PREMIUM_CHAR_LIMIT if is_premium else Config.CHAR_LIMIT} حرفاً\n\n"
            "💎 لترقية حسابك:\n"
            "أرسل: /setapi مفتاح_الAPI_الخاص_بك\n\n"
            "📝 لبدء المعالجة، انقر الزر أدناه أو أرسل النص مباشرة"
        )
        
        keyboard = [
            [InlineKeyboardButton("📝 بدء المعالجة", callback_data="start_processing")]
        ]
        
        await update.message.reply_text(
            welcome_msg, 
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Error in start command: {str(e)}", exc_info=True)
        await update.message.reply_text("⚠️ حدث خطأ غير متوقع")

async def handle_process_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        
        # إرشادات الاستخدام مع أمثلة
        examples = (
            "📌 **إرسل النص مباشرة مثل:**\n\n"
            "1. لتصحيح الأخطاء:\n"
            "\"كانت الجو جميله في الخارج\"\n\n"
            "2. لإعادة الصياغة:\n"
            "\"أريد إعادة صياغة هذه الجملة بطريقة أكثر احترافية\"\n\n"
            "ثم اختر الخدمة من القائمة التي تظهر"
        )
        
        await query.edit_message_text(
            examples,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error in process button: {str(e)}")
        await query.edit_message_text("⚠️ حدث خطأ، يرجى المحاولة مرة أخرى")

def setup_start_handlers(application):
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(handle_process_button, pattern='^start_processing$'))
