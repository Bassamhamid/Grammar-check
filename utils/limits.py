from firebase_db import FirebaseDB
from config import Config
import time

class UsageLimiter:
    def __init__(self):
        try:
            self.db = FirebaseDB()
            self.CHAR_LIMIT = Config.CHAR_LIMIT
            self.REQUEST_LIMIT = Config.REQUEST_LIMIT
            self.RESET_HOURS = Config.RESET_HOURS
        except Exception as e:
            raise RuntimeError(f"Failed to initialize UsageLimiter: {str(e)}")

    # ... (باقي الدوال تبقى كما هي)

# التهيئة المؤجلة
limiter = None
try:
    limiter = UsageLimiter()
except Exception as e:
    print(f"⚠️ Warning: Failed to initialize limiter: {str(e)}")
    # يمكنك إضافة نظام بديل هنا إذا لزم الأمر
