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
        
        # الحصول على بيانات المستخدم مع التعامل مع الأخطاء
        try:
            user_data = limiter.db.get_user(user_id)
            allowed, time_left = limiter.check_limits(user_id)
            hours_left = max(0, int(time_left // 3600)) if time_left else 0
            remaining_uses = Config.REQUEST_LIMIT - user_data.get('request_count', 0)
        except Exception as e:
            logger.error(f"Failed to get user data: {str(e)}")
            await update.message.reply_text("⚠️ حدث خطأ في تحميل بياناتك. يرجى المحاولة لاحقاً.")
            return

        # رسالة الترحيب المعدلة
        welcome_msg = (
            "✨ مرحباً بك في بوت التصحيح النحوي وإعادة الصياغة ✨\n\n"
            "🎯 الخدمات المتاحة:\n"
            "- تصحيح الأخطاء النحوية والإملائية\n"
            "- إعادة صياغة النصوص باحترافية\n\n"
            f"📊 عدد الطلبات المتبقية: {remaining_uses}/{Config.REQUEST_LIMIT}\n"
            f"⏳ وقت التجديد: بعد {hours_left} ساعة\n"
            f"📝 الحد الأقصى للنص: {Config.CHAR_LIMIT} حرفاً\n\n"
            "💡 لإدخال API الخاص بك واستخدام البوت بدون قيود:\n"
            "أرسل /setapi <api_key>"
        )
        
        # إضافة زر للبدء
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
