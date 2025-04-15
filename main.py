import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)
from config import Config
from firebase_db import initialize_firebase
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log')
    ]
)
logger = logging.getLogger(__name__)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Error: {context.error}", exc_info=True)
    if update and update.effective_message:
        await update.effective_message.reply_text("⚠️ حدث خطأ غير متوقع. يرجى المحاولة لاحقاً.")

async def initialize_system():
    """Initialize all system components asynchronously"""
    try:
        # Validate configuration
        Config.validate_config()
        logger.info("✅ Configuration validated successfully")
        
        # Initialize Firebase
        logger.info("Initializing Firebase...")
        initialize_firebase()
        logger.info("✅ Firebase initialized successfully")
        
        # Log admin info
        logger.info(f"🔑 Admin usernames: {Config.ADMIN_USERNAMES}")
        return True
        
    except Exception as e:
        logger.critical(f"❌ System initialization failed: {str(e)}")
        logger.info("💡 Troubleshooting Tips:")
        logger.info("1. Check all required environment variables")
        logger.info(f"2. FIREBASE_DATABASE_URL: {getattr(Config, 'FIREBASE_DATABASE_URL', 'NOT SET')}")
        return False

async def setup_handlers(application):
    """Register all bot handlers asynchronously"""
    try:
        from handlers.start import setup_start_handlers
        from handlers.text_handling import handle_message, handle_callback
        from handlers.subscription import check_subscription, verify_subscription_callback
        from handlers.premium import setup as setup_premium
        from handlers.admin_panel import setup_admin_handlers
        
        # Admin filter
        admin_filter = filters.ChatType.PRIVATE & filters.User(username=Config.ADMIN_USERNAMES)
        user_filter = filters.ChatType.PRIVATE & ~admin_filter
        
        # Setup handlers
        await setup_start_handlers(application)
        await setup_admin_handlers(application)
        
        # Add message handlers
        application.add_handler(MessageHandler(
            user_filter & filters.TEXT & ~filters.COMMAND,
            handle_message
        ))
        
        application.add_handler(CallbackQueryHandler(
            handle_callback,
            pattern="^(correct|rewrite|cancel_api|use_api)$"
        ))
        
        application.add_handler(CallbackQueryHandler(
            verify_subscription_callback,
            pattern="^check_subscription$"
        ))
        
        await setup_premium(application)
        
        logger.info("✅ All handlers registered successfully")
        
    except Exception as e:
        logger.error(f"Failed to register handlers: {str(e)}")
        raise

async def run_bot():
    """Run the bot in webhook mode asynchronously"""
    try:
        if not await initialize_system():
            sys.exit(1)
            
        # Build application
        application = ApplicationBuilder().token(Config.BOT_TOKEN).build()
        
        # Setup handlers
        await setup_handlers(application)
        
        # Add error handler
        application.add_error_handler(error_handler)
        
        # Webhook configuration
        webhook_url = f"{Config.WEBHOOK_URL.rstrip('/')}/{Config.BOT_TOKEN}"
        port = int(Config.PORT)
        
        logger.info(f"🌐 Webhook URL: {webhook_url}")
        logger.info(f"🔌 Port: {port}")
        
        # Run bot
        await application.initialize()
        await application.start()
        await application.updater.start_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=Config.BOT_TOKEN,
            webhook_url=webhook_url,
            drop_pending_updates=True
        )
        
        logger.info("🤖 Bot is now running...")
        
        # Keep the application running
        while True:
            await asyncio.sleep(3600)
            
    except Exception as e:
        logger.critical(f"🔥 Bot crashed: {str(e)}")
        raise
    finally:
        if 'application' in locals():
            await application.stop()

if __name__ == "__main__":
    try:
        asyncio.run(run_bot())
    except Exception as e:
        logger.critical(f"❌ Failed to start bot: {str(e)}")
        sys.exit(1)
