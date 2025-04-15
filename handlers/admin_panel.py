from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler, CallbackQueryHandler, MessageHandler,
    ContextTypes, filters
)
from config import Config
import logging
from datetime import datetime, timedelta
import time
from firebase_db import FirebaseDB

logger = logging.getLogger(__name__)
firebase_db = FirebaseDB()

def is_admin(username):
    """التحقق من صلاحية المشرف باستخدام اسم المستخدم"""
    if not username:
        return False
    return username.lower() in [admin.lower() for admin in Config.ADMIN_USERNAMES]

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message = update.message or update.callback_query.message
        username = update.effective_user.username
        
        if not is_admin(username):
            await message.reply_text("⛔ ليس لديك صلاحية الدخول")
            return

        keyboard = [
            [InlineKeyboardButton("📊 الإحصائيات الحية", callback_data="admin_stats")],
            [InlineKeyboardButton("📢 إرسال إشعار عام", callback_data="admin_broadcast")],
            [InlineKeyboardButton("👥 إدارة المستخدمين", callback_data="admin_manage_users")],
            [InlineKeyboardButton("⚙️ الإعدادات", callback_data="admin_settings")]
        ]
        
        await message.reply_text(
            "🛠️ لوحة تحكم المشرفين:\n\nاختر الخيار المطلوب:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"Error in admin_panel: {str(e)}", exc_info=True)
        await message.reply_text("⚠️ حدث خطأ في تحميل لوحة التحكم")

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    try:
        # تحديث الإحصاءات أولاً
        firebase_db.update_stats()
        
        # جلب البيانات المحدثة
        users = firebase_db.get_all_users()
        stats = firebase_db.get_stats()

        total_users = len(users)
        active_today = sum(1 for u in users.values() 
                        if u.get('last_active', '').startswith(datetime.now().date().isoformat()))
        premium_users = sum(1 for u in users.values() if u.get('is_premium'))
        banned_users = sum(1 for u in users.values() if u.get('is_banned'))

        stats_text = (
            f"📊 الإحصائيات الحية (آخر تحديث: {datetime.now().strftime('%Y-%m-%d %H:%M')}):\n\n"
            f"👥 إجمالي المستخدمين: {total_users}\n"
            f"🟢 نشطين اليوم: {active_today}\n"
            f"⭐ مستخدمين مميزين: {premium_users}\n"
            f"⛔ مستخدمين محظورين: {banned_users}\n"
            f"📨 طلبات اليوم: {stats.get('daily_requests', 0)}\n"
            f"📈 إجمالي الطلبات: {stats.get('total_requests', 0)}"
        )

        keyboard = [
            [InlineKeyboardButton("🔄 تحديث", callback_data="admin_stats")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="admin_back")]
        ]

        await query.edit_message_text(
            text=stats_text,
            reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        logger.error(f"Error in show_stats: {str(e)}", exc_info=True)
        await query.edit_message_text("⚠️ خطأ في جلب الإحصائيات")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['admin_action'] = 'broadcast'
    
    keyboard = [[InlineKeyboardButton("🔙 إلغاء", callback_data="admin_back")]]
    await query.edit_message_text(
        "📝 اكتب الرسالة التي تريد إرسالها لجميع المستخدمين:",
        reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.username):
        return

    action = context.user_data.get('admin_action')
    if not action:
        return await handle_normal_message(update, context)

    if action == 'broadcast':
        await handle_broadcast_message(update, context)
    elif action == 'search_user':
        await handle_search_input(update, context)
    elif action == 'edit_limits':
        await save_new_limit(update, context)

async def handle_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message.text
    context.user_data['broadcast_message'] = message
    context.user_data['admin_action'] = None

    keyboard = [
        [InlineKeyboardButton("✅ تأكيد الإرسال", callback_data="admin_confirm_broadcast")],
        [InlineKeyboardButton("❌ إلغاء", callback_data="admin_back")]
    ]
    
    await update.message.reply_text(
        f"📨 هذه هي الرسالة:\n\n{message}",
        reply_markup=InlineKeyboardMarkup(keyboard))

async def confirm_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    message = context.user_data.get('broadcast_message')
    if not message:
        await query.edit_message_text("⚠️ لا توجد رسالة محددة.")
        return

    users = firebase_db.get_all_users()
    success = 0
    failed = 0
    blocked = 0

    await query.edit_message_text("⏳ جاري إرسال الإشعار لجميع المستخدمين...")

    for user_id, user_data in users.items():
        try:
            # تخطي المستخدمين المحظورين أو الذين لم يبدأوا محادثة
            if user_data.get('is_banned') or not user_data.get('started_chat', True):
                blocked += 1
                continue
                
            await context.bot.send_message(
                chat_id=int(user_id),
                text=f"📢 إشعار عام من الإدارة:\n\n{message}"
            )
            success += 1
            time.sleep(0.3)  # تقليل الضغط على السيرفر
        except Exception as e:
            failed += 1
            logger.error(f"Failed to send to {user_id}: {str(e)}")
            # تحديث حالة المستخدم إذا كان قد حظر البوت
            if "chat not found" in str(e).lower():
                firebase_db.update_user(int(user_id), {'started_chat': False})

    await query.edit_message_text(
        f"✅ تم إرسال الإشعار بنجاح!\n\n"
        f"📤 وصل إلى: {success} مستخدم\n"
        f"🚫 محظور/لم يبدأ محادثة: {blocked} مستخدم\n"
        f"❌ فشل الإرسال لـ: {failed} مستخدم")

async def manage_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("🔍 بحث بالمعرف/اليوزرنيم", callback_data="admin_search_user")],
        [InlineKeyboardButton("📋 قائمة المستخدمين (آخر 50)", callback_data="admin_users_list")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_back")]
    ]

    await query.edit_message_text(
        "👥 إدارة المستخدمين:\n\nاختر العملية المطلوبة:",
        reply_markup=InlineKeyboardMarkup(keyboard))

async def search_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['admin_action'] = 'search_user'
    
    keyboard = [[InlineKeyboardButton("🔙 إلغاء", callback_data="admin_manage_users")]]
    await query.edit_message_text(
        "🔍 أدخل اسم المستخدم أو الـ ID للبحث:",
        reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_search_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    search_term = update.message.text.strip()
    context.user_data['admin_action'] = None

    user_data = None
    user_id = None
    
    # البحث بالمعرف إذا كان رقماً
    if search_term.isdigit():
        user_id = int(search_term)
        user_data = firebase_db.get_user(user_id)
    else:
        # البحث باليوزرنيم
        search_term = search_term.replace('@', '')
        user_data = firebase_db.get_user_by_username(search_term)
        if user_data:
            user_id = next((uid for uid, data in firebase_db.get_all_users().items() 
                          if data.get('username') == search_term), None)

    if not user_data or not user_id:
        await update.message.reply_text("❌ لم يتم العثور على المستخدم.")
        return

    text = (
        f"👤 معلومات المستخدم:\n\n"
        f"🆔 ID: {user_id}\n"
        f"👤 اسم المستخدم: @{user_data.get('username', 'غير معروف')}\n"
        f"📅 تاريخ التسجيل: {datetime.fromtimestamp(user_data.get('timestamp', 0)).strftime('%Y-%m-%d %H:%M')}\n"
        f"⭐ حالة المميز: {'نعم' if user_data.get('is_premium') else 'لا'}\n"
        f"⛔ حالة الحظر: {'نعم' if user_data.get('is_banned') else 'لا'}\n"
        f"🔄 عدد الطلبات: {user_data.get('request_count', 0)}\n"
        f"🕒 آخر نشاط: {user_data.get('last_active', 'غير معروف')}"
    )

    keyboard = [
        [
            InlineKeyboardButton("🚫 حظر" if not user_data.get('is_banned') else "✅ رفع الحظر", 
                               callback_data=f"admin_toggle_ban_{user_id}"),
            InlineKeyboardButton("⭐ تفعيل مميز" if not user_data.get('is_premium') else "❌ إلغاء المميز", 
                               callback_data=f"admin_toggle_premium_{user_id}")
        ],
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_manage_users")]
    ]

    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def manage_user_action(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str):
    query = update.callback_query
    await query.answer()

    user_id = query.data.split('_')[-1]
    
    try:
        if action == 'ban':
            is_banned = not firebase_db.get_user(user_id).get('is_banned', False)
            firebase_db.update_user(user_id, {'is_banned': is_banned})
            action_text = "حظر" if is_banned else "رفع الحظر عن"
        elif action == 'premium':
            is_premium = not firebase_db.get_user(user_id).get('is_premium', False)
            firebase_db.update_user(user_id, {'is_premium': is_premium})
            action_text = "تفعيل العضوية المميزة ل" if is_premium else "إلغاء العضوية المميزة ل"
        
        await query.edit_message_text(f"✅ تم {action_text} المستخدم {user_id} بنجاح.")
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
            f"📝 حد النص العادي: {settings.get('normal_text_limit', Config.CHAR_LIMIT)} حرف\n"
            f"📝 حد النص المميز: {settings.get('premium_text_limit', Config.PREMIUM_CHAR_LIMIT)} حرف\n"
            f"🔢 عدد الطلبات اليومية: {settings.get('daily_limit', Config.REQUEST_LIMIT)}\n"
            f"🔢 عدد طلبات المميز: {settings.get('premium_daily_limit', Config.PREMIUM_REQUEST_LIMIT)}\n"
            f"⏰ وقت تجديد العدادات: كل {Config.RESET_HOURS} ساعة"
        )

        keyboard = [
            [InlineKeyboardButton("🔄 تبديل وضع الصيانة", callback_data="admin_toggle_maintenance")],
            [InlineKeyboardButton("✏️ تعديل الحدود", callback_data="admin_edit_limits")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="admin_back")]
        ]

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard))
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
            f"✅ تم {'تفعيل' if new_mode else 'تعطيل'} وضع الصيانة بنجاح.")
    except Exception as e:
        logger.error(f"Error in toggle_maintenance: {str(e)}")
        await query.edit_message_text("⚠️ حدث خطأ أثناء تغيير وضع الصيانة")

async def edit_limits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['admin_action'] = 'edit_limits'
    
    current_settings = firebase_db.get_settings()
    
    keyboard = [
        [InlineKeyboardButton(f"حد النص العادي ({current_settings.get('normal_text_limit', Config.CHAR_LIMIT)})", 
                            callback_data="admin_edit_normal_limit")],
        [InlineKeyboardButton(f"حد النص المميز ({current_settings.get('premium_text_limit', Config.PREMIUM_CHAR_LIMIT)})", 
                            callback_data="admin_edit_premium_limit")],
        [InlineKeyboardButton(f"الطلبات اليومية ({current_settings.get('daily_limit', Config.REQUEST_LIMIT)})", 
                            callback_data="admin_edit_daily_limit")],
        [InlineKeyboardButton(f"طلبات المميزين ({current_settings.get('premium_daily_limit', Config.PREMIUM_REQUEST_LIMIT)})", 
                            callback_data="admin_edit_premium_daily_limit")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_settings")]
    ]
    
    await query.edit_message_text(
        "⚙️ اختر الحد الذي تريد تعديله:",
        reply_markup=InlineKeyboardMarkup(keyboard))

async def save_new_limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        new_value = int(update.message.text)
        limit_type = context.user_data.get('limit_type')
        
        updates = {}
        if limit_type == 'admin_edit_normal_limit':
            updates['normal_text_limit'] = new_value
        elif limit_type == 'admin_edit_premium_limit':
            updates['premium_text_limit'] = new_value
        elif limit_type == 'admin_edit_daily_limit':
            updates['daily_limit'] = new_value
        elif limit_type == 'admin_edit_premium_daily_limit':
            updates['premium_daily_limit'] = new_value
            
        firebase_db.update_settings(updates)
        await update.message.reply_text("✅ تم تحديث الحد بنجاح!")
        return await settings(update, context)
    except ValueError:
        await update.message.reply_text("⚠️ يجب إدخال رقم صحيح")
    except Exception as e:
        logger.error(f"Error saving limits: {str(e)}")
        await update.message.reply_text("⚠️ حدث خطأ أثناء حفظ التعديلات")

async def handle_normal_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الرسائل العادية للمشرفين"""
    if is_admin(update.effective_user.username):
        await update.message.reply_text("ℹ️ اختر أحد الخيارات من لوحة التحكم")

def setup_admin_handlers(application):
    admin_filter = filters.ChatType.PRIVATE & filters.User(username=Config.ADMIN_USERNAMES)
    
    # تسجيل المعالجات
    application.add_handler(CommandHandler("admin", admin_panel, filters=admin_filter))
    application.add_handler(CallbackQueryHandler(show_stats, pattern="^admin_stats$"))
    application.add_handler(CallbackQueryHandler(broadcast, pattern="^admin_broadcast$"))
    application.add_handler(CallbackQueryHandler(confirm_broadcast, pattern="^admin_confirm_broadcast$"))
    application.add_handler(CallbackQueryHandler(manage_users, pattern="^admin_manage_users$"))
    application.add_handler(CallbackQueryHandler(search_user, pattern="^admin_search_user$"))
    application.add_handler(CallbackQueryHandler(
        lambda u, c: manage_user_action(u, c, 'ban'), 
        pattern="^admin_toggle_ban_"))
    application.add_handler(CallbackQueryHandler(
        lambda u, c: manage_user_action(u, c, 'premium'), 
        pattern="^admin_toggle_premium_"))
    application.add_handler(CallbackQueryHandler(settings, pattern="^admin_settings$"))
    application.add_handler(CallbackQueryHandler(toggle_maintenance, pattern="^admin_toggle_maintenance$"))
    application.add_handler(CallbackQueryHandler(edit_limits, pattern="^admin_edit_limits$"))
    application.add_handler(CallbackQueryHandler(
        lambda u, c: (u, c.__setitem__('limit_type', u.callback_query.data)) or edit_limits(u, c),
        pattern="^admin_edit_.*_limit$"))
    application.add_handler(MessageHandler(
        admin_filter & filters.TEXT & ~filters.COMMAND,
        handle_admin_message
    ))
    application.add_handler(CallbackQueryHandler(admin_panel, pattern="^admin_back$"))
