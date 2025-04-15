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
    CHANNEL_LINK = os.getenv("CHANNEL_LINK", "https://t.me/your_channel")
    
    # Usage Limits
    CHAR_LIMIT = int(os.getenv("CHAR_LIMIT", "120"))
    PREMIUM_CHAR_LIMIT = int(os.getenv("PREMIUM_CHAR_LIMIT", "500"))
    REQUEST_LIMIT = int(os.getenv("REQUEST_LIMIT", "10"))
    PREMIUM_REQUEST_LIMIT = int(os.getenv("PREMIUM_REQUEST_LIMIT", "50"))
    RESET_HOURS = int(os.getenv("RESET_HOURS", "24"))
    PREMIUM_RESET_HOURS = int(os.getenv("PREMIUM_RESET_HOURS", "24"))
    
    # Webhook
    WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://your-render-app.onrender.com")
    PORT = int(os.getenv("PORT", "10000"))
    
    # App Info
    SITE_URL = os.getenv("SITE_URL", "https://your-website.com")
    SITE_TITLE = os.getenv("SITE_TITLE", "Arabic Text Correction Bot")

    # Firebase Configuration
    FIREBASE_DB_URL = os.getenv("FIREBASE_DATABASE_URL", "https://your-project.firebaseio.com")
    FIREBASE_SERVICE_ACCOUNT = json.loads(os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "{}")) if os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON") else None

    # Timeout Settings
    REQUEST_TIMEOUT = timedelta(seconds=30)

    # Admin Settings - تم التعديل هنا لاستخدام usernames بدلاً من IDs
    @staticmethod
    def get_admin_usernames():
        admins = os.getenv("ADMIN_USERNAMES", "").strip()
        if not admins:
            return []
        
        try:
            # تقسيم الأسماء بفاصلة وإزالة أي مسافات أو @
            return [username.strip().lower().replace('@', '') 
                   for username in admins.split(',') 
                   if username.strip()]
        except Exception as e:
            print(f"Error parsing ADMIN_USERNAMES: {e}")
            return []

    ADMIN_USERNAMES = get_admin_usernames()
    MAX_BROADCAST_USERS = int(os.getenv("MAX_BROADCAST_USERS", "1000"))
    BACKUP_DIR = os.getenv("BACKUP_DIR", "backups")
