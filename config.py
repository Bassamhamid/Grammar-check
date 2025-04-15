import os
import json
from datetime import timedelta

class Config:
    ##############################################
    #               إعدادات البوت                #
    ##############################################
    
    # Telegram Bot Token
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    
    # OpenRouter API
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL = "meta-llama/llama-4-maverick:free"
    
    ##############################################
    #              إعدادات القناة                #
    ##############################################
    
    CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "").strip()
    CHANNEL_LINK = os.getenv("CHANNEL_LINK", "").strip()
    
    ##############################################
    #             حدود الاستخدام                 #
    ##############################################
    
    CHAR_LIMIT = int(os.getenv("CHAR_LIMIT", "120"))
    PREMIUM_CHAR_LIMIT = int(os.getenv("PREMIUM_CHAR_LIMIT", "500"))
    REQUEST_LIMIT = int(os.getenv("REQUEST_LIMIT", "10"))
    PREMIUM_REQUEST_LIMIT = int(os.getenv("PREMIUM_REQUEST_LIMIT", "50"))
    RESET_HOURS = int(os.getenv("RESET_HOURS", "24"))
    PREMIUM_RESET_HOURS = int(os.getenv("PREMIUM_RESET_HOURS", "24"))
    
    ##############################################
    #             إعدادات الويب هوك              #
    ##############################################
    
    WEBHOOK_URL = os.getenv("WEBHOOK_URL", "").strip("/")
    PORT = int(os.getenv("PORT", "10000"))
    
    ##############################################
    #              معلومات التطبيق               #
    ##############################################
    
    SITE_URL = os.getenv("SITE_URL", "").strip("/")
    SITE_TITLE = os.getenv("SITE_TITLE", "Arabic Text Correction Bot")

    ##############################################
    #            إعدادات Firebase               #
    ##############################################
    
    # التصحيح النهائي: توحيد اسم المتغير
    FIREBASE_DATABASE_URL = os.getenv("FIREBASE_DATABASE_URL", "").strip()
    FIREBASE_SERVICE_ACCOUNT = None
    
    try:
        service_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "")
        if service_json.strip():
            FIREBASE_SERVICE_ACCOUNT = json.loads(service_json)
    except json.JSONDecodeError as e:
        print(f"❌ خطأ في تحليل FIREBASE_SERVICE_ACCOUNT_JSON: {str(e)}")
    except Exception as e:
        print(f"❌ خطأ غير متوقع في تحميل إعدادات Firebase: {str(e)}")

    REQUEST_TIMEOUT = timedelta(seconds=30)

    ##############################################
    #            إعدادات المشرفين                #
    ##############################################
    
    @staticmethod
    def get_admin_usernames():
        """استخراج أسماء المشرفين من متغير البيئة"""
        admins = os.getenv("ADMIN_USERNAMES", "").strip()
        if not admins:
            raise ValueError("يجب تعيين ADMIN_USERNAMES في متغيرات البيئة")
        
        try:
            return [
                username.strip().lower().replace('@', '')
                for username in admins.split(',')
                if username.strip()
            ]
        except Exception as e:
            print(f"❌ خطأ في معالجة أسماء المشرفين: {str(e)}")
            return []

    ADMIN_USERNAMES = get_admin_usernames()
    MAX_BROADCAST_USERS = int(os.getenv("MAX_BROADCAST_USERS", "1000"))
    BACKUP_DIR = os.getenv("BACKUP_DIR", "backups")

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
            'WEBHOOK_URL': 'رابط الويب هوك'
        }
        
        missing = []
        for var, desc in required_configs.items():
            if not getattr(cls, var):
                missing.append(f"{var} ({desc})")
        
        if missing:
            raise ValueError(
                "المتغيرات المطلوبة مفقودة:\n- " + 
                "\n- ".join(missing) +
                "\n\nيرجى تعيينها في متغيرات البيئة على Render"
            )

# التحقق التلقائي عند الاستيراد
try:
    Config.validate_config()
    print("✅ تم التحقق من الإعدادات بنجاح")
except Exception as e:
    print(f"❌ خطأ في إعدادات التطبيق: {str(e)}")
    raise
