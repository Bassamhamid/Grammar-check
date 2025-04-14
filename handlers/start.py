from telegram import Update
from telegram.ext import ContextTypes
from utils.limits import limiter
from handlers.subscription import check_subscription, send_subscription_message
from config import Config

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # التحقق من الاشتراك أولاً
    if not await check_subscription(update, context):
        await send_subscription_message(update, context)
        return
    
    user_id = update.effective_user.id
    
    # الحصول على بيانات المستخدم من Firebase
    user_data = limiter.db.get_user(user_id)
    allowed, time_left = limiter.check_limits(user_id)
    hours_left = int(time_left // 3600) if time_left > 0 else 0
    
    # حساب الطلبات المتبقية
    remaining_uses = Config.REQUEST_LIMIT - user_data.get('request_count', 0)
    
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

async def handle_start_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("📝 يرجى إرسال النص الذي تريد معالجته:")
