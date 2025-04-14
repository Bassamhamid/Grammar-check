from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from config import Config
from handlers.start import start
from handlers.text_handling import handle_message, handle_callback
from handlers.subscription import check_subscription, verify_subscription_callback

def main():
    app = ApplicationBuilder().token(Config.BOT_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback, pattern="^(correct|rewrite)$"))
    app.add_handler(CallbackQueryHandler(verify_subscription_callback, pattern="^check_subscription$"))
    
    # Error handler
    app.add_error_handler(error_handler)
    
    app.run_webhook(
        listen="0.0.0.0",
        port=Config.PORT,
        url_path=Config.BOT_TOKEN,
        webhook_url=f"{Config.WEBHOOK_URL}/{Config.BOT_TOKEN}"
    )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"حدث خطأ: {context.error}")
    if update.effective_message:
        await update.effective_message.reply_text("⚠️ حدث خطأ غير متوقع. يرجى المحاولة لاحقاً.")

if __name__ == "__main__":
    main()
