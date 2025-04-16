import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from config import Config
from firebase_db import FirebaseDB

logger = logging.getLogger(__name__)
db = FirebaseDB()

def is_admin(username: str) -> bool:
    """التحقق من صلاحية المشرف"""
    if not username:
        return False
    return username.lower() in [admin.lower() for admin in Config.ADMIN_USERNAMES]

async def check_admin(update: Update):
    """تحقق أساسي من صلاحية المشرف"""
    if not is_admin(update.effective_user.username):
        await update.message.reply_text("⛔ ليس لديك صلاحية الوصول إلى هذه الأداة.")
        return False
    return True

async def admin_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض قائمة أوامر المشرف"""
    if not await check_admin(update):
        return

    help_text = """
    🛠 أوامر إدارة المشرفين:
    
    📊 /admin_stats - عرض إحصاءات البوت
    🔍 /admin_find [user_id] - البحث عن مستخدم
    ⭐ /admin_promote [user_id] - ترقية مستخدم
    🔓 /admin_demote [user_id] - إلغاء ترقية
    ⛔ /admin_ban [user_id] - حظر مستخدم
    ✅ /admin_unban [user_id] - إلغاء حظر
    📢 /admin_broadcast [الرسالة] - إرسال إشعار للجميع
    🚧 /admin_maintenance [on/off] - وضع الصيانة
    ⚙️ /admin_limits [عادي مميز طلبات_عادي طلبات_مميز ساعات] - ضبط الحدود
    
    أمثلة:
    /admin_find 123456789
    /admin_broadcast مرحبا بكم في التحديث الجديد
    /admin_limits 500 2000 10 50 24
    """
    await update.message.reply_text(help_text)

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض إحصاءات البوت"""
    if not await check_admin(update):
        return

    stats = db.get_stats()
    message = (
        f"📊 إحصائيات البوت:\n"
        f"👥 إجمالي المستخدمين: {stats.get('total_users', 0)}\n"
        f"⭐ المستخدمون المميزون: {stats.get('premium_users', 0)}\n"
        f"📨 الطلبات اليومية: {stats.get('daily_requests', 0)}\n"
        f"📬 إجمالي الطلبات: {stats.get('total_requests', 0)}\n"
        f"⏳ آخر تجديد: {datetime.fromtimestamp(stats.get('last_reset', 0)).strftime('%Y-%m-%d %H:%M')}"
    )
    await update.message.reply_text(message)

async def admin_find_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """البحث عن مستخدم"""
    if not await check_admin(update):
        return

    if not context.args:
        await update.message.reply_text("⚠️ يرجى إدخال معرف المستخدم بعد الأمر")
        return

    try:
        user_id = int(context.args[0])
        user_data = db.get_user(user_id)
        
        if not user_data:
            await update.message.reply_text("❌ المستخدم غير موجود")
            return

        is_premium = user_data.get('is_premium', False)
        is_banned = db.is_banned(user_id)
        
        message = (
            f"👤 معلومات المستخدم:\n"
            f"🆔 المعرف: {user_id}\n"
            f"💎 الحالة: {'مميز' if is_premium else 'عادي'}\n"
            f"🚫 الحظر: {'محظور' if is_banned else 'نشط'}\n"
            f"📅 تاريخ التسجيل: {datetime.fromtimestamp(user_data.get('join_date', 0)).strftime('%Y-%m-%d')}"
        )
        await update.message.reply_text(message)
    except ValueError:
        await update.message.reply_text("⚠️ معرف المستخدم يجب أن يكون رقماً")

async def admin_manage_user(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str):
    """إدارة المستخدمين (ترقية/حظر/إلخ)"""
    if not await check_admin(update):
        return

    if not context.args:
        await update.message.reply_text(f"⚠️ يرجى إدخال معرف المستخدم بعد الأمر")
        return

    try:
        user_id = int(context.args[0])
        user_data = db.get_user(user_id)
        
        if not user_data:
            await update.message.reply_text("❌ المستخدم غير موجود")
            return

        if action == "promote":
            db.update_user(user_id, {'is_premium': True})
            await update.message.reply_text(f"✅ تم ترقية المستخدم {user_id}")
        elif action == "demote":
            db.update_user(user_id, {'is_premium': False})
            await update.message.reply_text(f"🔓 تم إلغاء ترقية المستخدم {user_id}")
        elif action == "ban":
            db.ban_user(user_id, "حظر من المشرف")
            await update.message.reply_text(f"⛔ تم حظر المستخدم {user_id}")
        elif action == "unban":
            db.unban_user(user_id)
            await update.message.reply_text(f"✅ تم إلغاء حظر المستخدم {user_id}")
            
    except ValueError:
        await update.message.reply_text("⚠️ معرف المستخدم يجب أن يكون رقماً")
    except Exception as e:
        logger.error(f"Error in admin action: {str(e)}")
        await update.message.reply_text("❌ حدث خطأ أثناء تنفيذ العملية")

async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إرسال إشعار لجميع المستخدمين"""
    if not await check_admin(update):
        return

    if not context.args:
        await update.message.reply_text("⚠️ يرجى كتابة الرسالة بعد الأمر")
        return

    message = " ".join(context.args)
    users = db.get_all_users()
    total = len(users)
    success = 0

    progress_msg = await update.message.reply_text(f"⏳ جاري الإرسال... 0/{total}")

    for user_id in users:
        try:
            await context.bot.send_message(chat_id=user_id, text=message)
            success += 1
        except Exception as e:
            logger.error(f"فشل الإرسال لـ {user_id}: {str(e)}")
        
        if success % 10 == 0 or success == total:
            await progress_msg.edit_text(f"⏳ جاري الإرسال... {success}/{total}")

    await progress_msg.edit_text(f"✅ تم إرسال الإشعار لـ {success} من {total} مستخدم")

async def admin_maintenance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إدارة وضع الصيانة"""
    if not await check_admin(update):
        return

    if not context.args:
        current = db.is_maintenance_mode()
        await update.message.reply_text(f"🚧 وضع الصيانة: {'مفعل' if current else 'معطل'}")
        return

    mode = context.args[0].lower()
    if mode in ['on', '1', 'true']:
        db.update_settings({'maintenance_mode': True})
        await update.message.reply_text("✅ تم تفعيل وضع الصيانة")
    elif mode in ['off', '0', 'false']:
        db.update_settings({'maintenance_mode': False})
        await update.message.reply_text("✅ تم تعطيل وضع الصيانة")
    else:
        await update.message.reply_text("⚠️ استخدم /admin_maintenance [on/off]")

async def admin_set_limits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ضبط حدود البوت"""
    if not await check_admin(update):
        return

    if len(context.args) != 5:
        await update.message.reply_text("⚠️ يرجى إدخال 5 قيم:\n/admin_limits [حد_عادي حد_مميز طلبات_عادي طلبات_مميز ساعات]")
        return

    try:
        new_limits = {
            'char_limit': int(context.args[0]),
            'premium_char_limit': int(context.args[1]),
            'request_limit': int(context.args[2]),
            'premium_request_limit': int(context.args[3]),
            'reset_hours': int(context.args[4])
        }
        db.update_settings(new_limits)
        await update.message.reply_text("✅ تم تحديث الحدود بنجاح!")
    except ValueError:
        await update.message.reply_text("⚠️ جميع القيم يجب أن تكون أرقاماً صحيحة")
    except Exception as e:
        logger.error(f"Error setting limits: {str(e)}")
        await update.message.reply_text("❌ حدث خطأ أثناء تحديث الحدود")

def setup_admin_commands(application):
    """إعداد أوامر المشرفين"""
    application.add_handler(CommandHandler("admin", admin_help))
    application.add_handler(CommandHandler("admin_stats", admin_stats))
    application.add_handler(CommandHandler("admin_find", admin_find_user))
    
    # إدارة المستخدمين
    application.add_handler(CommandHandler("admin_promote", 
        lambda u, c: admin_manage_user(u, c, "promote")))
    application.add_handler(CommandHandler("admin_demote", 
        lambda u, c: admin_manage_user(u, c, "demote")))
    application.add_handler(CommandHandler("admin_ban", 
        lambda u, c: admin_manage_user(u, c, "ban")))
    application.add_handler(CommandHandler("admin_unban", 
        lambda u, c: admin_manage_user(u, c, "unban")))
    
    # البث والإعدادات
    application.add_handler(CommandHandler("admin_broadcast", admin_broadcast))
    application.add_handler(CommandHandler("admin_maintenance", admin_maintenance))
    application.add_handler(CommandHandler("admin_limits", admin_set_limits))
