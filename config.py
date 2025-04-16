import os
import json
from datetime import timedelta
import logging

class Config:
    ##############################################
    #               إعدادات البوت                #
    ##############################################
    
    # Telegram Bot Token
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    
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
    
    FIREBASE_DATABASE_URL = os.getenv("FIREBASE_DATABASE_URL", "").strip()
    FIREBASE_SERVICE_ACCOUNT = None
    
    try:
        service_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "")
        if service_json.strip():
            FIREBASE_SERVICE_ACCOUNT = json.loads(service_json)
    except json.JSONDecodeError as e:
        logging.error(f"Error parsing FIREBASE_SERVICE_ACCOUNT_JSON: {str(e)}")
    except Exception as e:
        logging.error(f"Error loading Firebase config: {str(e)}")

    # إعدادات الأداء
    REQUEST_TIMEOUT = timedelta(seconds=30)
    FIREBASE_CACHE_TTL = int(os.getenv("FIREBASE_CACHE_TTL", "300"))  # 5 دقائق

    ##############################################
    #            إعدادات المشرفين                #
    ##############################################
    
    @staticmethod
    def get_admin_usernames():
        """استخراج أسماء المشرفين من متغير البيئة"""
        admins = os.getenv("ADMIN_USERNAMES", "").strip()
        if not admins:
            raise ValueError("ADMIN_USERNAMES environment variable is required")
        
        try:
            return [
                username.strip().lower().replace('@', '')
                for username in admins.split(',')
                if username.strip()
            ]
        except Exception as e:
            logging.error(f"Error processing admin usernames: {str(e)}")
            return []

    ADMIN_USERNAMES = get_admin_usernames()
    MAX_BROADCAST_USERS = int(os.getenv("MAX_BROADCAST_USERS", "1000"))
    BROADCAST_DELAY = float(os.getenv("BROADCAST_DELAY", "0.3"))  # تأخير بين كل إرسال
    BACKUP_DIR = os.getenv("BACKUP_DIR", "backups")
    LOGS_RETENTION_DAYS = int(os.getenv("LOGS_RETENTION_DAYS", "30"))

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
        """التحقق من وجود جميع المتغيرات المطلوبة"""
        required_configs = {
            'BOT_TOKEN': 'توكن بوت التليجرام',
            'FIREBASE_DATABASE_URL': 'رابط قاعدة بيانات Firebase',
            'ADMIN_USERNAMES': 'قائمة أسماء المشرفين',
            'WEBHOOK_URL': 'رابط الويب هوك',
            'FIREBASE_SERVICE_ACCOUNT': 'بيانات اعتماد Firebase'
        }
        
        missing = []
        for var, desc in required_configs.items():
            if not getattr(cls, var):
                missing.append(f"{var} ({desc})")
        
        if missing:
            error_msg = "المتغيرات المطلوبة مفقودة:\n- " + "\n- ".join(missing)
            error_msg += "\n\nيرجى تعيينها في متغيرات البيئة"
            logging.critical(error_msg)
            raise ValueError(error_msg)

        # تحقق إضافي لبيانات Firebase
        if not cls.FIREBASE_SERVICE_ACCOUNT:
            logging.critical("Firebase service account configuration is invalid")
            raise ValueError("Invalid Firebase service account configuration")

# التحقق التلقائي عند الاستيراد
try:
    # تكوين نظام التسجيل أولاً
    logging.basicConfig(
        level=Config.LOG_LEVEL,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    Config.validate_config()
    logging.info("✅ تم تحميل الإعدادات بنجاح")
except Exception as e:
    logging.critical(f"❌ فشل تحميل الإعدادات: {str(e)}")
    raise
