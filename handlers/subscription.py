from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from telegram.error import BadRequest
from config import Config

async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    # Skip check if channel not configured
    if not Config.CHANNEL_USERNAME:
        return True
    
    user = update.effective_user
    if not user:
        return False
    
    try:
        # Try to get chat member (works for public channels)
        chat_member = await context.bot.get_chat_member(
            chat_id=f"@{Config.CHANNEL_USERNAME}",
            user_id=user.id
        )
        return chat_member.status in ["member", "administrator", "creator"]
    except BadRequest as e:
        if "user not found" in str(e).lower():
            # User never interacted with the bot before
            return False
        elif "chat not found" in str(e).lower():
            # Channel doesn't exist or bot not admin
            print(f"Error: Channel @{Config.CHANNEL_USERNAME} not found or bot not admin")
            return True  # Skip check to avoid blocking users
        return False
    except Exception as e:
        print(f"Subscription check error: {str(e)}")
        return True  # Skip check on other errors

async def send_subscription_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("انضم للقناة", url=Config.CHANNEL_LINK)],
        [InlineKeyboardButton("✅ تأكيد الاشتراك", callback_data="check_subscription")]
    ])
    
    message = (
        "🔒 للوصول إلى البوت، يرجى الاشتراك في قناتنا أولاً:\n"
        f"{Config.CHANNEL_LINK}\n\n"
        "بعد الاشتراك، اضغط على زر '✅ تأكيد الاشتراك'"
    )
    
    if update.callback_query:
        await update.callback_query.edit_message_text(message, reply_markup=keyboard)
    else:
        await update.message.reply_text(message, reply_markup=keyboard)

async def verify_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if await check_subscription(update, context):
        await query.edit_message_text("✅ تم التحقق من اشتراكك بنجاح! يمكنك الآن استخدام البوت.")
        # إعادة توجيه المستخدم إلى البداية
        from handlers.start import start
        await start(update, context)
    else:
        await query.answer("⚠️ لم يتم التحقق من اشتراكك بعد. يرجى الانضمام للقناة أولاً.", show_alert=True)

def setup_subscription_handlers(application):
    """
    إعداد معالجات الاشتراك في القناة
    """
    application.add_handler(CallbackQueryHandler(
        verify_subscription_callback,
        pattern="^check_subscription$"
    ))
