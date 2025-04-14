from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler
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
        
        # رسالة الترحيب بتنسيق HTML
        welcome_msg = f"""
<b>✨ مرحباً بك في بوت التصحيح النحوي ✨</b>

<b>📋 خطة الاستخدام الحالية:</b>
- عدد الطلبات اليومية: <code>{Config.PREMIUM_REQUEST_LIMIT if is_premium else Config.REQUEST_LIMIT}</code>
- الطلبات المتبقية: <code>{Config.PREMIUM_REQUEST_LIMIT - request_count if is_premium else Config.REQUEST_LIMIT - request_count}</code>
- الحد الأقصى للنص: <code>{Config.PREMIUM_CHAR_LIMIT if is_premium else Config.CHAR_LIMIT}</code> حرفاً
- وقت تجديد الطلبات: بعد <code>{hours_left}</code> ساعة

<b>💎 ترقية الحساب:</b>
يمكنك استخدام API شخصي للحصول على:
- <code>{Config.PREMIUM_REQUEST_LIMIT}</code> طلب يومياً
- حد <code>{Config.PREMIUM_CHAR_LIMIT}</code> حرفاً للنص

<b>🔑 كيفية الحصول على API مجاني:</b>
1. سجل في <a href="https://openrouter.ai">OpenRouter.ai</a>
2. احصل على مفتاح API من لوحة التحكم
3. أرسل لي المفتاح بهذا الشكل:
<code>/setapi مفتاحك_السري</code>

<b>📝 لبدء الاستخدام:</b>
انقر الزر أدناه أو أرسل النص مباشرة
"""
        
        keyboard = [
            [InlineKeyboardButton("🚀 بدء المعالجة", callback_data="start_processing")],
            [InlineKeyboardButton("🔗 موقع OpenRouter", url="https://openrouter.ai")]
        ]
        
        await update.message.reply_text(
            welcome_msg, 
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML",
            disable_web_page_preview=True
        )

    except Exception as e:
        logger.error(f"Error in start command: {str(e)}", exc_info=True)
        await update.message.reply_text("⚠️ حدث خطأ غير متوقع")

async def handle_process_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        
        # إرشادات الاستخدام بتنسيق HTML
        examples = """
<b>📌 كيفية الاستخدام:</b>

<u>الطريقة الأولى:</u>
1. أرسل النص مباشرة
2. اختر الخدمة من القائمة

<u>الطريقة الثانية:</u>
1. انقر على أيقونة 📎
2. اختر <code>الملف</code> أو <code>الصورة</code> تحتوي على النص
3. انتظر المعالجة

<b>📝 أمثلة:</b>
<code>• "كانت الجو جميله في الخارج"</code> (لتصحيح الأخطاء)
<code>• "أعد صياغة هذا النص بلغة عربية فصحى"</code> (لإعادة الصياغة)
"""
        
        await query.edit_message_text(
            examples,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 العودة للرئيسية", callback_data="back_to_start")]
            ])
        )
        
    except Exception as e:
        logger.error(f"Error in process button: {str(e)}")
        await query.edit_message_text("⚠️ حدث خطأ، يرجى المحاولة مرة أخرى")

async def back_to_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

def setup_start_handlers(application):
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(handle_process_button, pattern='^start_processing$'))
    application.add_handler(CallbackQueryHandler(back_to_start, pattern='^back_to_start$'))
