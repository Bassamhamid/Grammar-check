from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from config import Config
from handlers.start import start
from handlers.text_handling import handle_message, handle_callback
from handlers.subscription import check_subscription, verify_subscription_callback

def main():
    # Build application
    app = ApplicationBuilder().token(Config.BOT_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback, pattern="^(correct|rewrite)$"))
    app.add_handler(CallbackQueryHandler(verify_subscription_callback, pattern="^check_subscription$"))
    
    # Check subscription (lower priority group)
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, check_subscription), group=1)
    app.add_handler(CallbackQueryHandler(check_subscription), group=1)
    
    # Run bot
    app.run_webhook(
        listen="0.0.0.0",
        port=Config.PORT,
        url_path=Config.BOT_TOKEN,
        webhook_url=f"{Config.WEBHOOK_URL}/{Config.BOT_TOKEN}"
    )

if __name__ == "__main__":
    main()
