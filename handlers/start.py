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
        
        # الحصول على بيانات المستخدم
        allowed, time_left = limiter.check_limits(user_id)
        user_data = limiter.db.get_user(user_id)
        
        # حساب الوقت المتبقي بشكل صحيح
        hours_left = max(0, int(time_left // 3600)) if time_left else 0
        remaining_uses = Config.REQUEST_LIMIT - user_data.get('request_count', 0)
        
        # رسالة الترحيب المعدلة مع تحسينات بصرية
        welcome_msg = f"""
<b>✨ مرحباً بك في بوت التصحيح النحوي ✨</b>

<b>🎯 الخدمات المتاحة:</b>
- تصحيح الأخطاء النحوية والإملائية
- إعادة صياغة النصوص باحترافية

<b>📊 إحصائيات حسابك:</b>
- الطلبات المتبقية: <code>{remaining_uses}/{Config.REQUEST_LIMIT}</code>
- وقت التجديد: بعد <code>{hours_left}</code> ساعة
- الحد الأقصى للنص: <code>{Config.CHAR_LIMIT}</code> حرفاً

<b>💡 اختر طريقة الاستخدام:</b>
"""
        
        # الأزرار الرئيسية (كما كانت في الكود القديم)
        keyboard = [
            [InlineKeyboardButton("📝 الطريقة العادية (بدون API)", callback_data="normal_usage")],
            [InlineKeyboardButton("🔑 استخدام API شخصي", callback_data="api_usage")]
        ]
        
        await update.message.reply_text(
            welcome_msg,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Error in start command: {str(e)}", exc_info=True)
        await update.message.reply_text("⚠️ حدث خطأ غير متوقع. يرجى المحاولة لاحقاً.")
