from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler
from utils.limits import limiter
from handlers.subscription import check_subscription, send_subscription_message
from config import Config
import time
import logging

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # التحقق من الاشتراك أولاً
        if not await check_subscription(update, context):
            await send_subscription_message(update, context)
            return
        
        user_id = update.effective_user.id
        
        # الحصول على بيانات المستخدم بشكل آمن
        user_data = limiter.db.get_user(user_id) or {}
        request_count = user_data.get('request_count', 0)
        reset_time = user_data.get('reset_time', time.time() + (Config.RESET_HOURS * 3600))
        
        # حساب الوقت المتبقي والطلبات المتبقية
        current_time = time.time()
        time_left = max(0, reset_time - current_time)
        hours_left = max(0, int(time_left // 3600))
        remaining_uses = max(0, Config.REQUEST_LIMIT - request_count)
        
        # رسالة الترحيب المعدلة
        welcome_msg = f"""
<b>✨ مرحباً بك في بوت التصحيح النحوي ✨</b>

<b>🎯 الخدمات المتاحة:</b>
- تصحيح الأخطاء النحوية والإملائية
- إعادة صياغة النصوص باحترافية

<b>📊 إحصائيات حسابك:</b>
- الطلبات المتبقية: <code>{remaining_uses}/{Config.REQUEST_LIMIT}</code>
- وقت التجديد: بعد <code>{hours_left}</code> ساعة
- الحد الأقصى للنص: <code>{Config.CHAR_LIMIT}</code> حرفاً

<b>💡 اختر طريقة الاستخدام:</b>
"""
        
        # الأزرار الرئيسية
        keyboard = [
            [InlineKeyboardButton("📝 الطريقة العادية (بدون API)", callback_data="normal_usage")],
            [InlineKeyboardButton("🔑 استخدام API شخصي", callback_data="api_usage")]
        ]
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                welcome_msg,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="HTML"
            )
            await update.callback_query.answer()
        else:
            await update.message.reply_text(
                welcome_msg,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="HTML"
            )

    except Exception as e:
        logger.error(f"Error in start command: {str(e)}", exc_info=True)
        error_msg = "⚠️ حدث خطأ غير متوقع. يرجى المحاولة لاحقاً."
        if update.callback_query:
            await update.callback_query.edit_message_text(error_msg)
        else:
            await update.message.reply_text(error_msg)

async def show_normal_usage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        
        usage_guide = """
<b>📌 الطريقة العادية للاستخدام:</b>

1. أرسل النص الذي تريد معالجته مباشرة إلى البوت
مثال: 
<code>"كانت الجو جميله في الخارج"</code>

2. انتظر حتى تظهر لك قائمة الخيارات

3. اختر الخدمة المطلوبة:
   - 🛠 تصحيح الأخطاء النحوية
   - 🔄 إعادة صياغة النص

4. استلم النتيجة المعدلة خلال ثوانٍ
"""
        
        await query.edit_message_text(
            usage_guide,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 العودة للرئيسية", callback_data="back_to_start")]
            ])
        )
        
    except Exception as e:
        logger.error(f"Error in normal usage guide: {str(e)}")
        await update.callback_query.edit_message_text("⚠️ حدث خطأ في عرض الإرشادات")

async def show_api_usage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        
        api_guide = """
<b>🔑 طريقة استخدام API شخصي:</b>

1. احصل على مفتاح API مجاني من:
   <a href="https://openrouter.ai">OpenRouter.ai</a>

2. أرسل المفتاح للبوت بهذا الشكل:
   <code>/setapi مفتاحك_السري</code>

3. المميزات التي ستحصل عليها:
   - {limit} طلب يومياً
   - حد {chars} حرفاً للنص
   - أولوية في المعالجة

4. لإلغاء API الشخصي:
   أرسل <code>/cancelapi</code>
""".format(limit=Config.PREMIUM_REQUEST_LIMIT, chars=Config.PREMIUM_CHAR_LIMIT)
        
        await query.edit_message_text(
            api_guide,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔗 الذهاب لموقع OpenRouter", url="https://openrouter.ai")],
                [InlineKeyboardButton("🏠 العودة للرئيسية", callback_data="back_to_start")]
            ])
        )
        
    except Exception as e:
        logger.error(f"Error in API usage guide: {str(e)}")
        await update.callback_query.edit_message_text("⚠️ حدث خطأ في عرض إرشادات API")

async def back_to_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

def setup_start_handlers(application):
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(show_normal_usage, pattern='^normal_usage$'))
    application.add_handler(CallbackQueryHandler(show_api_usage, pattern='^api_usage$'))
    application.add_handler(CallbackQueryHandler(back_to_start, pattern='^back_to_start$'))
