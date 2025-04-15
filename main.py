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

# تهيئة نظام التسجيل
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
    """معالج الأخطاء العام للبوت"""
    logger.error(f"حدث خطأ: {context.error}", exc_info=True)
    if update and update.effective_message:
        await update.effective_message.reply_text("⚠️ حدث خطأ غير متوقع. يرجى المحاولة لاحقاً.")

def initialize_system():
    """تهيئة جميع أنظمة البوت"""
    try:
        # تهيئة Firebase
        initialize_firebase()
        logger.info("✅ تم تهيئة Firebase بنجاح")
        
        # التحقق من المتغيرات المطلوبة
        required_vars = [
            'BOT_TOKEN',
            'PORT',
            'WEBHOOK_URL',
            'ADMIN_USERNAMES',
            'FIREBASE_DATABASE_URL'
        ]
        
        missing_vars = [var for var in required_vars if not getattr(Config, var, None)]
        if missing_vars:
            raise ValueError(f"المتغيرات المفقودة: {', '.join(missing_vars)}")
            
        # تحقق من وجود مشرفين على الأقل
        if not Config.ADMIN_USERNAMES:
            raise ValueError("يجب تعيين أسماء المشرفين في ADMIN_USERNAMES")
            
        logger.info(f"✅ تم تهيئة النظام بنجاح | عدد المشرفين: {len(Config.ADMIN_USERNAMES)}")
        
    except Exception as e:
        logger.critical(f"❌ فشل تهيئة النظام: {str(e)}")
        raise

def setup_handlers(application):
    """تسجيل جميع معالجات البوت مع الفصل بين المشرفين والمستخدمين"""
    try:
        # فلتر المشرفين
        admin_filter = filters.ChatType.PRIVATE & filters.User(username=Config.ADMIN_USERNAMES)
        
        # فلتر المستخدمين العاديين
        user_filter = filters.ChatType.PRIVATE & ~admin_filter
        
        # 1. معالجات البدء والاشتراك
        setup_start_handlers(application)
        
        # 2. معالجات المشرفين (تطبق فقط على المشرفين)
        setup_admin_handlers(application)
        
        # 3. معالجات المستخدمين العاديين
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
        
        # 4. معالجات العضويات المميزة
        setup_premium(application)
        
        logger.info("✅ تم تسجيل جميع المعالجات بنجاح")
        
    except Exception as e:
        logger.error(f"فشل في تسجيل المعالجات: {str(e)}")
        raise

def run_bot():
    """تشغيل البوت في وضع الويب هوك"""
    try:
        # إنشاء تطبيق البوت
        app = ApplicationBuilder() \
            .token(Config.BOT_TOKEN) \
            .post_init(lambda app: logger.info("✅ تم تهيئة البوت بنجاح")) \
            .build()
        
        # تسجيل المعالجات
        setup_handlers(app)
        
        # تسجيل معالج الأخطاء
        app.add_error_handler(error_handler)
        
        # تهيئة الويب هوك
        webhook_url = f"{Config.WEBHOOK_URL.rstrip('/')}/{Config.BOT_TOKEN}"
        port = int(Config.PORT)
        
        logger.info(f"🌐 جاري التشغيل على البورت: {port}")
        logger.info(f"🔗 رابط الويب هوك: {webhook_url}")
        
        # تشغيل البوت
        app.run_webhook(
            listen="0.0.0.0",
            port=port,
            webhook_url=webhook_url,
            url_path=Config.BOT_TOKEN,
            drop_pending_updates=True
        )
        
    except Exception as e:
        logger.critical(f"🔥 تعطل البوت: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        initialize_system()
        run_bot()
    except Exception as e:
        logger.critical(f"🔥 فشل تشغيل البوت: {str(e)}")
        sys.exit(1)
