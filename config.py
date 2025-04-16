import os
import json
from datetime import timedelta
import logging

class Config:
    ##############################################
    #               إعدادات البوت                #
    ##############################################
    
    # Telegram Bot Token (مطلوب)
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    if not BOT_TOKEN:
        raise ValueError("يجب تعيين متغير BOT_TOKEN في إعدادات Render")
    
    # Webhook URL (مطلوب)
    WEBHOOK_URL = os.getenv("WEBHOOK_URL")
    if not WEBHOOK_URL:
        raise ValueError("يجب تعيين متغير WEBHOOK_URL في إعدادات Render")
    
    # Port (مطلوب من Render)
    PORT = int(os.getenv("PORT", "10000"))  # default لو مش متعين

    # اسم قناة العرض (مطلوب)
    CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
    if not CHANNEL_USERNAME:
        raise ValueError("يجب تعيين متغير CHANNEL_USERNAME في إعدادات Render")

    ##############################################
    #            إعدادات Firebase (مطلوبة)       #
    ##############################################
    
    FIREBASE_DATABASE_URL = os.getenv("FIREBASE_DATABASE_URL")
    if not FIREBASE_DATABASE_URL:
        raise ValueError("يجب تعيين متغير FIREBASE_DATABASE_URL في إعدادات Render")
    
    FIREBASE_SERVICE_ACCOUNT = None
    try:
        service_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
        if service_json:
            FIREBASE_SERVICE_ACCOUNT = json.loads(service_json)
    except Exception as e:
        logging.error(f"خطأ في تحليل بيانات Firebase: {str(e)}")
        raise ValueError("تكوين Firebase غير صالح")

    ##############################################
    #             حدود الاستخدام                 #
    ##############################################
    
    CHAR_LIMIT = int(os.getenv("CHAR_LIMIT", "120"))
    PREMIUM_CHAR_LIMIT = int(os.getenv("PREMIUM_CHAR_LIMIT", "500"))
    
    REQUEST_LIMIT = int(os.getenv("REQUEST_LIMIT", "10"))
    PREMIUM_REQUEST_LIMIT = int(os.getenv("PREMIUM_REQUEST_LIMIT", "50"))
    
    RESET_HOURS = int(os.getenv("RESET_HOURS", "24"))

    ##############################################
    #            إعدادات المشرفين                #
    ##############################################
    
    @staticmethod
    def get_admin_usernames():
        admins = os.getenv("ADMIN_USERNAMES", "").strip()
        if not admins:
            raise ValueError("يجب تعيين متغير ADMIN_USERNAMES في إعدادات Render")
        return [username.strip().lower().replace('@', '') for username in admins.split(',') if username.strip()]

    ADMIN_USERNAMES = get_admin_usernames()

    ##############################################
    #              إعدادات التصحيح               #
    ##############################################
    
    DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    ##############################################
    #              التحقق من الإعدادات           #
    ##############################################
    
    @classmethod
    def validate_config(cls):
        required_vars = {
            'BOT_TOKEN': 'توكن البوت',
            'WEBHOOK_URL': 'رابط Webhook',
            'PORT': 'منفذ التشغيل',
            'FIREBASE_DATABASE_URL': 'رابط قاعدة بيانات Firebase',
            'FIREBASE_SERVICE_ACCOUNT': 'بيانات اعتماد Firebase',
            'ADMIN_USERNAMES': 'قائمة المشرفين',
            'CHANNEL_USERNAME': 'اسم قناة العرض'
        }

        missing = []
        for var, desc in required_vars.items():
            if getattr(cls, var, None) is None:
                missing.append(f"{var} ({desc})")
        
        if missing:
            error_msg = "المتغيرات المطلوبة مفقودة في إعدادات Render:\n- " + "\n- ".join(missing)
            logging.critical(error_msg)
            raise ValueError(error_msg)

# التحقق التلقائي عند الاستيراد
try:
    logging.basicConfig(
        level=Config.LOG_LEVEL,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    Config.validate_config()
    logging.info("✅ تم تحميل الإعدادات بنجاح من متغيرات Render")
except Exception as e:
    logging.critical(f"❌ فشل تحميل الإعدادات: {str(e)}")
    raise
