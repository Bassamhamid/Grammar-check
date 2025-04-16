import os
import json
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

    CHAR_LIMIT = int(os.getenv("CHAR_LIMIT", "120"))               # حد الحروف العادي
    PREMIUM_CHAR_LIMIT = int(os.getenv("PREMIUM_CHAR_LIMIT", "500"))  # حد الحروف المميز

    REQUEST_LIMIT = int(os.getenv("REQUEST_LIMIT", "10"))            # حد الطلبات العادي
    PREMIUM_REQUEST_LIMIT = int(os.getenv("PREMIUM_REQUEST_LIMIT", "50"))  # حد الطلبات المميز

    RESET_HOURS = int(os.getenv("RESET_HOURS", "24"))               # وقت تجديد العداد

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

    ADMIN_USERNAMES = get_admin_usernames.__func__()

    ##############################################
    #               إعدادات السيرفر              #
    ##############################################

    PORT = int(os.getenv("PORT", "10000"))  # Render سيرفر يحدد البورت وقت التشغيل

    @staticmethod
    def validate_config():
        """دالة للتحقق من صحة الإعدادات"""
        if not Config.BOT_TOKEN:
            raise ValueError("يجب تعيين متغير BOT_TOKEN")
        if not Config.WEBHOOK_URL:
            raise ValueError("يجب تعيين متغير WEBHOOK_URL")
        if not Config.FIREBASE_DATABASE_URL:
            raise ValueError("يجب تعيين متغير FIREBASE_DATABASE_URL")
        if not Config.ADMIN_USERNAMES:
            raise ValueError("يجب تعيين متغير ADMIN_USERNAMES")

        logging.info("✅ جميع الإعدادات تم التحقق منها بنجاح")
