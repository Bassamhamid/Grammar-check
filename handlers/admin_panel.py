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

def is_admin(username):
    """التحقق من صلاحية المشرف باستخدام اسم المستخدم"""
    return username and username.lower() in [
        admin.lower() for admin in Config.ADMIN_USERNAMES
    ]

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # الحصول على الرسالة سواء من callback أو message
        message = update.message or update.callback_query.message
        
        username = update.effective_user.username
        if not is_admin(username):
            await message.reply_text("⛔ ليس لديك صلاحية الدخول")
            return

        keyboard = [
            [InlineKeyboardButton("📊 الإحصائيات الحية", callback_data="real_stats")],
            [InlineKeyboardButton("📢 إرسال إشعار عام", callback_data="broadcast")],
            [InlineKeyboardButton("👥 إدارة المستخدمين", callback_data="manage_users")],
            [InlineKeyboardButton("⚙️ الإعدادات", callback_data="settings")]
        ]
        await message.reply_text(
            "🛠️ لوحة تحكم المشرفين:\n\nاختر الخيار المطلوب:",
            reply_markup=InlineKeyboardMarkup(keyboard)
    except Exception as e:
        logger.error(f"Error in admin_panel: {str(e)}", exc_info=True)
        message = update.message or update.callback_query.message
        await message.reply_text("⚠️ حدث خطأ في تحميل لوحة التحكم")

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
            f"📊 الإحصائيات الحية:\n\n"
            f"👥 إجمالي المستخدمين: {total_users}\n"
            f"🟢 نشطين اليوم: {active_today}\n"
            f"⭐ مستخدمين مميزين: {premium_users}\n"
            f"⛔ مستخدمين محظورين: {banned_users}\n"
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

    await query.edit_message_text("⏳ جاري إرسال الإشعار لجميع المستخدمين...")

    for user_id, user_data in users.items():
        try:
            if not user_data.get('is_banned'):
                await context.bot.send_message(chat_id=user_id, text=message)
                success_count += 1
                time.sleep(0.1)  # تجنب حظر الرسائل السريعة
        except Exception as e:
            logger.error(f"Failed to send to {user_id}: {str(e)}")
            failed_count += 1

    await query.edit_message_text(
        f"✅ تم إرسال الإشعار بنجاح!\n\n"
        f"📤 وصل إلى: {success_count} مستخدم\n"
        f"❌ فشل الإرسال لـ: {failed_count} مستخدم"
    )

async def manage_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("🔍 بحث عن مستخدم", callback_data="search_user")],
        [InlineKeyboardButton("📋 قائمة المستخدمين", callback_data="users_list")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_admin")]
    ]

    await query.edit_message_text(
        "👥 إدارة المستخدمين:\n\nاختر العملية المطلوبة:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def search_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['search_mode'] = True

    keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="manage_users")]]
    await query.edit_message_text(
        "🔍 أدخل اسم المستخدم أو الـ ID للبحث:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_search_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('search_mode'):
        return

    search_term = update.message.text.strip()
    context.user_data['search_mode'] = False

    # البحث أولاً بالاسم
    user_data = firebase_db.get_user_by_username(search_term)
    
    # إذا لم يتم العثور بالاسم، جرب البحث بالـ ID
    if not user_data and search_term.isdigit():
        user_data = firebase_db.get_user(int(search_term))

    if not user_data:
        await update.message.reply_text("❌ لم يتم العثور على المستخدم.")
        return

    user_id = next((uid for uid, data in firebase_db.get_all_users().items() 
                   if data.get('username') == search_term or uid == search_term), None)

    text = (
        f"👤 معلومات المستخدم:\n\n"
        f"🆔 ID: {user_id}\n"
        f"👤 اسم المستخدم: @{user_data.get('username', 'غير معروف')}\n"
        f"⭐ حالة المميز: {'نعم' if user_data.get('is_premium') else 'لا'}\n"
        f"⛔ حالة الحظر: {'نعم' if user_data.get('is_banned') else 'لا'}\n"
        f"🕒 آخر نشاط: {user_data.get('last_active', 'غير معروف')}"
    )

    keyboard = [
        [
            InlineKeyboardButton("🚫 حظر", callback_data=f"ban_{user_id}"),
            InlineKeyboardButton("✅ رفع الحظر", callback_data=f"unban_{user_id}")
        ],
        [
            InlineKeyboardButton("⭐ تفعيل مميز", callback_data=f"premium_{user_id}"),
            InlineKeyboardButton("❌ إلغاء المميز", callback_data=f"unpremium_{user_id}")
        ],
        [InlineKeyboardButton("🔙 رجوع", callback_data="manage_users")]
    ]

    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def manage_user_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    action, user_id = data.split('_', 1)

    try:
        if action == "ban":
            firebase_db.ban_user(user_id)
            await query.edit_message_text(f"✅ تم حظر المستخدم {user_id} بنجاح.")
        elif action == "unban":
            firebase_db.unban_user(user_id)
            await query.edit_message_text(f"✅ تم رفع الحظر عن المستخدم {user_id} بنجاح.")
        elif action == "premium":
            firebase_db.update_user(user_id, {"is_premium": True})
            await query.edit_message_text(f"✅ تم تفعيل العضوية المميزة للمستخدم {user_id}.")
        elif action == "unpremium":
            firebase_db.update_user(user_id, {"is_premium": False})
            await query.edit_message_text(f"✅ تم إلغاء العضوية المميزة للمستخدم {user_id}.")
    except Exception as e:
        logger.error(f"Error in manage_user_action: {str(e)}")
        await query.edit_message_text("⚠️ حدث خطأ أثناء تنفيذ العملية")

async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        settings = firebase_db.get_settings()

        text = (
            f"⚙️ إعدادات البوت:\n\n"
            f"🔧 وضع الصيانة: {'✅ مفعل' if settings.get('maintenance_mode') else '❌ معطل'}\n"
            f"📝 حد النص العادي: {settings.get('normal_text_limit', 500)} حرف\n"
            f"📝 حد النص المميز: {settings.get('premium_text_limit', 2000)} حرف\n"
            f"🔢 عدد الطلبات اليومية: {settings.get('daily_limit', 10)}\n"
            f"⏰ وقت تجديد العدادات: {settings.get('renew_time', '00:00')}"
        )

        keyboard = [
            [InlineKeyboardButton("🔄 تبديل وضع الصيانة", callback_data="toggle_maintenance")],
            [InlineKeyboardButton("✏️ تعديل الحدود", callback_data="edit_limits")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_admin")]
        ]

        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        logger.error(f"Error in settings: {str(e)}")
        await query.edit_message_text("⚠️ حدث خطأ في تحميل الإعدادات")

async def toggle_maintenance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        current_settings = firebase_db.get_settings()
        new_mode = not current_settings.get('maintenance_mode', False)
        firebase_db.update_settings({'maintenance_mode': new_mode})
        
        await query.edit_message_text(
            f"✅ تم {'تفعيل' if new_mode else 'تعطيل'} وضع الصيانة بنجاح."
        )
    except Exception as e:
        logger.error(f"Error in toggle_maintenance: {str(e)}")
        await query.edit_message_text("⚠️ حدث خطأ أثناء تغيير وضع الصيانة")

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
    application.add_handler(CallbackQueryHandler(toggle_maintenance, pattern="^toggle_maintenance$"))
    application.add_handler(CallbackQueryHandler(admin_panel, pattern="^back_to_admin$"))
