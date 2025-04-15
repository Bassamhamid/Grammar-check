import os
import json
from datetime import timedelta

class Config:
    # Telegram Bot Token
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    
    # OpenRouter API
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL = "meta-llama/llama-4-maverick:free"
    
    # Channel Configuration
    CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "")
    CHANNEL_LINK = os.getenv("CHANNEL_LINK", "")
    
    # Usage Limits
    CHAR_LIMIT = int(os.getenv("CHAR_LIMIT", "120"))
    PREMIUM_CHAR_LIMIT = int(os.getenv("PREMIUM_CHAR_LIMIT", "500"))
    REQUEST_LIMIT = int(os.getenv("REQUEST_LIMIT", "10"))
    PREMIUM_REQUEST_LIMIT = int(os.getenv("PREMIUM_REQUEST_LIMIT", "50"))
    RESET_HOURS = int(os.getenv("RESET_HOURS", "24"))
    PREMIUM_RESET_HOURS = int(os.getenv("PREMIUM_RESET_HOURS", "24"))
    
    # Webhook Settings
    WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
    PORT = int(os.getenv("PORT", "10000"))
    
    # App Info
    SITE_URL = os.getenv("SITE_URL", "")
    SITE_TITLE = os.getenv("SITE_TITLE", "Arabic Text Correction Bot")

    # Firebase Configuration
    FIREBASE_DB_URL = os.getenv("FIREBASE_DATABASE_URL", "")
    FIREBASE_SERVICE_ACCOUNT = None
    
    try:
        service_account_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "")
        if service_account_json:
            FIREBASE_SERVICE_ACCOUNT = json.loads(service_account_json)
    except Exception as e:
        print(f"Error parsing FIREBASE_SERVICE_ACCOUNT_JSON: {e}")

    # Timeout Settings
    REQUEST_TIMEOUT = timedelta(seconds=30)

    # Admin Settings
    @staticmethod
    def get_admin_usernames():
        admins = os.getenv("ADMIN_USERNAMES", "").strip()
        if not admins:
            raise ValueError("ADMIN_USERNAMES not set in environment variables")
        
        try:
            return [username.strip().lower().replace('@', '') 
                   for username in admins.split(',') 
                   if username.strip()]
        except Exception as e:
            print(f"Error parsing ADMIN_USERNAMES: {e}")
            return []

    ADMIN_USERNAMES = get_admin_usernames()
    MAX_BROADCAST_USERS = int(os.getenv("MAX_BROADCAST_USERS", "1000"))
    BACKUP_DIR = os.getenv("BACKUP_DIR", "backups")

    # System Validation
    @classmethod
    def validate_config(cls):
        required = {
            'BOT_TOKEN': 'Telegram Bot Token',
            'FIREBASE_DATABASE_URL': 'Firebase Database URL',
            'ADMIN_USERNAMES': 'Admin Usernames',
            'WEBHOOK_URL': 'Webhook URL'
        }
        
        missing = []
        for var, desc in required.items():
            if not getattr(cls, var):
                missing.append(f"{var} ({desc})")
        
        if missing:
            raise ValueError(f"Missing required configs:\n- " + "\n- ".join(missing))
