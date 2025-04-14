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
        allowed, time_left, char_limit = limiter.check_limits(user_id)
        user_data = limiter.db.get_user(user_id)
        
        # حساب الوقت المتبقي
        current_time = time.time()
        reset_time = user_data.get('reset_time', current_time + (Config.PREMIUM_RESET_HOURS * 3600 if is_premium else Config.RESET_HOURS * 3600))
        time_left = max(0, reset_time - current_time)
        hours_left = max(0, int(time_left // 3600))
        
        # تحديد الحدود للعرض
        if is_premium:
            request_limit = Config.PREMIUM_REQUEST_LIMIT
            remaining_uses = request_limit - user_data.get('request_count', 0)
            limit_msg = f"🌟 (حساب مميز) الطلبات المتبقية: {remaining_uses}/{request_limit}"
            char_msg = f"📝 الحد الأقصى للنص: {Config.PREMIUM_CHAR_LIMIT} حرفاً"
        else:
            request_limit = Config.REQUEST_LIMIT
            remaining_uses = request_limit - user_data.get('request_count', 0)
            limit_msg = f"📊 الطلبات المتبقية: {remaining_uses}/{request_limit}"
            char_msg = f"📝 الحد الأقصى للنص: {Config.CHAR_LIMIT} حرفاً"

        # رسالة الترحيب المعدلة
        welcome_msg = (
            "✨ مرحباً بك في بوت التصحيح النحوي ✨\n\n"
            f"{limit_msg}\n"
            f"⏳ وقت التجديد: بعد {hours_left} ساعة\n"
            f"{char_msg}\n\n"
            "🎯 الخدمات المتاحة:\n"
            "- تصحيح الأخطاء النحوية والإملائية\n"
            "- إعادة صياغة النصوص باحترافية\n\n"
            "💡 لتفعيل API الخاص بك والحصول على:\n"
            f"- {Config.PREMIUM_REQUEST_LIMIT} طلب يومياً\n"
            f"- حد {Config.PREMIUM_CHAR_LIMIT} حرفاً للنص\n"
            "أرسل: /setapi <api_key>"
        )
        
        # إضافة زر البدء إن أردت
        keyboard = [
            [InlineKeyboardButton("🚀 بدء الاستخدام", callback_data="start_using")]
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
        await query.edit_message_text("📝 يرجى إرسال النص الذي تريد معالجته:")
    except Exception as e:
        logger.error(f"Error in start button: {str(e)}")
        await query.edit_message_text("⚠️ حدث خطأ أثناء المعالجة.")
