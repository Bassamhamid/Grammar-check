import firebase_admin
from firebase_admin import credentials, db
from config import Config
import logging
import time
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class FirebaseDB:
    def __init__(self):
        if not firebase_admin._apps:
            cred = credentials.Certificate(Config.FIREBASE_SERVICE_ACCOUNT)
            firebase_admin.initialize_app(cred, {
                'databaseURL': Config.FIREBASE_DATABASE_URL
            })
        
        self.root_ref = db.reference('/')
    
    # ------------------- إدارة المستخدمين -------------------
    def get_user(self, user_id: int) -> dict:
        """الحصول على بيانات مستخدم"""
        try:
            user_ref = self.root_ref.child('users').child(str(user_id))
            return user_ref.get() or {}
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {str(e)}")
            return {}

    def update_user(self, user_id: int, data: dict):
        """تحديث بيانات مستخدم"""
        try:
            user_ref = self.root_ref.child('users').child(str(user_id))
            user_ref.update(data)
            
            # تحديث آخر نشاط إذا لم يكن موجوداً في البيانات
            if 'last_activity' not in data:
                user_ref.update({'last_activity': time.time()})
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {str(e)}")
            raise

    def get_all_users(self) -> dict:
        """الحصول على جميع المستخدمين"""
        try:
            return self.root_ref.child('users').get() or {}
        except Exception as e:
            logger.error(f"Error getting all users: {str(e)}")
            return {}

    def ban_user(self, user_id: int, reason: str = ""):
        """حظر مستخدم"""
        try:
            self.root_ref.child('banned_users').child(str(user_id)).set({
                'timestamp': time.time(),
                'reason': reason
            })
        except Exception as e:
            logger.error(f"Error banning user {user_id}: {str(e)}")
            raise

    def unban_user(self, user_id: int):
        """إلغاء حظر مستخدم"""
        try:
            self.root_ref.child('banned_users').child(str(user_id)).delete()
        except Exception as e:
            logger.error(f"Error unbanning user {user_id}: {str(e)}")
            raise

    def is_banned(self, user_id: int) -> bool:
        """التحقق إذا كان المستخدم محظوراً"""
        try:
            banned_user = self.root_ref.child('banned_users').child(str(user_id)).get()
            return banned_user is not None
        except Exception as e:
            logger.error(f"Error checking ban status for user {user_id}: {str(e)}")
            return False

    # ------------------- الإحصاءات -------------------
    def get_stats(self) -> dict:
    """الحصول على الإحصاءات العامة"""
    try:
        stats_ref = self.root_ref.child('stats')
        stats = stats_ref.get()
        
        logger.info(f"Firebase stats data: {stats}")  # تسجيل البيانات المستلمة
        
        if not stats:
            initial_stats = {
                'total_users': self.count_users(),
                'premium_users': self.count_premium_users(),
                'total_requests': 0,
                'daily_requests': 0,
                'last_reset': time.time()
            }
            stats_ref.set(initial_stats)
            return initial_stats
        
        return stats
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}", exc_info=True)
        return {}

    def update_stats(self, data: dict):
        """تحديث الإحصاءات العامة"""
        try:
            current_stats = self.get_stats()
            current_stats.update(data)
            self.root_ref.child('stats').update(current_stats)
            
            # إعادة تعيين الطلبات اليومية إذا مر 24 ساعة
            if time.time() - current_stats.get('last_reset', 0) > 86400:  # 24 ساعة
                self.reset_daily_stats()
        except Exception as e:
            logger.error(f"Error updating stats: {str(e)}")
            raise

    def reset_daily_stats(self):
        """إعادة تعيين الإحصاءات اليومية"""
        try:
            self.root_ref.child('stats').update({
                'daily_requests': 0,
                'last_reset': time.time()
            })
        except Exception as e:
            logger.error(f"Error resetting daily stats: {str(e)}")
            raise

    def count_users(self) -> int:
        """عد جميع المستخدمين"""
        try:
            users = self.root_ref.child('users').get()
            return len(users) if users else 0
        except Exception as e:
            logger.error(f"Error counting users: {str(e)}")
            return 0

    def count_premium_users(self) -> int:
        """عد المستخدمين المميزين"""
        try:
            users = self.root_ref.child('users').get() or {}
            return sum(1 for user in users.values() if user.get('is_premium', False))
        except Exception as e:
            logger.error(f"Error counting premium users: {str(e)}")
            return 0

    def initialize_stats(self):
        """تهيئة الإحصاءات إذا لم تكن موجودة"""
        try:
            if not self.root_ref.child('stats').get():
                self.root_ref.child('stats').set({
                    'total_users': self.count_users(),
                    'premium_users': self.count_premium_users(),
                    'total_requests': 0,
                    'daily_requests': 0,
                    'last_reset': time.time()
                })
        except Exception as e:
            logger.error(f"Error initializing stats: {str(e)}")
            raise

    # ------------------- الإعدادات -------------------
    def get_settings(self) -> dict:
        """الحصول على إعدادات البوت"""
        try:
            settings = self.root_ref.child('settings').get() or {}
            
            # القيم الافتراضية إذا لم تكن الإعدادات موجودة
            if not settings:
                settings = {
                    'char_limit': Config.CHAR_LIMIT,
                    'premium_char_limit': Config.PREMIUM_CHAR_LIMIT,
                    'request_limit': Config.REQUEST_LIMIT,
                    'premium_request_limit': Config.PREMIUM_REQUEST_LIMIT,
                    'reset_hours': Config.RESET_HOURS,
                    'premium_reset_hours': Config.PREMIUM_RESET_HOURS,
                    'maintenance_mode': False
                }
                self.root_ref.child('settings').set(settings)
            
            return settings
        except Exception as e:
            logger.error(f"Error getting settings: {str(e)}")
            return {}

    def update_settings(self, new_settings: dict):
        """تحديث إعدادات البوت"""
        try:
            current_settings = self.get_settings()
            current_settings.update(new_settings)
            self.root_ref.child('settings').update(current_settings)
        except Exception as e:
            logger.error(f"Error updating settings: {str(e)}")
            raise

    def is_maintenance_mode(self) -> bool:
        """التحقق من وضع الصيانة"""
        try:
            settings = self.get_settings()
            return settings.get('maintenance_mode', False)
        except Exception as e:
            logger.error(f"Error checking maintenance mode: {str(e)}")
            return False

def initialize_firebase():
    """تهيئة Firebase (للاستيراد في main.py)"""
    return FirebaseDB()
