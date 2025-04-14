import time
from config import Config
from firebase_db import FirebaseDB  # تأكد من وجود هذا الملف

class UsageLimiter:
    def __init__(self):
        self.db = FirebaseDB()
        self.CHAR_LIMIT = Config.CHAR_LIMIT
        self.REQUEST_LIMIT = Config.REQUEST_LIMIT
        self.RESET_HOURS = Config.RESET_HOURS

    def check_limits(self, user_id: int) -> tuple:
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

    def increment_usage(self, user_id: int):
        user = self.db.get_user(user_id)
        new_count = user.get('request_count', 0) + 1
        update_data = {
            'request_count': new_count,
            'last_request': int(time.time())
        }
        
        if not user.get('reset_time'):
            update_data['reset_time'] = time.time() + (self.RESET_HOURS * 3600)
        
        self.db.update_user(user_id, update_data)

# تعريف الكائن هنا بشكل صحيح
limiter = UsageLimiter()
