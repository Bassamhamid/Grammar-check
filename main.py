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
import os
import sys

# تهيئة النظام
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"حدث خطأ: {context.error}", exc_info=True)
    if update.effective_message:
        await update.effective_message.reply_text("⚠️ حدث خطأ غير متوقع. يرجى المحاولة لاحقاً.")

def initialize_system():
    try:
        initialize_firebase()
        logger.info("✅ تم تهيئة Firebase بنجاح")
        
        # قائمة المتغيرات المطلوبة (تم تحديثها لاستخدام ADMIN_USERNAMES بدلاً من ADMIN_IDS)
        required_vars = ['BOT_TOKEN', 'PORT', 'WEBHOOK_URL', 'ADMIN_USERNAMES']
        
        for var in required_vars:
            if not getattr(Config, var, None):
                raise ValueError(f"المتغير {var} غير موجود في الإعدادات")
                
        # تحقق إضافي للتأكد من وجود مشرفين على الأقل
        if not Config.ADMIN_USERNAMES:
            raise ValueError("يجب تعيين أسماء المشرفين في ADMIN_USERNAMES")
            
        logger.info(f"✅ تم التحقق من الإعدادات بنجاح | المشرفون: {Config.ADMIN_USERNAMES}")
        
    except Exception as e:
        logger.critical(f"❌ فشل تهيئة النظام: {str(e)}")
        raise

def setup_all_handlers(application):
    """تسجيل جميع معالجات البوت"""
    setup_start_handlers(application)
    setup_admin_handlers(application)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(handle_callback, pattern="^(correct|rewrite|cancel_api|use_api)$"))
    application.add_handler(CallbackQueryHandler(verify_subscription_callback, pattern="^check_subscription$"))
    setup_premium(application)

def main():
    try:
        initialize_system()
        app = ApplicationBuilder().token(Config.BOT_TOKEN).build()
        
        setup_all_handlers(app)
        app.add_error_handler(error_handler)
        
        webhook_url = Config.WEBHOOK_URL.rstrip('/')
        port = int(Config.PORT)
        
        logger.info(f"🌐 جاري تشغيل البوت على الويب هوك (البورت: {port})")
        logger.info(f"🔗 رابط الويب هوك: {webhook_url}/{Config.BOT_TOKEN}")
        
        app.run_webhook(
            listen="0.0.0.0",
            port=port,
            webhook_url=f"{webhook_url}/{Config.BOT_TOKEN}",
            url_path=Config.BOT_TOKEN,
            drop_pending_updates=True
        )
            
    except Exception as e:
        logger.critical(f"🔥 تعطل البوت: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
