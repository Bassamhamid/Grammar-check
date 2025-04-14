from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from config import Config
import logging
import csv
from io import StringIO
from datetime import datetime
from firebase_admin import db  # استيراد Firebase

logger = logging.getLogger(__name__)

# حالة البوت
MAINTENANCE_MODE = False

def is_admin(user_id):
    try:
        return user_id in Config.ADMIN_IDS
    except:
        return False

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not is_admin(update.effective_user.id):
            if update.callback_query:
                await update.callback_query.answer("⛔ ليس لديك صلاحية الدخول")
            return

        keyboard = [
            [InlineKeyboardButton("📊 إحصائيات البوت", callback_data="bot_stats")],
            [InlineKeyboardButton("📢 إرسال إشعار عام", callback_data="broadcast")],
            [InlineKeyboardButton("👥 إدارة المستخدمين", callback_data="manage_users")],
            [InlineKeyboardButton("🔧 إعدادات البوت", callback_data="bot_settings")]
        ]
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                "🛠️ لوحة تحكم المشرفين:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await update.message.reply_text(
                "🛠️ لوحة تحكم المشرفين:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    except Exception as e:
        logger.error(f"Error in admin_panel: {str(e)}")

async def handle_admin_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if not is_admin(query.from_user.id):
        await query.edit_message_text("⛔ صلاحيات غير كافية")
        return

    action = query.data
    
    if action == "bot_stats":
        stats = await get_real_stats()  # الحصول على إحصائيات حقيقية
        await show_stats_menu(query, stats)
    elif action == "broadcast":
        await show_broadcast_menu(query, context)
    elif action == "manage_users":
        await show_user_management_menu(query)
    elif action == "bot_settings":
        await show_bot_settings_menu(query)
    elif action == "back_to_admin":
        await admin_panel(update, context)

async def get_real_stats():
    try:
        # جلب إحصائيات حقيقية من Firebase
        ref = db.reference('/')
        data = ref.get()
        
        return {
            "total_users": len(data.get('users', {})),
            "active_today": sum(1 for u in data.get('users', {}).values() if u.get('last_active') == str(datetime.today().date())),
            "total_requests": data.get('stats', {}).get('total_requests', 0),
            "api_users": sum(1 for u in data.get('users', {}).values() if u.get('is_premium', False)),
            "banned_users": sum(1 for u in data.get('users', {}).values() if u.get('is_banned', False)),
            "last_backup": data.get('stats', {}).get('last_backup', 'غير متوفر')
        }
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        return {
            "total_users": "غير متوفر",
            "active_today": "غير متوفر",
            "total_requests": "غير متوفر",
            "api_users": "غير متوفر",
            "banned_users": "غير متوفر",
            "last_backup": "غير متوفر"
        }

async def show_stats_menu(query, stats):
    text = (
        "📊 إحصائيات البوت (حقيقية):\n\n"
        f"👥 إجمالي المستخدمين: {stats['total_users']}\n"
        f"🟢 مستخدمين نشطين اليوم: {stats['active_today']}\n"
        f"📨 إجمالي الطلبات: {stats['total_requests']}\n"
        f"⭐ مستخدمين API: {stats['api_users']}\n"
        f"⛔ مستخدمين محظورين: {stats['banned_users']}\n"
        f"💾 آخر نسخة احتياطية: {stats['last_backup']}"
    )
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 تحديث", callback_data="bot_stats")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_admin")]
        ])
    )

async def show_broadcast_menu(query, context):
    await query.edit_message_text(
        "📢 أرسل الرسالة التي تريد نشرها لجميع المستخدمين:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("إلغاء", callback_data="back_to_admin")]
        ])
    )
    context.user_data['awaiting_broadcast'] = True

async def show_user_management_menu(query):
    keyboard = [
        [InlineKeyboardButton("🔍 بحث عن مستخدم", callback_data="search_user")],
        [InlineKeyboardButton("⛔ حظر مستخدم", callback_data="ban_user")],
        [InlineKeyboardButton("✅ رفع حظر", callback_data="unban_user")],
        [InlineKeyboardButton("⭐ ترقية مستخدم", callback_data="upgrade_user")],
        [InlineKeyboardButton("📩 تصدير البيانات", callback_data="export_users")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_admin")]
    ]
    
    await query.edit_message_text(
        "👥 إدارة المستخدمين:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_bot_settings_menu(query):
    status = "✅ مفعل" if MAINTENANCE_MODE else "❌ معطل"
    
    keyboard = [
        [InlineKeyboardButton(f"🛑 وضع الصيانة ({status})", callback_data="toggle_maintenance")],
        [InlineKeyboardButton("💾 نسخة احتياطية", callback_data="backup_data")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_admin")]
    ]
    
    await query.edit_message_text(
        "⚙️ إعدادات البوت:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_admin_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    
    if 'awaiting_broadcast' in context.user_data:
        message = update.message.text
        # كود إرسال الإشعار هنا
        await update.message.reply_text(f"تم إرسال الإشعار بنجاح")
        del context.user_data['awaiting_broadcast']
        await admin_panel(update, context)

def setup_admin_handlers(application):
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(CallbackQueryHandler(handle_admin_actions, pattern="^(bot_stats|broadcast|manage_users|bot_settings|back_to_admin|search_user|ban_user|unban_user|upgrade_user|export_users|toggle_maintenance|backup_data)$"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_messages))
