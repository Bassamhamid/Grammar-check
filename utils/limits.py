import time
from config import Config
from firebase_db import FirebaseDB
import logging

logger = logging.getLogger(__name__)

class UsageLimiter:
    def __init__(self):
        self.db = FirebaseDB()
        self.CHAR_LIMIT = Config.CHAR_LIMIT
        self.REQUEST_LIMIT = Config.REQUEST_LIMIT
        self.RESET_HOURS = Config.RESET_HOURS

    def check_limits(self, user_id: int) -> tuple:
        try:
            user_data = self.db.get_user(user_id)
            current_time = time.time()
            
            # ضبط القيم الافتراضية إذا كانت غير موجودة
            reset_time = user_data.get('reset_time') or (current_time + (self.RESET_HOURS * 3600))
            request_count = user_data.get('request_count', 0)
            
            # إذا انتهت المدة، إعادة تعيين العداد
            if current_time > reset_time:
                self.db.update_user(user_id, {
                    'request_count': 0,
                    'reset_time': current_time + (self.RESET_HOURS * 3600)
                })
                return True, 0
            
            remaining = self.REQUEST_LIMIT - request_count
            time_left = max(0, reset_time - current_time)
            return remaining > 0, time_left
            
        except Exception as e:
            logger.error(f"Error in check_limits: {str(e)}", exc_info=True)
            # القيم الافتراضية في حالة الخطأ
            return True, 0

    def increment_usage(self, user_id: int):
        try:
            user_data = self.db.get_user(user_id)
            current_time = time.time()
            
            # القيم الافتراضية إذا كانت غير موجودة
            reset_time = user_data.get('reset_time') or (current_time + (self.RESET_HOURS * 3600))
            request_count = user_data.get('request_count', 0)
            
            # إذا انتهت المدة، إعادة تعيين العداد
            if current_time > reset_time:
                reset_time = current_time + (self.RESET_HOURS * 3600)
                request_count = 0
            
            self.db.update_user(user_id, {
                'request_count': request_count + 1,
                'last_request': int(current_time),
                'reset_time': reset_time
            })
            
        except Exception as e:
            logger.error(f"Error in increment_usage: {str(e)}", exc_info=True)
            raise

limiter = UsageLimiter()
