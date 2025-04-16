import os
import json
from datetime import timedelta
import logging

class Config:
    ##############################################
    #               إعدادات البوت                #
    ##############################################
    
    # Telegram Bot Token
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    if not BOT_TOKEN:
        raise ValueError("يجب تعيين متغير BOT_TOKEN في إعدادات Render")
    
    # OpenRouter API
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-4-maverick:free")
    
    ##############################################
    #              إعدادات القناة                #
    ##############################################
    
    CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "").strip()
    CHANNEL_LINK = os.getenv("CHANNEL_LINK", "").strip()
    CHANNEL_REQUIRED = os.getenv("CHANNEL_REQUIRED", "true").lower() == "true"
    
    ##############################################
    #             حدود الاستخدام                 #
    ##############################################
    
    # حدود النصوص
    CHAR_LIMIT = int(os.getenv("CHAR_LIMIT", "120"))
    PREMIUM_CHAR_LIMIT = int(os.getenv("PREMIUM_CHAR_LIMIT", "500"))
    
    # حدود الطلبات
    REQUEST_LIMIT = int(os.getenv("REQUEST_LIMIT", "10"))
    PREMIUM_REQUEST_LIMIT = int(os.getenv("PREMIUM_REQUEST_LIMIT", "50"))
    
    # توقيت إعادة التعيين
    RESET_HOURS = int(os.getenv("RESET_HOURS", "24"))
    PREMIUM_RESET_HOURS = int(os.getenv("PREMIUM_RESET_HOURS", "24"))
    
    ##############################################
    #             إعدادات الويب هوك              #
    ##############################################
    
    WEBHOOK_URL = os.getenv("WEBHOOK_URL", "").strip("/")
    PORT = int(os.getenv("PORT", "10000"))
    WEBAPP_HOST = os.getenv("WEBAPP_HOST", "0.0.0.0")
    
    ##############################################
    #              معلومات التطبيق               #
    ##############################################
    
    SITE_URL = os.getenv("SITE_URL", "").strip("/")
    SITE_TITLE = os.getenv("SITE_TITLE", "Arabic Text Correction Bot")
    VERSION = os.getenv("VERSION", "1.0.0")

    ##############################################
    #            إعدادات Firebase               #
    ##############################################
    
    FIREBASE_DATABASE_URL = os.getenv("FIREBASE_DATABASE_URL")
    if not FIREBASE_DATABASE_URL:
        raise ValueError("يجب تعيين متغير FIREBASE_DATABASE_URL في إعدادات Render")
    
    FIREBASE_SERVICE_ACCOUNT = None
    
    try:
        # قراءة بيانات Firebase من متغيرات Render مباشرة
        firebase_config = {
            "type": os.getenv("FIREBASE_TYPE"),
            "project_id": os.getenv("FIREBASE_PROJECT_ID"),
            "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
            "private_key": os.getenv("FIREBASE_PRIVATE_KEY").replace('\\n', '\n'),
            "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
            "client_id": os.getenv("FIREBASE_CLIENT_ID"),
            "auth_uri": os.getenv("FIREBASE_AUTH_URI"),
            "token_uri": os.getenv("FIREBASE_TOKEN_URI"),
            "auth_provider_x509_cert_url": os.getenv("FIREBASE_AUTH_PROVIDER_CERT_URL"),
            "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_CERT_URL")
        }
        
        FIREBASE_SERVICE_ACCOUNT = firebase_config
    except Exception as e:
        logging.error(f"فشل تحميل إعدادات Firebase: {str(e)}")
        raise ValueError("إعدادات Firebase غير صالحة في متغيرات Render")

    # إعدادات الأداء
    REQUEST_TIMEOUT = timedelta(seconds=int(os.getenv("REQUEST_TIMEOUT_SECONDS", "30")))
    FIREBASE_CACHE_TTL = int(os.getenv("FIREBASE_CACHE_TTL", "300"))  # 5 دقائق

    ##############################################
    #            إعدادات المشرفين                #
    ##############################################
    
    @staticmethod
    def get_admin_usernames():
        """استخراج أسماء المشرفين من متغيرات Render"""
        admins = os.getenv("ADMIN_USERNAMES", "").strip()
        if not admins:
            raise ValueError("يجب تعيين متغير ADMIN_USERNAMES في إعدادات Render")
        
        return [username.strip().lower().replace('@', '') for username in admins.split(',') if username.strip()]

    ADMIN_USERNAMES = get_admin_usernames()
    MAX_BROADCAST_USERS = int(os.getenv("MAX_BROADCAST_USERS", "1000"))
    BROADCAST_DELAY = float(os.getenv("BROADCAST_DELAY_SECONDS", "0.3"))
    ADMIN_LOG_CHAT_ID = os.getenv("ADMIN_LOG_CHAT_ID", "")
    ERROR_REPORTING_CHAT_ID = os.getenv("ERROR_REPORTING_CHAT_ID", "")

    ##############################################
    #              إعدادات التصحيح               #
    ##############################################
    
    DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    ##############################################
    #            إعدادات لوحة التحكم             #
    ##############################################
    
    ADMIN_PANEL_REFRESH_INTERVAL = int(os.getenv("ADMIN_PANEL_REFRESH_SECONDS", "300"))
    STATS_AUTO_RESET_TIME = os.getenv("STATS_AUTO_RESET_TIME", "00:00")
    MAINTENANCE_MESSAGE = os.getenv("MAINTENANCE_MESSAGE", "البوت في وضع الصيانة حالياً، الرجاء المحاولة لاحقاً")

    ##############################################
    #              التحقق من الإعدادات           #
    ##############################################
    
    @classmethod
    def validate_config(cls):
        """التحقق من صحة الإعدادات"""
        required_vars = {
            'BOT_TOKEN': 'توكن البوت',
            'FIREBASE_DATABASE_URL': 'رابط قاعدة بيانات Firebase',
            'ADMIN_USERNAMES': 'قائمة المشرفين'
        }
        
        missing = []
        for var, desc in required_vars.items():
            if not getattr(cls, var):
                missing.append(f"{var} ({desc})")
        
        if missing:
            error_msg = "المتغيرات المطلوبة مفقودة في إعدادات Render:\n- " + "\n- ".join(missing)
            logging.critical(error_msg)
            raise ValueError(error_msg)

        # تحقق من صحة توقيت إعادة التعيين
        try:
            if cls.STATS_AUTO_RESET_TIME:
                hours, minutes = map(int, cls.STATS_AUTO_RESET_TIME.split(':'))
                if not (0 <= hours < 24 and 0 <= minutes < 60):
                    raise ValueError
        except:
            logging.warning("تنسيق وقت إعادة التعيين غير صالح، سيتم استخدام 00:00")
            cls.STATS_AUTO_RESET_TIME = "00:00"

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
