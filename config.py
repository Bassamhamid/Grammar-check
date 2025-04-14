import os
import json

class Config:
    # Telegram Bot Token
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    
    # OpenRouter API
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    OPENROUTER_MODEL = "meta-llama/llama-4-maverick:free"
    
    # Channel Configuration
    CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")  # بدون @
    CHANNEL_LINK = os.getenv("CHANNEL_LINK")         # رابط القناة
    
    # Usage Limits
    CHAR_LIMIT = 120                  # الحد الأساسي للأحرف
    PREMIUM_CHAR_LIMIT = 500          # حد الأحرف لمستخدمي API الشخصي
    REQUEST_LIMIT = 3                 # الحد الأساسي للطلبات
    PREMIUM_REQUEST_LIMIT = 50        # حد الطلبات لمستخدمي API الشخصي
    RESET_HOURS = 20                  # مدة تجديد الطلبات العادية
    PREMIUM_RESET_HOURS = 24          # مدة تجديد طلبات API الشخصي
    
    # Webhook
    WEBHOOK_URL = os.getenv("WEBHOOK_URL")
    PORT = int(os.environ.get("PORT", "10000"))
    
    # App Info
    SITE_URL = os.getenv("SITE_URL", "")
    SITE_TITLE = os.getenv("SITE_TITLE", "Arabic Text Bot")

    # Firebase Configuration
    FIREBASE_DB_URL = os.getenv("FIREBASE_DATABASE_URL")
    FIREBASE_SERVICE_ACCOUNT = json.loads(os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "{}")) if os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON") else None
