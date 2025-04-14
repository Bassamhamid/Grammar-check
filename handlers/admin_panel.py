from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters
)
from config import Config
import logging
import csv
from io import StringIO
import time
from datetime import datetime

logger = logging.getLogger(__name__)

# حالة البوت
MAINTENANCE_MODE = False
BOT_SETTINGS = {
    "daily_limit": Config.REQUEST_LIMIT,
    "char_limit": Config.CHAR_LIMIT
}

def is_admin(user_id):
    return user_id in Config.ADMIN_IDS if isinstance(Config.ADMIN_IDS, (list, tuple)) else False

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ ليس لديك صلاحية الدخول لهذه اللوحة")
        return

    keyboard = [
        [InlineKeyboardButton("📊 إحصائيات البوت", callback_data="bot_stats")],
        [InlineKeyboardButton("📢 إرسال إشعار عام", callback_data="broadcast")],
        [InlineKeyboardButton("👥 إدارة المستخدمين", callback_data="manage_users")],
        [InlineKeyboardButton("🔧 إعدادات البوت", callback_data="bot_settings")]
    ]
    
    await update.message.reply_text(
        "🛠️ لوحة تحكم المشرفين:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_admin_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if not is_admin(query.from_user.id):
        await query.edit_message_text("⛔ صلاحيات غير كافية")
        return

    action = query.data
    
    if action == "bot_stats":
        stats = await generate_bot_stats()
        await show_stats_menu(query, stats)
    
    elif action == "broadcast":
        await show_broadcast_menu(query)
    
    elif action == "manage_users":
        await show_user_management_menu(query)
    
    elif action == "bot_settings":
        await show_bot_settings_menu(query)
    
    elif action == "back_to_admin":
        await admin_panel(update, context)

async def generate_bot_stats():
    # هذه بيانات وهمية - استبدلها ببيانات حقيقية من قاعدة البيانات
    return {
        "total_users": 1500,
        "active_today": 342,
        "total_requests": 12500,
        "api_users": 87,
        "banned_users": 23,
        "last_backup": datetime.now().strftime("%Y-%m-%d %H:%M")
    }

async def show_stats_menu(query, stats):
    text = (
        "📊 إحصائيات البوت:\n\n"
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

async def show_broadcast_menu(query):
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
        [InlineKeyboardButton(f"🔢 تغيير الحد اليومي ({BOT_SETTINGS['daily_limit']})", callback_data="change_limit")],
        [InlineKeyboardButton(f"✍️ تعديل طول النص ({BOT_SETTINGS['char_limit']})", callback_data="change_chars")],
        [InlineKeyboardButton(f"🛑 وضع الصيانة ({status})", callback_data="toggle_maintenance")],
        [InlineKeyboardButton("💾 نسخة احتياطية", callback_data="backup_data")],
        [InlineKeyboardButton("🔄 إعادة تشغيل", callback_data="restart_bot")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_admin")]
    ]
    
    await query.edit_message_text(
        "⚙️ إعدادات البوت:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_user_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    action = query.data
    
    if action == "search_user":
        await query.edit_message_text(
            "أدخل معرف المستخدم (ID) أو اسم المستخدم:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("إلغاء", callback_data="manage_users")]
            ])
        )
        context.user_data['awaiting_user_search'] = True
    
    elif action == "ban_user":
        await query.edit_message_text(
            "أدخل معرف المستخدم (ID) لحظره:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("إلغاء", callback_data="manage_users")]
            ])
        )
        context.user_data['awaiting_ban'] = True
    
    elif action == "export_users":
        await export_users_data(update, context)

async def handle_bot_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    action = query.data
    
    if action == "change_limit":
        await query.edit_message_text(
            f"أدخل الحد اليومي الجديد (الحالي: {BOT_SETTINGS['daily_limit']}):",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("إلغاء", callback_data="bot_settings")]
            ])
        )
        context.user_data['awaiting_limit_change'] = True
    
    elif action == "toggle_maintenance":
        global MAINTENANCE_MODE
        MAINTENANCE_MODE = not MAINTENANCE_MODE
        await show_bot_settings_menu(query)

async def handle_admin_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    
    if 'awaiting_broadcast' in context.user_data:
        message = update.message.text
        # هنا كود إرسال الرسالة لجميع المستخدمين
        await update.message.reply_text(f"تم إرسال الإشعار لـ 1000 مستخدم")
        del context.user_data['awaiting_broadcast']
        await admin_panel(update, context)
    
    elif 'awaiting_user_search' in context.user_data:
        user_id = update.message.text
        # هنا كود البحث عن المستخدم
        await update.message.reply_text(f"نتائج البحث عن المستخدم {user_id}")
        del context.user_data['awaiting_user_search']
    
    elif 'awaiting_limit_change' in context.user_data:
        try:
            new_limit = int(update.message.text)
            BOT_SETTINGS['daily_limit'] = new_limit
            await update.message.reply_text(f"تم تحديث الحد اليومي إلى {new_limit}")
            del context.user_data['awaiting_limit_change']
        except ValueError:
            await update.message.reply_text("⚠️ يجب إدخال رقم صحيح")

async def export_users_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # بيانات وهمية - استبدلها ببيانات حقيقية من قاعدة البيانات
    users = [
        {"id": 123, "username": "user1", "requests": 10, "status": "active"},
        {"id": 456, "username": "user2", "requests": 5, "status": "banned"}
    ]
    
    csv_file = StringIO()
    fieldnames = ["id", "username", "requests", "status"]
    writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(users)
    
    csv_file.seek(0)
    await query.message.reply_document(
        document=csv_file,
        filename="users_export.csv",
        caption="📁 تصدير بيانات المستخدمين"
    )

def setup_admin_handlers(application):
    application.add_handler(CommandHandler("admin", admin_panel))
    
    # معالجات الأزرار الرئيسية
    application.add_handler(CallbackQueryHandler(handle_admin_actions, 
        pattern="^(bot_stats|broadcast|manage_users|bot_settings|back_to_admin)$"))
    
    # معالجات إدارة المستخدمين
    application.add_handler(CallbackQueryHandler(handle_user_management, 
        pattern="^(search_user|ban_user|unban_user|upgrade_user|export_users)$"))
    
    # معالجات إعدادات البوت
    application.add_handler(CallbackQueryHandler(handle_bot_settings, 
        pattern="^(change_limit|change_chars|toggle_maintenance|backup_data|restart_bot)$"))
    
    # معالجات الرسائل
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, 
        handle_admin_messages))
