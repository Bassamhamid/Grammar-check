import logging
import time
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ConversationHandler
)
from config import Config
from firebase_db import FirebaseDB

logger = logging.getLogger(__name__)
db = FirebaseDB()

# حالات المحادثة
ADMIN_MAIN, ADMIN_STATS, ADMIN_USERS, ADMIN_BROADCAST, ADMIN_SETTINGS = range(5)
AWAIT_USER_ID, AWAIT_BROADCAST, AWAIT_LIMITS = range(3)

def is_admin(username: str) -> bool:
    """التحقق من صلاحية المشرف"""
    if not username:
        return False
    return username.lower() in [admin.lower() for admin in Config.ADMIN_USERNAMES]

async def check_maintenance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """التحقق من وضع الصيانة"""
    if db.is_maintenance_mode() and not is_admin(update.effective_user.username):
        if update.callback_query:
            await update.callback_query.answer("⛔ البوت في وضع الصيانة حالياً", show_alert=True)
        else:
            await update.message.reply_text("⛔ البوت في وضع الصيانة حالياً")
        return True
    return False

def generate_stats_message():
    """إنشاء رسالة الإحصاءات مع طابع زمني فريد"""
    stats = db.get_stats()
    timestamp = int(time.time())
    
    return (
        f"📊 إحصائيات البوت (آخر تحديث: {datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M')})\n\n"
        f"👥 إجمالي المستخدمين: {stats.get('total_users', 0)}\n"
        f"⭐ المستخدمون المميزون: {stats.get('premium_users', 0)}\n"
        f"📨 الطلبات اليومية: {stats.get('daily_requests', 0)}\n"
        f"📬 إجمالي الطلبات: {stats.get('total_requests', 0)}\n"
        f"⏳ آخر تجديد: {datetime.fromtimestamp(stats.get('last_reset', timestamp)).strftime('%Y-%m-%d %H:%M')}"
    )

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لوحة التحكم الرئيسية للمشرف"""
    if await check_maintenance(update, context):
        return ConversationHandler.END
    
    if not is_admin(update.effective_user.username):
        await update.message.reply_text("⛔ ليس لديك صلاحية الوصول إلى هذه الأداة.")
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton("📊 الإحصاءات", callback_data="admin_stats")],
        [InlineKeyboardButton("👥 إدارة المستخدمين", callback_data="admin_users")],
        [InlineKeyboardButton("📢 إرسال إشعار", callback_data="admin_broadcast")],
        [InlineKeyboardButton("⚙️ الإعدادات", callback_data="admin_settings")]
    ]

    if update.callback_query:
        await update.callback_query.edit_message_text(
            "🛠 لوحة تحكم المشرف - اختر القسم المطلوب:",
            reply_markup=InlineKeyboardMarkup(keyboard))
        await update.callback_query.answer()
    else:
        await update.message.reply_text(
            "🛠 لوحة تحكم المشرف - اختر القسم المطلوب:",
            reply_markup=InlineKeyboardMarkup(keyboard))

    return ADMIN_MAIN

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض الإحصاءات"""
    if await check_maintenance(update, context):
        return ConversationHandler.END
    
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("🔄 تحديث", callback_data="admin_refresh_stats")],
        [InlineKeyboardButton("🏠 الرئيسية", callback_data="admin_back")]
    ]

    try:
        await query.edit_message_text(
            generate_stats_message(),
            reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        logger.warning(f"No changes in stats: {str(e)}")

    return ADMIN_STATS

async def show_users_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """قائمة إدارة المستخدمين"""
    if await check_maintenance(update, context):
        return ConversationHandler.END
    
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("🔍 بحث عن مستخدم", callback_data="admin_search_user")],
        [InlineKeyboardButton("⭐ ترقية/إلغاء ترقية", callback_data="admin_toggle_premium")],
        [InlineKeyboardButton("⛔ حظر/إلغاء حظر", callback_data="admin_toggle_ban")],
        [InlineKeyboardButton("🏠 الرئيسية", callback_data="admin_back")]
    ]

    await query.edit_message_text(
        "👥 إدارة المستخدمين - اختر الإجراء المطلوب:",
        reply_markup=InlineKeyboardMarkup(keyboard))

    return ADMIN_USERS

async def search_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء عملية البحث عن مستخدم"""
    if await check_maintenance(update, context):
        return ConversationHandler.END
    
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "🔍 أرسل معرف المستخدم (رقم فقط):",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("↩️ رجوع", callback_data="admin_users")]
        ]))

    return AWAIT_USER_ID

async def handle_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة إدخال معرف المستخدم"""
    if await check_maintenance(update, context):
        return ConversationHandler.END
    
    user_id = update.message.text.strip()
    
    try:
        user_id = int(user_id)
    except ValueError:
        await update.message.reply_text("⚠️ يجب أن يكون المعرف رقماً. حاول مرة أخرى.")
        return AWAIT_USER_ID

    user_data = db.get_user(user_id)
    if not user_data:
        await update.message.reply_text("❌ لم يتم العثور على المستخدم.")
        return AWAIT_USER_ID

    is_premium = user_data.get('is_premium', False)
    is_banned = db.is_banned(user_id)
    
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
        f"👤 معلومات المستخدم {user_id}:\n\n"
        f"💎 الحالة: {'مميز' if is_premium else 'عادي'}\n"
        f"🚫 الحظر: {'محظور' if is_banned else 'نشط'}",
        reply_markup=InlineKeyboardMarkup(keyboard))

    return ADMIN_USERS

async def toggle_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تبديل حالة المستخدم المميز"""
    if await check_maintenance(update, context):
        return ConversationHandler.END
    
    query = update.callback_query
    await query.answer()

    user_id = int(query.data.split('_')[3])
    user_data = db.get_user(user_id)
    new_status = not user_data.get('is_premium', False)

    db.update_user(user_id, {'is_premium': new_status})
    
    await query.edit_message_text(
        f"✅ تم {'ترقية' if new_status else 'إلغاء ترقية'} المستخدم {user_id}.")

    return await show_users_menu(update, context)

async def toggle_ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تبديل حالة حظر المستخدم"""
    if await check_maintenance(update, context):
        return ConversationHandler.END
    
    query = update.callback_query
    await query.answer()

    user_id = int(query.data.split('_')[3])
    is_banned = db.is_banned(user_id)

    if is_banned:
        db.unban_user(user_id)
        msg = f"✅ تم إلغاء حظر المستخدم {user_id}."
    else:
        db.ban_user(user_id, "حظر من المشرف")
        msg = f"⛔ تم حظر المستخدم {user_id}."

    await query.edit_message_text(msg)
    return await show_users_menu(update, context)

async def prepare_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تحضير رسالة البث"""
    if await check_maintenance(update, context):
        return ConversationHandler.END
    
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "📢 أرسل الرسالة التي تريد بثها لجميع المستخدمين:\n\n"
        "يمكنك استخدام تنسيق Markdown مثل:\n"
        "*عريض* _مائل_ [رابط](https://example.com)",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("↩️ رجوع", callback_data="admin_back")]
        ]),
        parse_mode="Markdown")

    return AWAIT_BROADCAST

async def send_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إرسال رسالة بث لجميع المستخدمين"""
    if await check_maintenance(update, context):
        return ConversationHandler.END
    
    message = update.message.text
    users = db.get_all_users()
    total = len(users)
    success = 0

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
            logger.error(f"فشل الإرسال لـ {user_id}: {str(e)}")
        
        if success % 10 == 0 or success == total:
            await progress_msg.edit_text(f"⏳ جاري الإرسال... {success}/{total}")

    await progress_msg.edit_text(
        f"✅ تم إرسال الإشعار لـ {success} من {total} مستخدم.")

    return await admin_panel(update, context)

async def show_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض إعدادات البوت"""
    if await check_maintenance(update, context):
        return ConversationHandler.END
    
    query = update.callback_query
    await query.answer()

    settings = db.get_settings()
    
    keyboard = [
        [InlineKeyboardButton("🚧 تبديل وضع الصيانة", callback_data="admin_toggle_maintenance")],
        [InlineKeyboardButton("📝 تعديل الحدود", callback_data="admin_edit_limits")],
        [InlineKeyboardButton("🔄 تحديث", callback_data="admin_refresh_settings")],
        [InlineKeyboardButton("🏠 الرئيسية", callback_data="admin_back")]
    ]

    await query.edit_message_text(
        f"⚙️ إعدادات البوت الحالية:\n\n"
        f"📝 حد الحروف (عادي): {settings.get('char_limit', Config.CHAR_LIMIT)}\n"
        f"💎 حد الحروف (مميز): {settings.get('premium_char_limit', Config.PREMIUM_CHAR_LIMIT)}\n"
        f"📨 حد الطلبات (عادي): {settings.get('request_limit', Config.REQUEST_LIMIT)}\n"
        f"📬 حد الطلبات (مميز): {settings.get('premium_request_limit', Config.PREMIUM_REQUEST_LIMIT)}\n"
        f"🔄 وقت تجديد العداد: {settings.get('reset_hours', Config.RESET_HOURS)} ساعة\n"
        f"🚧 وضع الصيانة: {'✅ مفعل' if settings.get('maintenance_mode', False) else '❌ معطل'}",
        reply_markup=InlineKeyboardMarkup(keyboard))

    return ADMIN_SETTINGS

async def toggle_maintenance_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تبديل وضع الصيانة"""
    query = update.callback_query
    await query.answer()

    current_mode = db.is_maintenance_mode()
    db.update_settings({'maintenance_mode': not current_mode})

    await query.edit_message_text(
        f"✅ تم {'تفعيل' if not current_mode else 'تعطيل'} وضع الصيانة.")
    
    return await show_settings(update, context)

async def edit_limits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء تعديل الحدود"""
    if await check_maintenance(update, context):
        return ConversationHandler.END
    
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "📝 أرسل الحدود الجديدة بالترتيب التالي (كل قيمة في سطر):\n\n"
        "1. حد الحروف العادي\n"
        "2. حد الحروف المميز\n"
        "3. حد الطلبات العادي\n"
        "4. حد الطلبات المميز\n"
        "5. ساعات التجديد",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("↩️ رجوع", callback_data="admin_settings")]
        ]))

    return AWAIT_LIMITS

async def save_limits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حفظ الحدود الجديدة"""
    if await check_maintenance(update, context):
        return ConversationHandler.END
    
    try:
        limits = update.message.text.split('\n')
        if len(limits) != 5:
            raise ValueError("يجب إدخال 5 قيم")
        
        new_settings = {
            'char_limit': int(limits[0]),
            'premium_char_limit': int(limits[1]),
            'request_limit': int(limits[2]),
            'premium_request_limit': int(limits[3]),
            'reset_hours': int(limits[4])
        }
        
        db.update_settings(new_settings)
        await update.message.reply_text("✅ تم تحديث الحدود بنجاح!")
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {str(e)}\nالرجاء المحاولة مرة أخرى.")
        return AWAIT_LIMITS

    return await admin_panel(update, context)

async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """العودة للقائمة الرئيسية"""
    return await admin_panel(update, context)

def setup_admin_handlers(application):
    """إعداد معالجات لوحة المشرف"""
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("admin", admin_panel)],
        states={
            ADMIN_MAIN: [
                CallbackQueryHandler(show_stats, pattern="^admin_stats$"),
                CallbackQueryHandler(show_users_menu, pattern="^admin_users$"),
                CallbackQueryHandler(prepare_broadcast, pattern="^admin_broadcast$"),
                CallbackQueryHandler(show_settings, pattern="^admin_settings$"),
                CallbackQueryHandler(back_to_menu, pattern="^admin_back$")
            ],
            ADMIN_STATS: [
                CallbackQueryHandler(show_stats, pattern="^admin_refresh_stats$"),
                CallbackQueryHandler(back_to_menu, pattern="^admin_back$")
            ],
            ADMIN_USERS: [
                CallbackQueryHandler(search_user, pattern="^admin_search_user$"),
                CallbackQueryHandler(toggle_premium, pattern="^admin_toggle_premium$"),
                CallbackQueryHandler(toggle_premium, pattern="^admin_toggle_premium_\d+$"),
                CallbackQueryHandler(toggle_ban, pattern="^admin_toggle_ban$"),
                CallbackQueryHandler(toggle_ban, pattern="^admin_toggle_ban_\d+$"),
                CallbackQueryHandler(back_to_menu, pattern="^admin_back$"),
                CallbackQueryHandler(show_users_menu, pattern="^admin_users$")
            ],
            ADMIN_BROADCAST: [
                CallbackQueryHandler(prepare_broadcast, pattern="^admin_broadcast$"),
                CallbackQueryHandler(back_to_menu, pattern="^admin_back$")
            ],
            ADMIN_SETTINGS: [
                CallbackQueryHandler(toggle_maintenance_mode, pattern="^admin_toggle_maintenance$"),
                CallbackQueryHandler(edit_limits, pattern="^admin_edit_limits$"),
                CallbackQueryHandler(show_settings, pattern="^admin_refresh_settings$"),
                CallbackQueryHandler(back_to_menu, pattern="^admin_back$")
            ],
            AWAIT_USER_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_id),
                CallbackQueryHandler(show_users_menu, pattern="^admin_users$")
            ],
            AWAIT_BROADCAST: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, send_broadcast),
                CallbackQueryHandler(back_to_menu, pattern="^admin_back$")
            ],
            AWAIT_LIMITS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_limits),
                CallbackQueryHandler(show_settings, pattern="^admin_settings$")
            ]
        },
        fallbacks=[CommandHandler("admin", admin_panel)],
        allow_reentry=True
    )

    application.add_handler(conv_handler)
