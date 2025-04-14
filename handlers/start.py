from telegram import Update
from telegram.ext import ContextTypes
from .subscription import check_subscription, send_subscription_message
from utils.limits import limiter

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_subscription(update, context):
        await send_subscription_message(update, context)
        return
    
    _, time_left = limiter.check_limits(update.effective_user.id)
    hours_left = int(time_left // 3600)
    
    welcome_msg = (
        "مرحباً بك في بوت التصحيح النحوي وإعادة الصياغة!\n\n"
        "📝 أرسل لي أي نص وسأقدم لك:\n"
        "- تصحيحاً نحوياً دقيقاً\n"
        "- إعادة صياغة محترفة\n\n"
        f"⚡ المتبقي من طلباتك اليوم: {limiter.user_data.get(update.effective_user.id, {}).get('count', 0)}/{limiter.REQUEST_LIMIT}\n"
        f"⏳ يتم تجديد الطلبات بعد: {hours_left} ساعة\n\n"
        "📌 ملاحظة: الحد الأقصى للنص 120 حرفاً"
    )
    
    await update.message.reply_text(welcome_msg)
