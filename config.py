import os
import json
from datetime import timedelta

class Config:
    # Telegram
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    
    # Firebase
    FIREBASE_DATABASE_URL = os.getenv("FIREBASE_DATABASE_URL", "")
    FIREBASE_SERVICE_ACCOUNT = None
    
    try:
        if service_json := os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON"):
            FIREBASE_SERVICE_ACCOUNT = json.loads(service_json)
    except json.JSONDecodeError as e:
        print(f"Invalid FIREBASE_SERVICE_ACCOUNT_JSON: {e}")

    # Webhook
    WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
    PORT = int(os.getenv("PORT", "10000"))

    # Admin
    @staticmethod
    def get_admin_usernames():
        admins = os.getenv("ADMIN_USERNAMES", "").strip()
        return [u.strip().lower().replace('@', '') for u in admins.split(',') if u] if admins else []

    ADMIN_USERNAMES = get_admin_usernames()

    # Validation
    @classmethod
    def validate_config(cls):  # تم تغيير الاسم من validate إلى validate_config
        required = {
            'BOT_TOKEN': 'Telegram Bot Token',
            'FIREBASE_DATABASE_URL': 'Firebase Database URL',
            'ADMIN_USERNAMES': 'Admin Usernames',
            'WEBHOOK_URL': 'Webhook URL'
        }
        
        missing = [f"{var} ({desc})" for var, desc in required.items() if not getattr(cls, var)]
        if missing:
            raise ValueError(f"Missing required configs: {', '.join(missing)}")

# التحقق التلقائي عند الاستيراد
try:
    Config.validate_config()
except Exception as e:
    print(f"Config Validation Error: {e}")
