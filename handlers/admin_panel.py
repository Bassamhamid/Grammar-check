from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, CommandHandler, filters
from config import Config
import logging
from datetime import datetime
from firebase_admin import db
from utils.limits import limiter
from firebase_db import FirebaseDB
import time

logger = logging.getLogger(__name__)
firebase_db = FirebaseDB()

# حالة البوت
MAINTENANCE_MODE = False

def is_admin(user_id):
    return str(user_id) in [str(admin_id) for admin_id in Config.ADMIN_IDS]

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not is_admin(update.effective_user.id):
            await update.message.reply_text("⛔ ليس لديك صلاحية الدخول")
            return

        keyboard = [
            [InlineKeyboardButton("📊 الإحصائيات الحية", callback_data="real_stats")],
            [InlineKeyboardButton("📢 إرسال إشعار عام", callback_data="broadcast")],
            [InlineKeyboardButton("👥 إدارة المستخدمين", callback_data="manage_users")],
            [InlineKeyboardButton("⚙️ الإعدادات", callback_data="settings")],
            [InlineKeyboardButton("🔄 تحديث البيانات", callback_data="refresh_data")]
        ]
        
        await update.message.reply_text(
            "🛠️ لوحة تحكم المشرفين:\n\n"
            "اختر الخيار المطلوب:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Error in admin_panel: {str(e)}", exc_info=True)
        await update.message.reply_text("⚠️ حدث خطأ في تحميل لوحة التحكم")

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    try:
        users = firebase_db.get_all_users()
        stats = firebase_db.get_stats()

        total_users = len(users)
        active_today = 0
        premium_users = 0
        banned_users = 0
        
        today = datetime.now().date().isoformat()
        for user_data in users.values():
            last_active = user_data.get('last_active', '')
            if isinstance(last_active, str) and last_active.startswith(today):
                active_today += 1
            if user_data.get('is_premium', False):
                premium_users += 1
            if user_data.get('is_banned', False):
                banned_users += 1

        stats_text = (
            "📊 الإحصائيات الحية:\n\n"
            f"👥 إجمالي المستخدمين: {total_users}\n"
            f"🟢 نشطين اليوم: {active_today}\n"
            f"📨 طلبات اليوم: {stats.get('daily_requests', 0)}\n"
            f"📈 إجمالي الطلبات: {stats.get('total_requests', 0)}\n"
            f"⭐ مستخدمين مميزين: {premium_users}\n"
            f"⛔ مستخدمين محظورين: {banned_users}\n\n"
            f"🔄 آخر تحديث: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        keyboard = [
            [InlineKeyboardButton("🔄 تحديث", callback_data="real_stats")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_admin")]
        ]

        await query.edit_message_text(
            stats_text,
            reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        logger.error(f"Error in show_stats: {str(e)}", exc_info=True)
        await query.edit_message_text("⚠️ حدث خطأ في جلب الإحصائيات")

async def manage_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    try:
        users = firebase_db.get_recent_users(10)
        
        users_list = []
        for user_id, user_data in users.items():
            users_list.append(
                f"👤 {user_data.get('username', 'مجهول')} (ID: {user_id})\n"
                f"⭐ {'مميز' if user_data.get('is_premium', False) else 'عادي'} | "
                f"⛔ {'محظور' if user_data.get('is_banned', False) else 'نشط'}\n"
                f"📅 آخر نشاط: {user_data.get('last_active', 'غير معروف')}"
            )

        users_text = "👥 آخر 10 مستخدمين:\n\n" + "\n\n".join(users_list) if users_list else "⚠️ لا يوجد مستخدمين مسجلين"

        keyboard = [
            [InlineKeyboardButton("🔄 تحديث", callback_data="manage_users")],
            [InlineKeyboardButton("🔍 بحث عن مستخدم", callback_data="search_user")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_admin")]
        ]

        await query.edit_message_text(
            users_text,
            reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        logger.error(f"Error in manage_users: {str(e)}", exc_info=True)
        await query.edit_message_text("⚠️ حدث خطأ في جلب بيانات المستخدمين")

async def broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    try:
        await query.edit_message_text(
            "📢 أرسل الرسالة للإشعار العام:\n\n"
            "يمكنك استخدام تنسيق Markdown مثل:\n"
            "*عريض* _مائل_ `كود`\n\n"
            "أو /cancel للإلغاء",
            parse_mode="Markdown")
        context.user_data['awaiting_broadcast'] = True
    except Exception as e:
        logger.error(f"Error in broadcast_message: {str(e)}", exc_info=True)

async def send_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.user_data.get('awaiting_broadcast'):
            return

        message = update.message.text
        if not message:
            await update.message.reply_text("⚠️ يرجى إرسال رسالة صالحة")
            return

        if message.lower() == '/cancel':
            await update.message.reply_text("تم إلغاء الإرسال")
            await admin_panel(update, context)
            return

        users = firebase_db.get_all_users()
        total_users = len(users)
        sent_count = 0
        failed_count = 0

        status_msg = await update.message.reply_text(f"⏳ جاري الإرسال... 0/{total_users}")

        for user_id in users:
            try:
                await context.bot.send_message(
                    chat_id=int(user_id),
                    text=message,
                    parse_mode="Markdown")
                sent_count += 1
                if sent_count % 10 == 0:
                    await status_msg.edit_text(f"⏳ جاري الإرسال... {sent_count}/{total_users}")
            except Exception:
                failed_count += 1

        await status_msg.edit_text(
            f"✅ تم إرسال الإشعار بنجاح:\n"
            f"📤 تم الإرسال لـ: {sent_count} مستخدم\n"
            f"❌ فشل الإرسال لـ: {failed_count} مستخدم")
        await admin_panel(update, context)
    except Exception as e:
        logger.error(f"Error in send_broadcast: {str(e)}", exc_info=True)
        await update.message.reply_text("⚠️ حدث خطأ أثناء الإرسال")
    finally:
        context.user_data.pop('awaiting_broadcast', None)

async def show_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    try:
        stats = firebase_db.get_stats()
        settings_text = (
            "⚙️ إعدادات البوت:\n\n"
            f"🔧 وضع الصيانة: {'✅ مفعل' if MAINTENANCE_MODE else '❌ معطل'}\n"
            f"📝 حد النص العادي: {Config.CHAR_LIMIT} حرف\n"
            f"💎 حد النص المميز: {Config.PREMIUM_CHAR_LIMIT} حرف\n"
            f"📨 طلبات اليوم: {stats.get('daily_requests', 0)}\n"
            f"🔄 وقت التجديد: كل {Config.RESET_HOURS} ساعة"
        )

        keyboard = [
            [InlineKeyboardButton("🔧 تبديل وضع الصيانة", callback_data="toggle_maintenance")],
            [InlineKeyboardButton("🔄 تحديث", callback_data="settings")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_admin")]
        ]

        await query.edit_message_text(
            settings_text,
            reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        logger.error(f"Error in show_settings: {str(e)}", exc_info=True)
        await query.edit_message_text("⚠️ حدث خطأ في جلب الإعدادات")

async def back_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await admin_panel(update, context)

def setup_admin_handlers(application):
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(CallbackQueryHandler(show_stats, pattern="^real_stats$"))
    application.add_handler(CallbackQueryHandler(broadcast_message, pattern="^broadcast$"))
    application.add_handler(CallbackQueryHandler(manage_users, pattern="^manage_users$"))
    application.add_handler(CallbackQueryHandler(show_settings, pattern="^settings$"))
    application.add_handler(CallbackQueryHandler(back_to_admin, pattern="^back_to_admin$"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, send_broadcast))
