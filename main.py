import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
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
    """Initialize all system components"""
    try:
        Config.validate_config()
        logger.info("✅ Configuration validated successfully")
        
        logger.info("Initializing Firebase...")
        db = initialize_firebase()
        db.initialize_stats()  # <-- هنا تهيئة الإحصائيات
        logger.info("✅ Firebase initialized successfully")
        
        logger.info(f"🔑 Admin usernames: {Config.ADMIN_USERNAMES}")
        return True
        
    except Exception as e:
        logger.critical(f"❌ System initialization failed: {str(e)}")
        return False

# تعديل ترتيب تسجيل المعالجات
def setup_handlers(application):
    """Register all bot handlers"""
    try:
        # تسجيل معالجات المشرفين أولاً
        from handlers.admin_panel import setup_admin_commands
        setup_admin_commands(application)
        
        # ثم باقي المعالجات
        from handlers.start import setup_start_handlers
        from handlers.text_handling import setup_text_handlers
        from handlers.subscription import setup_subscription_handlers
        from handlers.premium import setup_premium_handlers
        
        setup_start_handlers(application)
        setup_text_handlers(application)
        setup_subscription_handlers(application)
        setup_premium_handlers(application)
        
        logger.info("✅ All handlers registered successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to register handlers: {str(e)}")
        return False

async def run_bot():
    # التحقق من بيانات الاعتماد أولاً
    if not check_firebase_credentials():
        sys.exit(1)
    
    # اختبار الاتصال
    try:
        from firebase_db import db
        test_ref = db.root_ref.child('connection_test')
        test_ref.set(int(time.time()))
        logger.info(f"✅ Firebase test write successful: {test_ref.get()}")
    except Exception as e:
        logger.critical(f"❌ Firebase test failed: {str(e)}")
        sys.exit(1)
    
    
            
        application = ApplicationBuilder().token(Config.BOT_TOKEN).build()
        
        if not setup_handlers(application):
            sys.exit(1)
            
        application.add_error_handler(error_handler)
        
        webhook_url = f"{Config.WEBHOOK_URL.rstrip('/')}/{Config.BOT_TOKEN}"
        port = int(Config.PORT)
        
        logger.info(f"🌐 Webhook URL: {webhook_url}")
        logger.info(f"🔌 Port: {port}")
        
        await application.initialize()
        await application.start()
        await application.updater.start_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=Config.BOT_TOKEN,
            webhook_url=webhook_url,
            drop_pending_updates=True
        )
        
        logger.info("🤖 Bot is now running and ready to handle updates...")
        
        # Keep the application running
        while True:
            await asyncio.sleep(3600)
            
    except asyncio.CancelledError:
        logger.info("🛑 Received shutdown signal, stopping bot...")
    except Exception as e:
        logger.critical(f"🔥 Bot crashed: {str(e)}")
    finally:
        if application and application.running:
            await application.stop()
            logger.info("🛑 Bot has been stopped successfully")

if __name__ == "__main__":
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.critical(f"❌ Failed to start bot: {str(e)}")
        sys.exit(1)
