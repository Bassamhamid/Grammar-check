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
from handlers.start import start, handle_process_button
from handlers.text_handling import handle_message, handle_callback
from handlers.subscription import check_subscription, verify_subscription_callback
from handlers.premium import setup as setup_premium
import logging

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
        
        if not Config.BOT_TOKEN:
            raise ValueError("BOT_TOKEN مفقود")
        if not Config.FIREBASE_DB_URL:
            raise ValueError("FIREBASE_DB_URL مفقود")
            
        logger.info("✅ تم التحقق من الإعدادات بنجاح")
    except Exception as e:
        logger.critical(f"❌ فشل تهيئة النظام: {str(e)}")
        raise

def setup_handlers(application):
    """تسجيل جميع معالجات البوت"""
    # معالجات الأوامر
    application.add_handler(CommandHandler("start", start))
    
    # معالجات الرسائل
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # معالجات الأزرار
    application.add_handler(CallbackQueryHandler(handle_process_button, pattern="^start_processing$"))
    application.add_handler(CallbackQueryHandler(handle_callback, pattern="^(correct|rewrite|cancel_api|use_api)$"))
    application.add_handler(CallbackQueryHandler(verify_subscription_callback, pattern="^check_subscription$"))
    
    # معالجات API الشخصي
    setup_premium(application)

def main():
    try:
        initialize_system()
        app = ApplicationBuilder().token(Config.BOT_TOKEN).build()
        
        # تسجيل المعالجات
        setup_handlers(app)
        
        # معالج الأخطاء
        app.add_error_handler(error_handler)
        
        logger.info("🤖 جاري تشغيل البوت...")
        
        if Config.USE_WEBHOOK:
            app.run_webhook(
                listen="0.0.0.0",
                port=Config.PORT,
                url_path=Config.BOT_TOKEN,
                webhook_url=f"{Config.WEBHOOK_URL}/{Config.BOT_TOKEN}",
                drop_pending_updates=True
            )
        else:
            app.run_polling(drop_pending_updates=True)
            
    except Exception as e:
        logger.critical(f"🔥 تعطل البوت: {str(e)}")
        exit(1)

if __name__ == "__main__":
    main()
