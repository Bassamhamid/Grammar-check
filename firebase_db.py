import firebase_admin
from firebase_admin import credentials, db
from config import Config

def initialize_firebase():
    # لا حاجة لملف JSON، نستخدم المتغير مباشرة
    cred = credentials.Certificate(Config.FIREBASE_SERVICE_ACCOUNT)
    firebase_admin.initialize_app(cred, {
        'databaseURL': Config.FIREBASE_DB_URL
    })

class FirebaseDB:
    def __init__(self):
        self.ref = db.reference('/arabic_bot_users')  # يمكنك تغيير المسار هنا
        
    def update_user(self, user_id: int, data: dict):
        self.ref.child(str(user_id)).update(data)
    
    def get_user(self, user_id: int) -> dict:
        return self.ref.child(str(user_id)).get() or {
            'request_count': 0,
            'last_request': None,
            'reset_time': None,
            'is_premium': False
        }
