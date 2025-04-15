import asyncio
from telegram.ext import ApplicationBuilder
from config import Config
from firebase_db import initialize_firebase
import logging
import sys

# الإعدادات الأساسية
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

async def initialize_system():
    """تهيئة جميع أنظمة البوت بشكل غير متزامن"""
    try:
        # التحقق من الإعدادات أولاً
        Config.validate_config()
        
        # تهيئة Firebase
        logger.info("Initializing Firebase...")
        initialize_firebase()  # هذه ليست async لكنها تعمل بشكل متزامن
        
        logger.info(f"Firebase Connected: {Config.FIREBASE_DATABASE_URL}")
        return True
        
    except Exception as e:
        logger.critical(f"Init Failed: {e}")
        return False

async def setup_handlers(application):
    """تسجيل جميع معالجات البوت بشكل غير متزامن"""
    try:
        from handlers.start import setup_start_handlers
        from handlers.admin_panel import setup_admin_handlers
        from handlers.premium import setup as setup_premium
        
        await setup_start_handlers(application)
        await setup_admin_handlers(application)
        await setup_premium(application)
        
        logger.info("✅ All handlers registered successfully")
        
    except Exception as e:
        logger.error(f"Failed to register handlers: {e}")
        raise

async def run_bot():
    """تشغيل البوت في وضع الويب هوك بشكل غير متزامن"""
    try:
        if not await initialize_system():
            sys.exit(1)
            
        app = ApplicationBuilder().token(Config.BOT_TOKEN).build()
        
        await setup_handlers(app)
        
        # إعداد الويب هوك
        webhook_url = f"{Config.WEBHOOK_URL.rstrip('/')}/{Config.BOT_TOKEN}"
        await app.initialize()
        await app.start()
        await app.updater.start_webhook(
            listen="0.0.0.0",
            port=int(Config.PORT),
            url_path=Config.BOT_TOKEN,
            webhook_url=webhook_url,
            drop_pending_updates=True
        )
        
        logger.info(f"🤖 Bot is running on webhook: {webhook_url}")
        
        # البقاء في حالة تشغيل
        while True:
            await asyncio.sleep(3600)
            
    except Exception as e:
        logger.critical(f"🔥 Bot crashed: {e}")
        raise
    finally:
        if 'app' in locals():
            await app.stop()

if __name__ == "__main__":
    try:
        asyncio.run(run_bot())
    except Exception as e:
        logger.critical(f"❌ Failed to start bot: {e}")
        sys.exit(1)
