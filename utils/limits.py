from firebase_db import FirebaseDB
import time
from config import Config

class UsageLimiter:
    def __init__(self):
        self.db = FirebaseDB()  # استبدل التخزين المحلي بـ Firebase

    def check_limits(self, user_id: int) -> tuple:
        user = self.db.get_user(user_id)
        current_time = time.time()
        
        if user['reset_time'] and current_time > user['reset_time']:
            self.db.update_user(user_id, {
                'request_count': 0,
                'reset_time': current_time + (Config.RESET_HOURS * 3600)
            })
            return True, 0
        
        remaining = Config.REQUEST_LIMIT - user['request_count']
        time_left = max(0, (user['reset_time'] - current_time))
        return remaining > 0, time_left

    def increment_usage(self, user_id: int):
        user = self.db.get_user(user_id)
        new_count = user['request_count'] + 1
        
        update_data = {
            'request_count': new_count,
            'last_request': int(time.time())
        }
        
        if not user['reset_time']:
            update_data['reset_time'] = time.time() + (Config.RESET_HOURS * 3600)
        
        self.db.update_user(user_id, update_data)
