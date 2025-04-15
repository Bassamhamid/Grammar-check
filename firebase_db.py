import firebase_admin
from firebase_admin import credentials, db
from config import Config
import logging
import time
from datetime import datetime
from typing import Dict, Optional, List

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
        self.logs_ref = db.reference('/logs')

    def get_user(self, user_id: int) -> dict:
        """Get user data by ID with default values"""
        default_data = {
            'request_count': 0,
            'last_request': None,
            'reset_time': time.time() + (Config.RESET_HOURS * 3600),
            'is_premium': False,
            'is_banned': False,
            'last_active': None,
            'timestamp': time.time(),
            'username': None,
            'started_chat': True  # Default to True assuming user has started chat
        }
        try:
            snapshot = self.users_ref.child(str(user_id)).get()
            return {**default_data, **snapshot} if snapshot else default_data
        except Exception as e:
            logging.error(f"🚨 Error in get_user: {str(e)}")
            return default_data

    def get_user_by_username(self, username: str) -> Optional[dict]:
        """Get user data by username (case-insensitive)"""
        try:
            all_users = self.get_all_users()
            username = username.lower().strip('@')
            return next(
                (u for u in all_users.values() 
                 if u.get('username', '').lower() == username),
                None
            )
        except Exception as e:
            logging.error(f"🚨 Error in get_user_by_username: {str(e)}")
            return None

    def update_user(self, user_id: int, data: dict) -> bool:
        """Update user data with timestamp"""
        try:
            data['timestamp'] = time.time()
            self.users_ref.child(str(user_id)).update(data)
            return True
        except Exception as e:
            logging.error(f"🚨 Error in update_user: {str(e)}")
            return False

    def get_stats(self) -> dict:
        """Get bot statistics with default values"""
        default_stats = {
            'total_requests': 0,
            'daily_requests': 0,
            'last_reset': time.time(),
            'total_users': 0,
            'active_today': 0,
            'premium_users': 0,
            'banned_users': 0,
            'last_updated': 0
        }
        try:
            snapshot = self.stats_ref.get()
            return {**default_stats, **snapshot} if snapshot else default_stats
        except Exception as e:
            logging.error(f"🚨 Error in get_stats: {str(e)}")
            return default_stats

    def update_stats(self) -> bool:
        """Update statistics in Firebase"""
        try:
            users = self.get_all_users()
            today = datetime.now().date().isoformat()
            
            stats = {
                'total_users': len(users),
                'active_today': sum(
                    1 for u in users.values() 
                    if u.get('last_active', '').startswith(today)
                ),
                'premium_users': sum(1 for u in users.values() if u.get('is_premium')),
                'banned_users': sum(1 for u in users.values() if u.get('is_banned')),
                'last_updated': time.time()
            }
            
            self.stats_ref.update(stats)
            return True
        except Exception as e:
            logging.error(f"🚨 Error updating stats: {str(e)}")
            return False

    def get_settings(self) -> dict:
        """Get bot settings with default values"""
        default_settings = {
            'maintenance_mode': False,
            'normal_text_limit': Config.CHAR_LIMIT,
            'premium_text_limit': Config.PREMIUM_CHAR_LIMIT,
            'daily_limit': Config.REQUEST_LIMIT,
            'premium_daily_limit': Config.PREMIUM_REQUEST_LIMIT,
            'last_updated': time.time()
        }
        try:
            snapshot = self.settings_ref.get()
            return {**default_settings, **snapshot} if snapshot else default_settings
        except Exception as e:
            logging.error(f"🚨 Error in get_settings: {str(e)}")
            return default_settings

    def update_settings(self, settings: dict) -> bool:
        """Update bot settings with timestamp"""
        try:
            settings['last_updated'] = time.time()
            self.settings_ref.update(settings)
            return True
        except Exception as e:
            logging.error(f"🚨 Error in update_settings: {str(e)}")
            return False

    def get_all_users(self) -> Dict[str, dict]:
        """Get all users with empty dict as fallback"""
        try:
            return self.users_ref.get() or {}
        except Exception as e:
            logging.error(f"🚨 Error in get_all_users: {str(e)}")
            return {}

    def get_recent_users(self, limit: int = 50) -> Dict[str, dict]:
        """Get recent users ordered by timestamp"""
        try:
            users = self.users_ref.order_by_child('timestamp').limit_to_last(limit).get()
            return users or {}
        except Exception as e:
            logging.error(f"🚨 Error getting recent users: {str(e)}")
            return {}

    def ban_user(self, user_id: int) -> bool:
        """Ban user and log the action"""
        success = self._update_user_status(user_id, True)
        if success:
            self.log_action(f"banned user {user_id}")
        return success

    def unban_user(self, user_id: int) -> bool:
        """Unban user and log the action"""
        success = self._update_user_status(user_id, False)
        if success:
            self.log_action(f"unbanned user {user_id}")
        return success

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

    def log_action(self, action: str) -> bool:
        """Log admin actions"""
        try:
            self.logs_ref.push().set({
                'action': action,
                'timestamp': time.time(),
                'time_str': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
            return True
        except Exception as e:
            logging.error(f"🚨 Error logging action: {str(e)}")
            return False

    def reset_daily_limits(self) -> bool:
        """Reset daily request limits for all users"""
        try:
            users = self.get_all_users()
            for user_id in users:
                self.users_ref.child(str(user_id)).update({
                    'request_count': 0,
                    'reset_time': time.time() + (Config.RESET_HOURS * 3600),
                    'timestamp': time.time()
                })
            self.log_action("reset daily limits for all users")
            return True
        except Exception as e:
            logging.error(f"🚨 Error resetting daily limits: {str(e)}")
            return False
