from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import Config
from utils.limits import limiter
from utils.openrouter import query_openrouter
from .subscription import check_subscription, send_subscription_message

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check subscription first
    if not await check_subscription(update, context):
        await send_subscription_message(update, context)
        return
    
    user_text = update.message.text
    user_id = update.effective_user.id
    
    # Check character limit
    if len(user_text) > Config.CHAR_LIMIT:
        await update.message.reply_text(
            f"⚠️ عذراً، الحد الأقصى المسموح به هو {Config.CHAR_LIMIT} حرفاً.\n"
            f"عدد أحرف نصك: {len(user_text)}"
        )
        return
    
    # Check usage limits
    allowed, time_left = limiter.check_limits(user_id)
    if not allowed:
        hours_left = int(time_left // 3600)
        await update.message.reply_text(
            "⏳ لقد استهلكت جميع طلباتك اليومية.\n"
            f"سيتم تجديد الطلبات بعد: {hours_left} ساعة"
        )
        return
    
    # Store text for callback
    context.user_data['last_text'] = user_text
    
    # Create menu
    keyboard = [
        [
            InlineKeyboardButton("🛠 تصحيح نحوي", callback_data="correct"),
            InlineKeyboardButton("🔄 إعادة صياغة", callback_data="rewrite")
        ]
    ]
    
    await update.message.reply_text(
        "🔍 اختر الخدمة المطلوبة:",
        reply_markup=InlineKeyboardMarkup(keyboard)
)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Check subscription on every interaction
    if not await check_subscription(update, context):
        await send_subscription_message(update, context)
        await query.delete_message()
        return
    
    user_id = query.from_user.id
    action = query.data
    user_text = context.user_data.get('last_text', '')
    
    if not user_text:
        await query.edit_message_text("❌ عذراً، لم يتم العثور على النص المطلوب.")
        return
    
    # Check limits again (prevent abuse)
    allowed, _ = limiter.check_limits(user_id)
    if not allowed:
        await query.edit_message_text("⏳ لقد استهلكت جميع طلباتك اليومية.")
        return
    
    # Prepare prompt based on action
    if action == "correct":
        prompt = (
            "صحح الأخطاء النحوية والإملائية في النص التالي مع الحفاظ على نفس المعنى:\n\n"
            f"{user_text}\n\n"
            "الرجاء إرسال النص المصحح فقط دون أي تعليقات إضافية."
        )
    elif action == "rewrite":
        prompt = (
            "أعد صياغة النص التالي بلغة عربية فصحى سليمة مع الحفاظ على نفس المعنى:\n\n"
            f"{user_text}\n\n"
            "الرجاء إرسال النص المعاد صياغته فقط دون أي تعليقات إضافية."
        )
    else:
        await query.edit_message_text("⚠️ أمر غير معروف")
        return
    
    try:
        # Show processing message
        await query.edit_message_text("⏳ جاري المعالجة...")
        
        # Call API
        result = query_openrouter(prompt)
        
        # Increment usage only after successful operation
        limiter.increment_usage(user_id)
        
        # Send result with remaining uses
        remaining, _ = limiter.check_limits(user_id)
        remaining_uses = Config.REQUEST_LIMIT - limiter.user_data[user_id]["count"]
        
        await query.edit_message_text(
            f"✅ النتيجة:\n\n{result}\n\n"
            f"📊 المتبقي من طلباتك: {remaining_uses}/{Config.REQUEST_LIMIT}",
            parse_mode="Markdown"
        )
    except Exception as e:
        await query.edit_message_text(
            "❌ حدث خطأ أثناء معالجة طلبك. يرجى المحاولة لاحقاً."
        )
