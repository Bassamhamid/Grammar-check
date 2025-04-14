import time
from config import Config
from firebase_db import FirebaseDB
import logging

class UsageLimiter:
    def __init__(self):
        try:
            self.db = FirebaseDB()
            self.CHAR_LIMIT = Config.CHAR_LIMIT
            self.REQUEST_LIMIT = Config.REQUEST_LIMIT
            self.RESET_HOURS = Config.RESET_HOURS
            logging.info("✅ UsageLimiter initialized successfully")
        except Exception as e:
            logging.error(f"🔥 Failed to initialize UsageLimiter: {str(e)}")
            raise

    def check_limits(self, user_id: int) -> tuple:
        try:
            user = self.db.get_user(user_id)
            current_time = time.time()
            
            if user.get('reset_time') and current_time > user['reset_time']:
                self.db.update_user(user_id, {
                    'request_count': 0,
                    'reset_time': current_time + (self.RESET_HOURS * 3600)
                })
                return True, 0
            
            remaining = self.REQUEST_LIMIT - user.get('request_count', 0)
            time_left = max(0, (user.get('reset_time', 0) - current_time))
            return remaining > 0, time_left
        except Exception as e:
            logging.error(f"🚨 Error in check_limits: {str(e)}")
            return False, 0

    def increment_usage(self, user_id: int):
        try:
            user = self.db.get_user(user_id)
            new_count = user.get('request_count', 0) + 1
            update_data = {
                'request_count': new_count,
                'last_request': int(time.time())
            }
            
            if not user.get('reset_time'):
                update_data['reset_time'] = time.time() + (self.RESET_HOURS * 3600)
            
            self.db.update_user(user_id, update_data)
        except Exception as e:
            logging.error(f"🚨 Error in increment_usage: {str(e)}")
            raise

# التهيئة مع التعامل مع الأخطاء
try:
    limiter = UsageLimiter()
except Exception as e:
    print(f"⚠️ Critical: Failed to initialize limiter - {str(e)}")
    exit(1)
