import firebase_admin
from firebase_admin import credentials, db
from config import Config
import logging
import time
from typing import Dict, List

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

    def get_user(self, user_id: int) -> dict:
        """استرجاع بيانات المستخدم من Firebase"""
        current_time = time.time()
        default_data = {
            'request_count': 0,
            'last_request': None,
            'reset_time': current_time + (Config.RESET_HOURS * 3600),
            'is_premium': False,
            'is_banned': False,
            'last_active': None,
            'timestamp': current_time
        }
        try:
            snapshot = self.users_ref.child(str(user_id)).get()
            if snapshot:
                return {**default_data, **snapshot}
            return default_data
        except Exception as e:
            logging.error(f"🚨 خطأ في get_user: {str(e)}")
            return default_data

    def update_user(self, user_id: int, data: dict):
        """تحديث بيانات المستخدم في Firebase"""
        try:
            data['timestamp'] = time.time()
            self.users_ref.child(str(user_id)).update(data)
        except Exception as e:
            logging.error(f"🚨 خطأ في update_user: {str(e)}")
            raise

    def get_stats(self) -> dict:
        """استرجاع إحصائيات البوت"""
        try:
            snapshot = self.stats_ref.get()
            return snapshot if snapshot else {'total_requests': 0, 'daily_requests': 0}
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
