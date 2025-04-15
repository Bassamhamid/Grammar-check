import firebase_admin
from firebase_admin import credentials, db
from config import Config
import logging
import time
from typing import Dict, Optional

# Initialize Firebase
_firebase_app = None

def initialize_firebase():
    global _firebase_app
    try:
        if not firebase_admin._apps:
            if not Config.FIREBASE_SERVICE_ACCOUNT:
                raise ValueError("FIREBASE_SERVICE_ACCOUNT not configured")
            if not Config.FIREBASE_DATABASE_URL:
                raise ValueError("FIREBASE_DATABASE_URL not configured")

            cred = credentials.Certificate(Config.FIREBASE_SERVICE_ACCOUNT)
            _firebase_app = firebase_admin.initialize_app(cred, {
                'databaseURL': Config.FIREBASE_DATABASE_URL
            })
            logging.info("✅ Firebase initialized successfully")
    except Exception as e:
        logging.error(f"🔥 Failed to initialize Firebase: {str(e)}")
        raise

class FirebaseDB:
    def __init__(self):
        initialize_firebase()
        self.users_ref = db.reference('/users')
        self.stats_ref = db.reference('/stats')
        self.settings_ref = db.reference('/settings')

    def get_user(self, user_id: int) -> dict:
        """Get user data by ID"""
        default_data = {
            'request_count': 0,
            'last_request': None,
            'reset_time': time.time() + (Config.RESET_HOURS * 3600),
            'is_premium': False,
            'is_banned': False,
            'last_active': None,
            'timestamp': time.time(),
            'username': None
        }
        try:
            snapshot = self.users_ref.child(str(user_id)).get()
            return {**default_data, **snapshot} if snapshot else default_data
        except Exception as e:
            logging.error(f"🚨 Error in get_user: {str(e)}")
            return default_data

    def get_user_by_username(self, username: str) -> Optional[dict]:
        """Get user data by username"""
        try:
            all_users = self.get_all_users()
            return next((u for u in all_users.values() if u.get('username') == username), None)
        except Exception as e:
            logging.error(f"🚨 Error in get_user_by_username: {str(e)}")
            return None

    def update_user(self, user_id: int, data: dict):
        """Update user data"""
        try:
            data['timestamp'] = time.time()
            self.users_ref.child(str(user_id)).update(data)
        except Exception as e:
            logging.error(f"🚨 Error in update_user: {str(e)}")
            raise

    def get_stats(self) -> dict:
        """Get bot statistics"""
        try:
            snapshot = self.stats_ref.get()
            return snapshot or {
                'total_requests': 0,
                'daily_requests': 0,
                'last_reset': time.time()
            }
        except Exception as e:
            logging.error(f"🚨 Error in get_stats: {str(e)}")
            return {'total_requests': 0, 'daily_requests': 0}

    def update_stats(self, data: dict):
        """Update bot statistics"""
        try:
            self.stats_ref.update(data)
        except Exception as e:
            logging.error(f"🚨 Error in update_stats: {str(e)}")
            raise

    def get_settings(self) -> dict:
        """Get bot settings"""
        default_settings = {
            'maintenance_mode': False,
            'normal_text_limit': Config.CHAR_LIMIT,
            'premium_text_limit': Config.PREMIUM_CHAR_LIMIT,
            'daily_limit': Config.REQUEST_LIMIT,
            'premium_daily_limit': Config.PREMIUM_REQUEST_LIMIT
        }
        try:
            snapshot = self.settings_ref.get()
            return {**default_settings, **snapshot} if snapshot else default_settings
        except Exception as e:
            logging.error(f"🚨 Error in get_settings: {str(e)}")
            return default_settings

    def update_settings(self, settings: dict) -> bool:
        """Update bot settings"""
        try:
            self.settings_ref.update(settings)
            return True
        except Exception as e:
            logging.error(f"🚨 Error in update_settings: {str(e)}")
            return False

    def get_all_users(self) -> Dict[str, dict]:
        """Get all users"""
        try:
            return self.users_ref.get() or {}
        except Exception as e:
            logging.error(f"🚨 Error in get_all_users: {str(e)}")
            return {}

    def ban_user(self, user_id: int) -> bool:
        """Ban a user"""
        return self._update_user_status(user_id, True)

    def unban_user(self, user_id: int) -> bool:
        """Unban a user"""
        return self._update_user_status(user_id, False)

    def _update_user_status(self, user_id: int, is_banned: bool) -> bool:
        """Internal method to update user ban status"""
        try:
            self.users_ref.child(str(user_id)).update({
                'is_banned': is_banned,
                'timestamp': time.time()
            })
            return True
        except Exception as e:
            logging.error(f"🚨 Error in _update_user_status: {str(e)}")
            return False
