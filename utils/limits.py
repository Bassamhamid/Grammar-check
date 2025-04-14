import time
from config import Config

class UsageLimiter:
    def __init__(self):
        self.user_data = {}

    def check_limits(self, user_id: int) -> tuple:
        current_time = time.time()
        
        if user_id not in self.user_data:
            self.user_data[user_id] = {
                "count": 0,
                "reset_time": current_time + (Config.RESET_HOURS * 3600)
            }
        
        user = self.user_data[user_id]
        
        # Check if reset time passed
        if current_time > user["reset_time"]:
            user["count"] = 0
            user["reset_time"] = current_time + (Config.RESET_HOURS * 3600)
        
        return user["count"] < Config.REQUEST_LIMIT, user["reset_time"] - current_time

    def increment_usage(self, user_id: int):
        if user_id not in self.user_data:
            self.check_limits(user_id)  # Initialize if not exists
        self.user_data[user_id]["count"] += 1

limiter = UsageLimiter()
