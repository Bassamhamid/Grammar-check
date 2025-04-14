import os
import json
from datetime import timedelta

class Config:
    # Telegram Bot Token
    BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_DEFAULT_BOT_TOKEN")
    
    # OpenRouter API
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "default_api_key")
    OPENROUTER_MODEL = "meta-llama/llama-4-maverick:free"
    
    # Channel Configuration
    CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "your_channel")  # بدون @
    CHANNEL_LINK = os.getenv("CHANNEL_LINK", "https://t.me/your_channel")  # رابط القناة
    
    # Usage Limits
    CHAR_LIMIT = int(os.getenv("CHAR_LIMIT", "120"))
    PREMIUM_CHAR_LIMIT = int(os.getenv("PREMIUM_CHAR_LIMIT", "500"))
    REQUEST_LIMIT = int(os.getenv("REQUEST_LIMIT", "3"))
    PREMIUM_REQUEST_LIMIT = int(os.getenv("PREMIUM_REQUEST_LIMIT", "50"))
    RESET_HOURS = int(os.getenv("RESET_HOURS", "20"))
    PREMIUM_RESET_HOURS = int(os.getenv("PREMIUM_RESET_HOURS", "24"))
    
    # Webhook
    WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://your-render-app.onrender.com")
    PORT = int(os.getenv("PORT", "10000"))
    
    # App Info
    SITE_URL = os.getenv("SITE_URL", "")
    SITE_TITLE = os.getenv("SITE_TITLE", "Arabic Text Bot")

    # Firebase Configuration
    FIREBASE_DB_URL = os.getenv("FIREBASE_DATABASE_URL", "https://your-project.firebaseio.com")
    FIREBASE_SERVICE_ACCOUNT = json.loads(os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "{}")) if os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON") else None

    # Timeout Settings
    REQUEST_TIMEOUT = timedelta(seconds=30)

    # Admin Settings - الطريقة الصحيحة
    @staticmethod
    def get_admin_ids():
        admin_ids = os.getenv("ADMIN_IDS", "").strip()
        if not admin_ids:
            return []
        
        try:
            return [int(id.strip()) for id in admin_ids.split(',') if id.strip().isdigit()]
        except Exception as e:
            print(f"Error parsing ADMIN_IDS: {e}")
            return []

    ADMIN_IDS = [int(id) for id in os.getenv("ADMIN_IDS", "123456789").split(',') if id.strip().isdigit()]
    MAX_BROADCAST_USERS = int(os.getenv("MAX_BROADCAST_USERS", "1000"))
    BACKUP_DIR = os.getenv("BACKUP_DIR", "backups")
