import time
from config import Config
from firebase_db import FirebaseDB
import logging

logger = logging.getLogger(__name__)

class UsageLimiter:
    def __init__(self):
        self.db = FirebaseDB()
        self.premium_users = {}  # لتخزين مستخدمي API الشخصي

    def check_limits(self, user_id: int) -> tuple:
        try:
            is_premium = user_id in self.premium_users
            user_data = self.db.get_user(user_id)
            current_time = time.time()
            
            # تحديد الحدود حسب نوع المستخدم
            char_limit = Config.PREMIUM_CHAR_LIMIT if is_premium else Config.CHAR_LIMIT
            request_limit = Config.PREMIUM_REQUEST_LIMIT if is_premium else Config.REQUEST_LIMIT
            reset_hours = Config.PREMIUM_RESET_HOURS if is_premium else Config.RESET_HOURS
            
            # ضبط القيم الافتراضية
            reset_time = user_data.get('reset_time') or (current_time + (reset_hours * 3600))
            request_count = user_data.get('request_count', 0)
            
            # إعادة تعيين العداد إذا انتهت المدة
            if current_time > reset_time:
                self.db.update_user(user_id, {
                    'request_count': 0,
                    'reset_time': current_time + (reset_hours * 3600),
                    'is_premium': is_premium
                })
                return True, 0, char_limit
            
            remaining = request_limit - request_count
            time_left = max(0, reset_time - current_time)
            return remaining > 0, time_left, char_limit
            
        except Exception as e:
            logger.error(f"Error in check_limits: {str(e)}", exc_info=True)
            return True, 0, Config.CHAR_LIMIT

    def increment_usage(self, user_id: int):
        try:
            is_premium = user_id in self.premium_users
            reset_hours = Config.PREMIUM_RESET_HOURS if is_premium else Config.RESET_HOURS
            
            user_data = self.db.get_user(user_id)
            current_time = time.time()
            reset_time = user_data.get('reset_time') or (current_time + (reset_hours * 3600))
            request_count = user_data.get('request_count', 0)
            
            if current_time > reset_time:
                reset_time = current_time + (reset_hours * 3600)
                request_count = 0
            
            self.db.update_user(user_id, {
                'request_count': request_count + 1,
                'last_request': int(current_time),
                'reset_time': reset_time,
                'is_premium': is_premium
            })
            
        except Exception as e:
            logger.error(f"Error in increment_usage: {str(e)}", exc_info=True)
            raise

    def set_premium_user(self, user_id: int, api_key: str):
        self.premium_users[user_id] = {
            'api_key': api_key,
            'count': 0,
            'reset_time': time.time() + (Config.PREMIUM_RESET_HOURS * 3600)
        }

    def is_premium_user(self, user_id: int) -> bool:
        return user_id in self.premium_users

limiter = UsageLimiter()
