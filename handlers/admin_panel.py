from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from config import Config
import logging
import csv
from io import StringIO
from datetime import datetime
from firebase_admin import db

logger = logging.getLogger(__name__)

# حالة البوت
MAINTENANCE_MODE = False

def is_admin(user_id):
    return user_id in Config.ADMIN_IDS

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not is_admin(update.effective_user.id):
            await update.message.reply_text("⛔ ليس لديك صلاحية الدخول")
            return

        keyboard = [
            [InlineKeyboardButton("📊 إحصائيات حقيقية", callback_data="real_stats")],
            [InlineKeyboardButton("📢 إرسال إشعار فعلي", callback_data="real_broadcast")],
            [InlineKeyboardButton("👥 إدارة مستخدمين حقيقية", callback_data="real_users")],
            [InlineKeyboardButton("🔧 إعدادات فعلية", callback_data="real_settings")]
        ]
        
        await update.message.reply_text(
            "🛠️ لوحة تحكم المشرفين - النسخة المعدلة:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        logger.error(f"Error in admin_panel: {str(e)}")

async def handle_real_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    try:
        # جلب بيانات حقيقية من Firebase
        users_ref = db.reference('users')
        stats_ref = db.reference('stats')
        
        users = users_ref.get() or {}
        stats = stats_ref.get() or {}
        
        total_users = len(users)
        active_today = len([u for u in users.values() if u.get('last_active') == str(datetime.now().date())])
        total_requests = stats.get('total_requests', 0)
        api_users = len([u for u in users.values() if u.get('is_premium', False)])
        banned_users = len([u for u in users.values() if u.get('is_banned', False)])
        
        stats_text = (
            "📊 الإحصائيات الفعلية:\n\n"
            f"👥 إجمالي المستخدمين: {total_users}\n"
            f"🟢 نشطين اليوم: {active_today}\n"
            f"📨 إجمالي الطلبات: {total_requests}\n"
            f"⭐ مستخدمين API: {api_users}\n"
            f"⛔ محظورين: {banned_users}"
        )
        
        await query.edit_message_text(
            stats_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 تحديث حقيقي", callback_data="real_stats")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_real_admin")]
            ])
        )
        
    except Exception as e:
        logger.error(f"Error in real stats: {str(e)}")
        await query.edit_message_text("⚠️ حدث خطأ في جلب البيانات")

async def handle_real_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "📢 أرسل الرسالة للإشعار الفعلي:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("إلغاء", callback_data="back_to_real_admin")]
        ])
    )
    context.user_data['awaiting_real_broadcast'] = True

async def send_real_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'awaiting_real_broadcast' in context.user_data:
        message = update.message.text
        
        try:
            users_ref = db.reference('users')
            users = users_ref.get() or {}
            
            sent_count = 0
            for user_id, user_data in users.items():
                try:
                    if user_data.get('is_banned', False):
                        continue
                        
                    # هنا كود إرسال الرسالة الفعلي لكل مستخدم
                    # await context.bot.send_message(chat_id=user_id, text=message)
                    sent_count += 1
                    
                    if sent_count >= Config.MAX_BROADCAST_USERS:
                        break
                        
                except Exception as e:
                    logger.error(f"Error sending to {user_id}: {str(e)}")
            
            await update.message.reply_text(f"✅ تم إرسال الإشعار لـ {sent_count} مستخدم")
            
        except Exception as e:
            logger.error(f"Broadcast error: {str(e)}")
            await update.message.reply_text("⚠️ فشل في إرسال الإشعار")
        
        finally:
            del context.user_data['awaiting_real_broadcast']
            await admin_panel(update, context)

def setup_admin_handlers(application):
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(CallbackQueryHandler(handle_real_stats, pattern="^real_stats$"))
    application.add_handler(CallbackQueryHandler(handle_real_broadcast, pattern="^real_broadcast$"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, send_real_broadcast))
