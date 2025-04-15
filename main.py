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
from handlers.start import setup_start_handlers
from handlers.text_handling import handle_message, handle_callback
from handlers.subscription import check_subscription, verify_subscription_callback
from handlers.premium import setup as setup_premium
from handlers.admin_panel import setup_admin_handlers
import logging
import sys
import time

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

def initialize_system():
    """Initialize all system components"""
    try:
        start_time = time.time()
        
        # Validate configuration
        Config.validate_config()
        logger.info("✅ Configuration validated successfully")
        
        # Initialize Firebase
        logger.info("Initializing Firebase...")
        initialize_firebase()
        logger.info(f"✅ Firebase initialized in {time.time()-start_time:.2f}s")
        
        # Log admin info
        logger.info(f"🔑 Admin usernames: {Config.ADMIN_USERNAMES}")
        
    except Exception as e:
        logger.critical(f"❌ System initialization failed: {str(e)}")
        logger.info("💡 Troubleshooting Tips:")
        logger.info("1. Check all required environment variables are set on Render")
        logger.info("2. Verify FIREBASE_DATABASE_URL is correct")
        logger.info("3. Ensure FIREBASE_SERVICE_ACCOUNT_JSON is valid JSON")
        raise

def setup_handlers(application):
    """Register all bot handlers"""
    try:
        start_time = time.time()
        
        # Admin filter
        admin_filter = filters.ChatType.PRIVATE & filters.User(username=Config.ADMIN_USERNAMES)
        
        # User filter
        user_filter = filters.ChatType.PRIVATE & ~admin_filter
        
        # 1. Start and subscription handlers
        setup_start_handlers(application)
        
        # 2. Admin handlers
        setup_admin_handlers(application)
        
        # 3. User message handlers
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
        
        # 4. Premium features
        setup_premium(application)
        
        logger.info(f"✅ Handlers registered in {time.time()-start_time:.2f}s")
        
    except Exception as e:
        logger.error(f"Failed to register handlers: {str(e)}")
        raise

def run_bot():
    """Run the bot in webhook mode"""
    try:
        logger.info("🚀 Starting bot...")
        start_time = time.time()
        
        # Build application
        app = ApplicationBuilder() \
            .token(Config.BOT_TOKEN) \
            .post_init(lambda app: logger.info("✅ Bot initialized successfully")) \
            .build()
        
        # Setup handlers
        setup_handlers(app)
        
        # Add error handler
        app.add_error_handler(error_handler)
        
        # Webhook configuration
        webhook_url = f"{Config.WEBHOOK_URL.rstrip('/')}/{Config.BOT_TOKEN}"
        port = int(Config.PORT)
        
        logger.info(f"🌐 Webhook URL: {webhook_url}")
        logger.info(f"🔌 Port: {port}")
        
        # Run bot
        app.run_webhook(
            listen="0.0.0.0",
            port=port,
            webhook_url=webhook_url,
            url_path=Config.BOT_TOKEN,
            drop_pending_updates=True
        )
        
    except Exception as e:
        logger.critical(f"🔥 Bot crashed: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        initialize_system()
        run_bot()
    except Exception as e:
        logger.critical(f"❌ Failed to start bot: {str(e)}")
        sys.exit(1)
