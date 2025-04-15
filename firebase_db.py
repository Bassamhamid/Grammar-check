import firebase_admin
from firebase_admin import credentials, db
from config import Config
import logging
import time
from typing import Dict, List, Optional

# تهيئة Firebase
_firebase_app = None

def initialize_firebase():
    global _firebase_app
    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(Config.FIREBASE_SERVICE_ACCOUNT)
            _firebase_app = firebase_admin.initialize_app(cred, {
                'databaseURL': Config.FIREBASE_DB_URL
            })
            logging.info("✅ تم تهيئة Firebase بنجاح")
    except Exception as e:
        logging.error(f"🔥 فشل تهيئة Firebase: {str(e)}")
        raise

class FirebaseDB:
    def __init__(self):
        initialize_firebase()
        self.users_ref = db.reference('/users')
        self.stats_ref = db.reference('/stats')
        self.settings_ref = db.reference('/settings')

    def get_user(self, user_id: int) -> dict:
        """استرجاع بيانات المستخدم من Firebase باستخدام ID"""
        current_time = time.time()
        default_data = {
            'request_count': 0,
            'last_request': None,
            'reset_time': current_time + (Config.RESET_HOURS * 3600),
            'is_premium': False,
            'is_banned': False,
            'last_active': None,
            'timestamp': current_time,
            'username': None
        }
        try:
            snapshot = self.users_ref.child(str(user_id)).get()
            if snapshot:
                return {**default_data, **snapshot}
            return default_data
        except Exception as e:
            logging.error(f"🚨 خطأ في get_user: {str(e)}")
            return default_data

    def get_user_by_username(self, username: str) -> Optional[dict]:
        """استرجاع بيانات المستخدم باستخدام اسم المستخدم"""
        try:
            all_users = self.users_ref.get() or {}
            for user_id, user_data in all_users.items():
                if user_data.get('username') == username:
                    return user_data
            return None
        except Exception as e:
            logging.error(f"🚨 خطأ في get_user_by_username: {str(e)}")
            return None

    def update_user(self, user_id: int, data: dict):
        """تحديث بيانات المستخدم في Firebase"""
        try:
            data['timestamp'] = time.time()
            self.users_ref.child(str(user_id)).update(data)
        except Exception as e:
            logging.error(f"🚨 خطأ في update_user: {str(e)}")
            raise

    def update_user_by_username(self, username: str, updates: dict):
        """تحديث بيانات المستخدم باستخدام اسم المستخدم"""
        try:
            all_users = self.users_ref.get() or {}
            for user_id, user_data in all_users.items():
                if user_data.get('username') == username:
                    updates['timestamp'] = time.time()
                    self.users_ref.child(user_id).update(updates)
                    return True
            return False
        except Exception as e:
            logging.error(f"🚨 خطأ في update_user_by_username: {str(e)}")
            raise

    def get_stats(self) -> dict:
        """استرجاع إحصائيات البوت"""
        try:
            snapshot = self.stats_ref.get()
            return snapshot if snapshot else {
                'total_requests': 0,
                'daily_requests': 0,
                'last_reset': time.time()
            }
        except Exception as e:
            logging.error(f"🚨 خطأ في get_stats: {str(e)}")
            return {'total_requests': 0, 'daily_requests': 0}

    def update_stats(self, data: dict):
        """تحديث إحصائيات البوت"""
        try:
            self.stats_ref.update(data)
        except Exception as e:
            logging.error(f"🚨 خطأ في update_stats: {str(e)}")
            raise

    def get_settings(self) -> dict:
        """استرجاع إعدادات البوت"""
        default_settings = {
            'maintenance_mode': False,
            'normal_text_limit': 500,
            'premium_text_limit': 2000,
            'daily_limit': 10,
            'renew_time': '00:00'
        }
        try:
            snapshot = self.settings_ref.get()
            return {**default_settings, **snapshot} if snapshot else default_settings
        except Exception as e:
            logging.error(f"🚨 خطأ في get_settings: {str(e)}")
            return default_settings

    def update_settings(self, new_settings: dict):
        """تحديث إعدادات البوت"""
        try:
            self.settings_ref.update(new_settings)
            return True
        except Exception as e:
            logging.error(f"🚨 خطأ في update_settings: {str(e)}")
            return False

    def get_recent_users(self, limit: int = 10) -> Dict[str, dict]:
        """استرجاع أحدث المستخدمين"""
        try:
            all_users = self.users_ref.get() or {}
            sorted_users = sorted(
                all_users.items(),
                key=lambda x: x[1].get('timestamp', 0),
                reverse=True
            )
            return dict(sorted_users[:limit])
        except Exception as e:
            logging.error(f"🚨 خطأ في get_recent_users: {str(e)}")
            return {}

    def get_all_users(self) -> Dict[str, dict]:
        """استرجاع جميع المستخدمين"""
        try:
            return self.users_ref.get() or {}
        except Exception as e:
            logging.error(f"🚨 خطأ في get_all_users: {str(e)}")
            return {}

    def ban_user(self, user_id: int) -> bool:
        """حظر مستخدم"""
        try:
            self.users_ref.child(str(user_id)).update({
                'is_banned': True,
                'timestamp': time.time()
            })
            return True
        except Exception as e:
            logging.error(f"🚨 خطأ في ban_user: {str(e)}")
            return False

    def unban_user(self, user_id: int) -> bool:
        """رفع الحظر عن مستخدم"""
        try:
            self.users_ref.child(str(user_id)).update({
                'is_banned': False,
                'timestamp': time.time()
            })
            return True
        except Exception as e:
            logging.error(f"🚨 خطأ في unban_user: {str(e)}")
            return False
