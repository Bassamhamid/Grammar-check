from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
)
from config import Config
import logging
from datetime import datetime
from firebase_admin import db
from utils.limits import limiter
from firebase_db import FirebaseDB
import time

logger = logging.getLogger(__name__)
firebase_db = FirebaseDB()

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
            [InlineKeyboardButton("⚙️ الإعدادات", callback_data="settings")]
        ]
        await update.message.reply_text(
            "🛠️ لوحة تحكم المشرفين:\n\nاختر الخيار المطلوب:",
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
            if user_data.get('last_active', '').startswith(today):
                active_today += 1
            if user_data.get('is_premium'):
                premium_users += 1
            if user_data.get('is_banned'):
                banned_users += 1

        stats_text = (
            f"👥 إجمالي المستخدمين: {total_users}\n"
            f"🟢 نشطين اليوم: {active_today}\n"
            f"⭐ مميزين: {premium_users}\n"
            f"⛔ محظورين: {banned_users}\n"
            f"📨 طلبات اليوم: {stats.get('daily_requests', 0)}\n"
            f"📈 إجمالي الطلبات: {stats.get('total_requests', 0)}"
        )

        keyboard = [
            [InlineKeyboardButton("🔄 تحديث", callback_data="real_stats")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_admin")]
        ]

        await query.edit_message_text(stats_text, reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        logger.error(f"Error in show_stats: {str(e)}", exc_info=True)
        await query.edit_message_text("⚠️ خطأ في جلب الإحصائيات")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['broadcast_mode'] = True

    keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_to_admin")]]
    await query.edit_message_text(
        "📝 اكتب الرسالة التي تريد إرسالها لجميع المستخدمين:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('broadcast_mode'):
        return

    context.user_data['broadcast_message'] = update.message.text
    context.user_data['broadcast_mode'] = False

    keyboard = [
        [InlineKeyboardButton("✅ تأكيد الإرسال", callback_data="confirm_broadcast")],
        [InlineKeyboardButton("❌ إلغاء", callback_data="back_to_admin")]
    ]
    await update.message.reply_text(
        f"📨 هذه هي الرسالة:\n\n{update.message.text}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def confirm_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    message = context.user_data.get('broadcast_message')
    if not message:
        await query.edit_message_text("⚠️ لا توجد رسالة محددة.")
        return

    users = firebase_db.get_all_users()
    success_count = 0
    failed_count = 0

    for user_id in users.keys():
        try:
            await context.bot.send_message(chat_id=user_id, text=message)
            success_count += 1
            time.sleep(0.1)
        except:
            failed_count += 1

    await query.edit_message_text(
        f"✅ تم إرسال الإشعار.\n\n"
        f"📤 وصل إلى: {success_count}\n"
        f"❌ لم يصل: {failed_count}"
    )

async def manage_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("🔍 بحث عن مستخدم", callback_data="search_user")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_admin")]
    ]

    await query.edit_message_text(
        "👥 إدارة المستخدمين:\n\nاختر العملية:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def search_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['search_mode'] = True

    keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="manage_users")]]
    await query.edit_message_text("🆔 أدخل معرف المستخدم (User ID):", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_search_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('search_mode'):
        return

    user_id = update.message.text.strip()
    user_data = firebase_db.get_user(user_id)
    context.user_data['search_mode'] = False

    if not user_data:
        await update.message.reply_text("❌ لم يتم العثور على هذا المستخدم.")
        return

    text = (
        f"👤 معلومات المستخدم:\n"
        f"🆔: {user_id}\n"
        f"⭐ مميز: {'نعم' if user_data.get('is_premium') else 'لا'}\n"
        f"⛔ محظور: {'نعم' if user_data.get('is_banned') else 'لا'}"
    )

    keyboard = [
        [InlineKeyboardButton("🚫 حظر", callback_data=f"ban_{user_id}"),
         InlineKeyboardButton("✅ رفع الحظر", callback_data=f"unban_{user_id}")],
        [InlineKeyboardButton("⭐ تفعيل مميز", callback_data=f"premium_{user_id}"),
         InlineKeyboardButton("❌ إلغاء المميز", callback_data=f"unpremium_{user_id}")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="manage_users")]
    ]

    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def manage_user_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    if data.startswith("ban_"):
        user_id = data.split("_")[1]
        firebase_db.update_user(user_id, {"is_banned": True})
        await query.edit_message_text(f"🚫 تم حظر المستخدم {user_id}.")

    elif data.startswith("unban_"):
        user_id = data.split("_")[1]
        firebase_db.update_user(user_id, {"is_banned": False})
        await query.edit_message_text(f"✅ تم رفع الحظر عن {user_id}.")

    elif data.startswith("premium_"):
        user_id = data.split("_")[1]
        firebase_db.update_user(user_id, {"is_premium": True})
        await query.edit_message_text(f"⭐ تم تفعيل المميز للمستخدم {user_id}.")

    elif data.startswith("unpremium_"):
        user_id = data.split("_")[1]
        firebase_db.update_user(user_id, {"is_premium": False})
        await query.edit_message_text(f"❌ تم إلغاء المميز عن {user_id}.")

async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    settings = firebase_db.get_settings()

    text = (
        f"⚙️ إعدادات النظام:\n"
        f"🔄 وضع الصيانة: {'مفعل' if settings.get('maintenance_mode') else 'معطل'}\n"
        f"✏️ حد نص المستخدم العادي: {settings.get('normal_text_limit', 500)}\n"
        f"✏️ حد نص المميز: {settings.get('premium_text_limit', 2000)}\n"
        f"📊 عدد الطلبات اليومي: {settings.get('daily_limit', 10)}\n"
        f"⏰ وقت التجديد: {settings.get('renew_time', '00:00')}"
    )

    keyboard = [
        [InlineKeyboardButton("🔄 تبديل وضع الصيانة", callback_data="toggle_maintenance")],
        [InlineKeyboardButton("✏️ تغيير حد نص المستخدم", callback_data="edit_normal_limit")],
        [InlineKeyboardButton("✏️ تغيير حد نص المميز", callback_data="edit_premium_limit")],
        [InlineKeyboardButton("📊 تغيير عدد الطلبات اليومي", callback_data="edit_daily_limit")],
        [InlineKeyboardButton("⏰ تغيير وقت التجديد", callback_data="edit_renew_time")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_admin")]
    ]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

def setup_admin_handlers(application):
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(CallbackQueryHandler(show_stats, pattern="^real_stats$"))
    application.add_handler(CallbackQueryHandler(broadcast, pattern="^broadcast$"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_broadcast_message))
    application.add_handler(CallbackQueryHandler(confirm_broadcast, pattern="^confirm_broadcast$"))
    application.add_handler(CallbackQueryHandler(manage_users, pattern="^manage_users$"))
    application.add_handler(CallbackQueryHandler(search_user, pattern="^search_user$"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_search_input))
    application.add_handler(CallbackQueryHandler(manage_user_action, pattern="^ban_|^unban_|^premium_|^unpremium_"))
    application.add_handler(CallbackQueryHandler(settings, pattern="^settings$"))
    application.add_handler(CallbackQueryHandler(admin_panel, pattern="^back_to_admin$"))
