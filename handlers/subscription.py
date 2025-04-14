from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import Config

async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    if not Config.CHANNEL_USERNAME:
        return True  # Skip check if channel not configured
    
    try:
        member = await context.bot.get_chat_member(
            chat_id=f"@{Config.CHANNEL_USERNAME}",
            user_id=user.id
        )
        return member.status in ["member", "administrator", "creator"]
    except Exception:
        return False

async def send_subscription_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("انضم للقناة", url=Config.CHANNEL_LINK)],
        [InlineKeyboardButton("تم الاشتراك ✅", callback_data="check_subscription")]
    ])
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"⏳ يرجى الاشتراك في القناة أولاً:\n{Config.CHANNEL_LINK}",
        reply_markup=keyboard
    )
