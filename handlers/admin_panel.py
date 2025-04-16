from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters
)
from config import Config
from firebase_db import FirebaseDB
from utils.limits import limiter
import logging
import time
from datetime import datetime

logger = logging.getLogger(__name__)
db = FirebaseDB()

def is_admin(username: str) -> bool:
    """التحقق إذا كان المستخدم مشرفاً"""
    if not username:
        return False
    return username.lower() in [admin.lower() for admin in Config.ADMIN_USERNAMES]

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لوحة تحكم المشرف"""
    if not is_admin(update.effective_user.username):
        await update.message.reply_text("⛔ ليس لديك صلاحية الوصول إلى هذه الأداة.")
        return

    keyboard = [
        [InlineKeyboardButton("📊 الإحصاءات", callback_data="admin_stats")],
        [InlineKeyboardButton("👥 إدارة المستخدمين", callback_data="admin_users")],
        [InlineKeyboardButton("📢 إرسال إشعار", callback_data="admin_broadcast")],
        [InlineKeyboardButton("⚙️ الإعدادات", callback_data="admin_settings")]
    ]

    await update.message.reply_text(
        "🛠 لوحة تحكم المشرف - اختر القسم المطلوب:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ------------------- قسم الإحصاءات -------------------
async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض الإحصاءات"""
    query = update.callback_query
    await query.answer()

    stats = db.get_stats()
    total_users = db.count_users()
    premium_users = db.count_premium_users()
    daily_requests = stats.get('daily_requests', 0)
    total_requests = stats.get('total_requests', 0)

    last_reset = stats.get('last_reset', time.time())
    next_reset = last_reset + 86400  # بعد 24 ساعة
    time_left = next_reset - time.time()
    hours_left = max(0, int(time_left // 3600))

    message = (
        "📊 إحصائيات البوت:\n\n"
        f"👥 إجمالي المستخدمين: {total_users}\n"
        f"⭐ المستخدمون المميزون: {premium_users}\n"
        f"📨 الطلبات اليومية: {daily_requests}\n"
        f"📬 إجمالي الطلبات: {total_requests}\n"
        f"⏳ وقت تجديد العداد: بعد {hours_left} ساعة"
    )

    keyboard = [
        [InlineKeyboardButton("🔄 تحديث", callback_data="admin_stats")],
        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="admin_back")]
    ]

    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ------------------- قسم إدارة المستخدمين -------------------
async def show_users_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض قائمة إدارة المستخدمين"""
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("🔍 بحث عن مستخدم", callback_data="admin_search_user")],
        [InlineKeyboardButton("⭐ ترقية مستخدم", callback_data="admin_promote_user")],
        [InlineKeyboardButton("🔓 إلغاء ترقية مستخدم", callback_data="admin_demote_user")],
        [InlineKeyboardButton("⛔ حظر مستخدم", callback_data="admin_ban_user")],
        [InlineKeyboardButton("✅ إلغاء حظر مستخدم", callback_data="admin_unban_user")],
        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="admin_back")]
    ]

    await query.edit_message_text(
        "👥 إدارة المستخدمين - اختر الإجراء المطلوب:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def search_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """البحث عن مستخدم"""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "🔍 أرسل معرف المستخدم (User ID) للبحث عنه:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("↩️ رجوع", callback_data="admin_users")]
        ])
    )
    return "AWAIT_USER_ID"

async def handle_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة معرف المستخدم المدخل"""
    user_id = update.message.text.strip()
    
    try:
        user_id = int(user_id)
    except ValueError:
        await update.message.reply_text("⚠️ معرف المستخدم يجب أن يكون رقماً. يرجى المحاولة مرة أخرى.")
        return "AWAIT_USER_ID"

    user_data = db.get_user(user_id)
    if not user_data:
        await update.message.reply_text("❌ لم يتم العثور على المستخدم.")
        return "AWAIT_USER_ID"

    is_premium = user_data.get('is_premium', False)
    request_count = user_data.get('request_count', 0)
    last_activity = user_data.get('last_activity', 0)
    last_seen = datetime.fromtimestamp(last_activity).strftime('%Y-%m-%d %H:%M') if last_activity else "غير معروف"
    is_banned = db.is_banned(user_id)

    message = (
        f"👤 معلومات المستخدم {user_id}:\n\n"
        f"💎 حالة الاشتراك: {'مميز' if is_premium else 'عادي'}\n"
        f"📊 عدد الطلبات: {request_count}\n"
        f"🕒 آخر نشاط: {last_seen}\n"
        f"🚫 حالة الحظر: {'محظور' if is_banned else 'غير محظور'}"
    )

    keyboard = [
        [
            InlineKeyboardButton("⭐ ترقية" if not is_premium else "🔓 إلغاء ترقية", 
                               callback_data=f"admin_toggle_premium_{user_id}"),
            InlineKeyboardButton("⛔ حظر" if not is_banned else "✅ إلغاء حظر", 
                               callback_data=f"admin_toggle_ban_{user_id}")
        ],
        [InlineKeyboardButton("↩️ رجوع", callback_data="admin_users")]
    ]

    await update.message.reply_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return "ADMIN_PANEL"

async def toggle_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ترقية/إلغاء ترقية مستخدم"""
    query = update.callback_query
    await query.answer()

    user_id = int(query.data.split('_')[-1])
    user_data = db.get_user(user_id)
    is_premium = user_data.get('is_premium', False)

    db.update_user(user_id, {'is_premium': not is_premium})
    
    if not is_premium:
        await query.edit_message_text(f"✅ تم ترقية المستخدم {user_id} إلى مميز.")
    else:
        await query.edit_message_text(f"✅ تم إلغاء ترقية المستخدم {user_id} إلى عادي.")

    await asyncio.sleep(2)
    await show_users_menu(update, context)
    return "ADMIN_PANEL"

async def toggle_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حظر/إلغاء حظر مستخدم"""
    query = update.callback_query
    await query.answer()

    user_id = int(query.data.split('_')[-1])
    is_banned = db.is_banned(user_id)

    if not is_banned:
        db.ban_user(user_id, "حظر من المشرف")
        await query.edit_message_text(f"⛔ تم حظر المستخدم {user_id}.")
    else:
        db.unban_user(user_id)
        await query.edit_message_text(f"✅ تم إلغاء حظر المستخدم {user_id}.")

    await asyncio.sleep(2)
    await show_users_menu(update, context)
    return "ADMIN_PANEL"

# ------------------- قسم الإشعارات -------------------
async def prepare_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تحضير إرسال إشعار"""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "📢 أرسل الرسالة التي تريد إشعار جميع المستخدمين بها:\n\n"
        "يمكنك استخدام تنسيق Markdown مثل:\n"
        "*عريض* _مائل_ [رابط](https://example.com)",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("↩️ رجوع", callback_data="admin_back")]
        ]),
        parse_mode="Markdown"
    )
    return "AWAIT_BROADCAST_MESSAGE"

async def send_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إرسال إشعار لجميع المستخدمين"""
    message = update.message.text
    users = db.get_all_users()
    total = len(users)
    success = 0
    failed = 0

    progress_msg = await update.message.reply_text(f"⏳ جاري الإرسال... 0/{total}")

    for user_id in users:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode="Markdown"
            )
            success += 1
        except Exception as e:
            logger.error(f"Failed to send to {user_id}: {str(e)}")
            failed += 1
        
        # تحديث حالة التقدم كل 10 مستخدمين
        if success % 10 == 0 or (success + failed) == total:
            await progress_msg.edit_text(
                f"⏳ جاري الإرسال... {success + failed}/{total}\n"
                f"✅ نجح: {success} | ❌ فشل: {failed}"
            )
        
        # تأخير لتجنب حظر التيليجرام
        await asyncio.sleep(0.5)

    await progress_msg.edit_text(
        f"✅ تم إرسال الإشعار بنجاح!\n\n"
        f"📊 النتائج:\n"
        f"• إجمالي المستخدمين: {total}\n"
        f"• الرسائل الناجحة: {success}\n"
        f"• الرسائل الفاشلة: {failed}"
    )
    return "ADMIN_PANEL"

# ------------------- قسم الإعدادات -------------------
async def show_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض إعدادات البوت"""
    query = update.callback_query
    await query.answer()

    settings = db.get_settings()
    maintenance_mode = settings.get('maintenance_mode', False)

    message = (
        "⚙️ إعدادات البوت الحالية:\n\n"
        f"📝 حد الحروف (عادي): {settings.get('char_limit', Config.CHAR_LIMIT)}\n"
        f"💎 حد الحروف (مميز): {settings.get('premium_char_limit', Config.PREMIUM_CHAR_LIMIT)}\n"
        f"📨 حد الطلبات (عادي): {settings.get('request_limit', Config.REQUEST_LIMIT)}\n"
        f"📬 حد الطلبات (مميز): {settings.get('premium_request_limit', Config.PREMIUM_REQUEST_LIMIT)}\n"
        f"🔄 وقت تجديد العداد: {settings.get('reset_hours', Config.RESET_HOURS)} ساعة\n"
        f"🚧 وضع الصيانة: {'✅ مفعل' if maintenance_mode else '❌ معطل'}"
    )

    keyboard = [
        [InlineKeyboardButton("🔄 تحديث", callback_data="admin_settings")],
        [InlineKeyboardButton("🚧 تبديل وضع الصيانة", callback_data="admin_toggle_maintenance")],
        [InlineKeyboardButton("📝 تعديل الحدود", callback_data="admin_edit_limits")],
        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="admin_back")]
    ]

    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def toggle_maintenance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تبديل وضع الصيانة"""
    query = update.callback_query
    await query.answer()

    current_mode = db.is_maintenance_mode()
    db.update_settings({'maintenance_mode': not current_mode})

    if not current_mode:
        await query.edit_message_text("✅ تم تفعيل وضع الصيانة. البوت غير متاح الآن للمستخدمين العاديين.")
    else:
        await query.edit_message_text("✅ تم تعطيل وضع الصيانة. البوت متاح الآن لجميع المستخدمين.")

    await asyncio.sleep(2)
    await show_settings(update, context)
    return "ADMIN_PANEL"

async def edit_limits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء تعديل الحدود"""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "📝 أرسل الحدود الجديدة بالشكل التالي:\n\n"
        "حد_العادي حد_المميز حد_طلبات_العادي حد_طلبات_المميز ساعات_التجديد\n\n"
        "مثال:\n"
        "120 500 10 50 24",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("↩️ رجوع", callback_data="admin_settings")]
        ])
    )
    return "AWAIT_LIMITS_INPUT"

async def save_new_limits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حفظ الحدود الجديدة"""
    try:
        parts = update.message.text.split()
        if len(parts) != 5:
            raise ValueError("يجب إدخال 5 قيم")
        
        new_limits = {
            'char_limit': int(parts[0]),
            'premium_char_limit': int(parts[1]),
            'request_limit': int(parts[2]),
            'premium_request_limit': int(parts[3]),
            'reset_hours': int(parts[4])
        }
        
        db.update_settings(new_limits)
        await update.message.reply_text("✅ تم تحديث الحدود بنجاح!")
        
    except ValueError as e:
        await update.message.reply_text(f"❌ خطأ في القيم المدخلة: {str(e)}")
        return "AWAIT_LIMITS_INPUT"
    
    return "ADMIN_PANEL"

# ------------------- التنقل -------------------
async def back_to_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """العودة إلى لوحة التحكم"""
    query = update.callback_query
    await query.answer()
    await admin_panel(update, context)
    return "ADMIN_PANEL"

def setup_admin_handlers(application):
    """إعداد معالجات لوحة المشرف"""
    # الأوامر
    application.add_handler(CommandHandler("admin", admin_panel))
    
    # معالجات الأقسام
    application.add_handler(CallbackQueryHandler(show_stats, pattern="^admin_stats$"))
    application.add_handler(CallbackQueryHandler(show_users_menu, pattern="^admin_users$"))
    application.add_handler(CallbackQueryHandler(prepare_broadcast, pattern="^admin_broadcast$"))
    application.add_handler(CallbackQueryHandler(show_settings, pattern="^admin_settings$"))
    application.add_handler(CallbackQueryHandler(back_to_admin_panel, pattern="^admin_back$"))
    
    # معالجات إدارة المستخدمين
    application.add_handler(CallbackQueryHandler(search_user, pattern="^admin_search_user$"))
    application.add_handler(CallbackQueryHandler(toggle_premium, pattern="^admin_toggle_premium_"))
    application.add_handler(CallbackQueryHandler(toggle_ban, pattern="^admin_toggle_ban_"))
    
    # معالجات الإعدادات
    application.add_handler(CallbackQueryHandler(toggle_maintenance, pattern="^admin_toggle_maintenance$"))
    application.add_handler(CallbackQueryHandler(edit_limits, pattern="^admin_edit_limits$"))
    
    # معالجات الرسائل
    conv_handler = ConversationHandler(
        entry_points=[],
        states={
            "AWAIT_USER_ID": [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_id)],
            "AWAIT_BROADCAST_MESSAGE": [MessageHandler(filters.TEXT & ~filters.COMMAND, send_broadcast)],
            "AWAIT_LIMITS_INPUT": [MessageHandler(filters.TEXT & ~filters.COMMAND, save_new_limits)],
            "ADMIN_PANEL": [CallbackQueryHandler(back_to_admin_panel, pattern="^admin_back$")]
        },
        fallbacks=[CommandHandler("admin", admin_panel)]
    )
    application.add_handler(conv_handler)
