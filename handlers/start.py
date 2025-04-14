from telegram import Update
from telegram.ext import ContextTypes
from utils.limits import limiter  # تغيير من استيراد نسبي إلى مطلق
from handlers.subscription import check_subscription, send_subscription_message  # استيراد مطلق

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check subscription first
    if not await check_subscription(update, context):
        await send_subscription_message(update, context)
        return
    
    user_id = update.effective_user.id
    _, time_left = limiter.check_limits(user_id)
    hours_left = int(time_left // 3600)
    remaining_uses = limiter.get_remaining_uses(user_id)
    
    welcome_msg = (
        "مرحباً بك في بوت التصحيح النحوي وإعادة الصياغة!\n\n"
        "📝 أرسل لي أي نص وسأقدم لك:\n"
        "- تصحيحاً نحوياً دقيقاً\n"
        "- إعادة صياغة محترفة\n\n"
        f"⚡ المتبقي من طلباتك اليوم: {remaining_uses}/{limiter.REQUEST_LIMIT}\n"
        f"⏳ يتم تجديد الطلبات بعد: {hours_left} ساعة\n\n"
        f"📌 ملاحظة: الحد الأقصى للنص {limiter.CHAR_LIMIT} حرفاً"
    )
    
    await update.message.reply_text(welcome_msg)
