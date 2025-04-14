import firebase_admin
from firebase_admin import credentials, db
from config import Config
import logging

# تهيئة Firebase (نسخة معدلة)
_firebase_app = None

def initialize_firebase():
    global _firebase_app
    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(Config.FIREBASE_SERVICE_ACCOUNT)
            _firebase_app = firebase_admin.initialize_app(cred, {
                'databaseURL': Config.FIREBASE_DB_URL
            })
            logging.info("✅ Firebase initialized successfully")
    except Exception as e:
        logging.error(f"🔥 Failed to initialize Firebase: {str(e)}")
        raise

class FirebaseDB:
    def __init__(self):
        initialize_firebase()  # تأكد من التهيئة أولاً
        try:
            self.ref = db.reference('/arabic_bot_users')
        except Exception as e:
            logging.error(f"🚨 Failed to create database reference: {str(e)}")
            raise
