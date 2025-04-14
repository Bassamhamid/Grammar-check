from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from utils.limits import limiter
from handlers.subscription import check_subscription, send_subscription_message
from config import Config
import time
import logging

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # التحقق من الاشتراك أولاً
        if not await check_subscription(update, context):
            await send_subscription_message(update, context)
            return
        
        user_id = update.effective_user.id
        is_premium = limiter.is_premium_user(user_id)
        
        # الحصول على بيانات المستخدم مع تحديد الحدود
        user_data = limiter.db.get_user(user_id)
        request_count = user_data.get('request_count', 0)
        
        # حساب الوقت المتبقي
        current_time = time.time()
        reset_time = user_data.get('reset_time', current_time + (Config.PREMIUM_RESET_HOURS * 3600 if is_premium else Config.RESET_HOURS * 3600))
        time_left = max(0, reset_time - current_time)
        hours_left = max(0, int(time_left // 3600))
        
        # رسالة الترحيب المعدلة
        welcome_msg = (
            "✨ مرحباً بك في بوت التصحيح النحوي ✨\n\n"
            "📋 خطة الاستخدام الحالية:\n"
            f"- عدد الطلبات اليومية: {Config.PREMIUM_REQUEST_LIMIT if is_premium else Config.REQUEST_LIMIT}\n"
            f"- الطلبات المتبقية: {Config.PREMIUM_REQUEST_LIMIT - request_count if is_premium else Config.REQUEST_LIMIT - request_count}\n"
            f"- الحد الأقصى للنص: {Config.PREMIUM_CHAR_LIMIT if is_premium else Config.CHAR_LIMIT} حرفاً\n"
            f"- وقت تجديد الطلبات: بعد {hours_left} ساعة\n\n"
            "💎 لترقية حسابك واستخدام API الخاص:\n"
            "أرسل الأمر التالي مع مفتاحك:\n"
            "/setapi ثم ضع مفتاح API الخاص بك\n\n"
            "مثال:\n"
            "/setapi sk-123456789abcdef\n\n"
            "مميزات API الشخصي:\n"
            f"- {Config.PREMIUM_REQUEST_LIMIT} طلب يومياً\n"
            f"- حد {Config.PREMIUM_CHAR_LIMIT} حرفاً للنص"
        )
        
        # زر البدء مع تعديل callback_data
        keyboard = [
            [InlineKeyboardButton("📝 بدء المعالجة", callback_data="process_text")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(welcome_msg, reply_markup=reply_markup)

    except Exception as e:
        logger.error(f"Error in start command: {str(e)}", exc_info=True)
        await update.message.reply_text("⚠️ حدث خطأ غير متوقع. يرجى المحاولة لاحقاً.")

async def handle_start_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        
        # إرسال رسالة توجيهية مع مثال للاستخدام
        guide_msg = (
            "📌 كيفية الاستخدام:\n\n"
            "1. أرسل النص الذي تريد معالجته مباشرة\n"
            "2. اختر الخدمة المطلوبة من القائمة\n\n"
            "مثال:\n"
            "يمكنك تصحيح هذا النص:\n"
            "\"كانت الجو جميله في الخارج\""
        )
        
        await query.edit_message_text(guide_msg)
        
    except Exception as e:
        logger.error(f"Error in start button: {str(e)}")
        await query.edit_message_text("⚠️ حدث خطأ أثناء المعالجة.")
