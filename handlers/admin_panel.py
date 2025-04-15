from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from config import Config
import logging
from datetime import datetime
from firebase_admin import db
from utils.limits import limiter
import time

logger = logging.getLogger(__name__)

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
            [InlineKeyboardButton("📢 إرسال إشعار عام", callback_data="real_broadcast")],
            [InlineKeyboardButton("👥 إدارة المستخدمين", callback_data="real_users")],
            [InlineKeyboardButton("⚙️ الإعدادات", callback_data="real_settings")],
            [InlineKeyboardButton("🔄 تحديث كل البيانات", callback_data="refresh_all")]
        ]
        
        await update.message.reply_text(
            "🛠️ لوحة تحكم المشرفين:\n\n"
            "اختر الخيار المطلوب:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        logger.error(f"Error in admin_panel: {str(e)}", exc_info=True)
        await update.message.reply_text("⚠️ حدث خطأ في تحميل لوحة التحكم")

async def get_user_stats():
    try:
        users_ref = db.reference('users')
        stats_ref = db.reference('stats')
        
        users = users_ref.get() or {}
        stats = stats_ref.get() or {}

        total_users = len(users)
        active_today = 0
        premium_users = 0
        banned_users = 0
        
        today = datetime.now().date().isoformat()
        for user_id, user_data in users.items():
            last_active = user_data.get('last_active', '')
            if isinstance(last_active, str) and last_active.startswith(today):
                active_today += 1
            if user_data.get('is_premium', False):
                premium_users += 1
            if user_data.get('is_banned', False):
                banned_users += 1

        return {
            'total_users': total_users,
            'active_today': active_today,
            'premium_users': premium_users,
            'banned_users': banned_users,
            'total_requests': stats.get('total_requests', 0),
            'daily_requests': stats.get('daily_requests', 0)
        }
    except Exception as e:
        logger.error(f"Error getting user stats: {str(e)}", exc_info=True)
        return None

async def handle_real_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    try:
        stats = await get_user_stats()
        if stats is None:
            raise Exception("Failed to get stats")

        stats_text = (
            "📊 الإحصائيات الحية:\n\n"
            f"👥 إجمالي المستخدمين: {stats['total_users']}\n"
            f"🟢 نشطين اليوم: {stats['active_today']}\n"
            f"📨 طلبات اليوم: {stats['daily_requests']}\n"
            f"📈 إجمالي الطلبات: {stats['total_requests']}\n"
            f"⭐ مستخدمين مميزين: {stats['premium_users']}\n"
            f"⛔ مستخدمين محظورين: {stats['banned_users']}\n\n"
            f"🔄 آخر تحديث: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        keyboard = [
            [InlineKeyboardButton("🔄 تحديث", callback_data="real_stats")],
            [InlineKeyboardButton("📤 تصدير البيانات", callback_data="export_data")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_admin")]
        ]

        await query.edit_message_text(
            stats_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        logger.error(f"Error in real stats: {str(e)}", exc_info=True)
        await query.edit_message_text("⚠️ حدث خطأ في جلب الإحصائيات")

async def get_recent_users(limit=10):
    try:
        users_ref = db.reference('users')
        users = users_ref.limit_to_last(limit).get() or {}
        
        users_list = []
        for user_id, user_data in users.items():
            users_list.append(
                f"👤 {user_data.get('username', 'مجهول')} (ID: {user_id}) - "
                f"{'⭐' if user_data.get('is_premium', False) else '🔹'}"
                f"{'⛔' if user_data.get('is_banned', False) else ''}"
            )
        return users_list
    except Exception as e:
        logger.error(f"Error getting recent users: {str(e)}", exc_info=True)
        return None

async def handle_real_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    try:
        users_list = await get_recent_users()
        if users_list is None:
            raise Exception("Failed to get users")

        users_text = "👥 آخر 10 مستخدمين:\n\n" + "\n".join(users_list) if users_list else "⚠️ لا يوجد مستخدمين مسجلين"

        keyboard = [
            [InlineKeyboardButton("🔄 تحديث", callback_data="real_users")],
            [InlineKeyboardButton("🔍 بحث عن مستخدم", callback_data="search_user")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_admin")]
        ]

        await query.edit_message_text(
            users_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        logger.error(f"Error in users management: {str(e)}", exc_info=True)
        await query.edit_message_text("⚠️ حدث خطأ في جلب بيانات المستخدمين")

async def handle_real_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    try:
        stats = limiter.db.get_stats()
        settings_text = (
            "⚙️ إعدادات البوت:\n\n"
            f"🔧 وضع الصيانة: {'✅ مفعل' if MAINTENANCE_MODE else '❌ معطل'}\n"
            f"📝 حد النص العادي: {Config.CHAR_LIMIT} حرف\n"
            f"💎 حد النص المميز: {Config.PREMIUM_CHAR_LIMIT} حرف\n"
            f"📨 طلبات اليوم: {stats.get('daily_requests', 0)}\n"
            f"🔄 وقت التجديد: كل {Config.RESET_HOURS} ساعة"
        )

        keyboard = [
            [
                InlineKeyboardButton("🔧 تبديل الصيانة", callback_data="toggle_maintenance"),
                InlineKeyboardButton("🔄 تحديث", callback_data="real_settings")
            ],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_admin")]
        ]

        await query.edit_message_text(
            settings_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    except Exception as e:
        logger.error(f"Error in settings: {str(e)}", exc_info=True)
        await query.edit_message_text("⚠️ حدث خطأ في جلب الإعدادات")

async def handle_real_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    try:
        await query.edit_message_text(
            "📢 أرسل الرسالة للإشعار العام:\n\n"
            "يمكنك استخدام تنسيق HTML مثل:\n"
            "<b>عريض</b>, <i>مائل</i>, <code>كود</code>\n\n"
            "أو /cancel للإلغاء",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("إلغاء", callback_data="back_to_admin")]
            ]),
            parse_mode="HTML"
        )
        context.user_data['awaiting_broadcast'] = True
    except Exception as e:
        logger.error(f"Error in broadcast setup: {str(e)}", exc_info=True)

async def send_real_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.user_data.get('awaiting_broadcast'):
            return

        message = update.message.text_markdown_v2 if update.message.text else ""

        if not message:
            await update.message.reply_text("⚠️ يرجى إرسال رسالة صالحة")
            return

        if message.lower() == '/cancel':
            await update.message.reply_text("تم إلغاء الإرسال")
            await admin_panel(update, context)
            return

        users_ref = db.reference('users')
        users = users_ref.get() or {}

        sent_count = 0
        failed_count = 0
        total_users = len(users)

        status_msg = await update.message.reply_text(f"⏳ جاري الإرسال... 0/{total_users}")

        for user_id, user_data in users.items():
            try:
                if user_data.get('is_banned', False):
                    continue

                await context.bot.send_message(
                    chat_id=int(user_id),
                    text=message,
                    parse_mode="MarkdownV2"
                )
                sent_count += 1

                if sent_count % 10 == 0:
                    await status_msg.edit_text(f"⏳ جاري الإرسال... {sent_count}/{total_users}")

            except Exception as e:
                logger.error(f"Failed to send to {user_id}: {str(e)}")
                failed_count += 1

            if Config.MAX_BROADCAST_USERS and sent_count >= Config.MAX_BROADCAST_USERS:
                break

        report = (
            f"✅ تقرير الإرسال:\n\n"
            f"📤 تم الإرسال بنجاح: {sent_count}\n"
            f"❌ فشل في الإرسال: {failed_count}\n"
            f"📩 الإجمالي: {sent_count + failed_count}"
        )

        await status_msg.edit_text(report)
        await admin_panel(update, context)

    except Exception as e:
        logger.error(f"Broadcast error: {str(e)}", exc_info=True)
        await update.message.reply_text("⚠️ حدث خطأ جسيم أثناء الإرسال")
    finally:
        context.user_data.pop('awaiting_broadcast', None)

async def handle_refresh_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("جارٍ تحديث جميع البيانات...")
    
    try:
        await handle_real_stats(update, context)
    except Exception as e:
        logger.error(f"Error in refresh all: {str(e)}", exc_info=True)

def setup_admin_handlers(application):
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(CallbackQueryHandler(handle_real_stats, pattern="^real_stats$"))
    application.add_handler(CallbackQueryHandler(handle_real_broadcast, pattern="^real_broadcast$"))
    application.add_handler(CallbackQueryHandler(handle_real_users, pattern="^real_users$"))
    application.add_handler(CallbackQueryHandler(handle_real_settings, pattern="^real_settings$"))
    application.add_handler(CallbackQueryHandler(handle_refresh_all, pattern="^refresh_all$"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, send_real_broadcast))
