from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler, MessageHandler, filters
from utils.limits import limiter
from handlers.subscription import check_subscription, send_subscription_message
from config import Config
import time
import logging

logger = logging.getLogger(__name__)

# حالة المستخدم
NORMAL_TEXT_INPUT = 1

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not await check_subscription(update, context):
            await send_subscription_message(update, context)
            return
        
        user_id = update.effective_user.id
        is_premium = limiter.is_premium_user(user_id)
        user_data = limiter.db.get_user(user_id) or {}
        
        request_count = user_data.get('request_count', 0)
        current_time = time.time()
        reset_hours = Config.PREMIUM_RESET_HOURS if is_premium else Config.RESET_HOURS
        
        reset_time = user_data.get('reset_time')
        if reset_time is None:
            reset_time = current_time + (reset_hours * 3600)
            limiter.db.update_user(user_id, {'reset_time': reset_time})

        try:
            time_left = max(0, float(reset_time) - current_time)
            hours_left = max(0, int(time_left // 3600))
        except (TypeError, ValueError) as e:
            logger.error(f"Error calculating time left: {str(e)}")
            time_left = 0
            hours_left = 0

        welcome_msg = f"""
<b>✨ مرحباً بك في بوت التصحيح النحوي ✨</b>

<b>📊 إحصائيات حسابك:</b>
- عدد الطلبات اليومية: <code>{Config.PREMIUM_REQUEST_LIMIT if is_premium else Config.REQUEST_LIMIT}</code>
- الطلبات المتبقية: <code>{max(0, Config.PREMIUM_REQUEST_LIMIT - request_count) if is_premium else max(0, Config.REQUEST_LIMIT - request_count)}</code>
- الحد الأقصى للنص: <code>{Config.PREMIUM_CHAR_LIMIT if is_premium else Config.CHAR_LIMIT}</code> حرفاً
- وقت تجديد الطلبات: بعد <code>{hours_left}</code> ساعة

<b>💡 اختر طريقة الاستخدام:</b>
"""
        
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
        error_msg = "⚠️ حدث خطأ غير متوقع. جاري إعادة التعيين..."
        
        try:
            if update.callback_query:
                await update.callback_query.edit_message_text(error_msg)
            else:
                await update.message.reply_text(error_msg)
            
            user_id = update.effective_user.id
            limiter.reset_user(user_id)
            await start(update, context)
        except Exception as e:
            logger.error(f"Error in error handling: {str(e)}")

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
        
        # تعيين حالة المستخدم لاستقبال النص
        context.user_data['state'] = NORMAL_TEXT_INPUT
        
    except Exception as e:
        logger.error(f"Error in normal usage guide: {str(e)}")
        await update.callback_query.edit_message_text("⚠️ حدث خطأ في عرض الإرشادات")

async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        user_text = update.message.text
        
        # التحقق من الحد الأقصى للأحرف
        char_limit = Config.PREMIUM_CHAR_LIMIT if limiter.is_premium_user(user_id) else Config.CHAR_LIMIT
        if len(user_text) > char_limit:
            await update.message.reply_text(f"⚠️ النص يتجاوز الحد المسموح ({char_limit} حرفاً)")
            return
        
        # التحقق من عدد الطلبات المتبقية
        if not limiter.can_make_request(user_id):
            await update.message.reply_text("⚠️ لقد استنفذت عدد الطلبات اليومية. يرجى المحاولة لاحقاً.")
            return
        
        # إرسال أزرار الخيارات
        keyboard = [
            [InlineKeyboardButton("🛠 تصحيح الأخطاء النحوية", callback_data=f"correct_{user_id}")],
            [InlineKeyboardButton("🔄 إعادة صياغة النص", callback_data=f"paraphrase_{user_id}")],
            [InlineKeyboardButton("🏠 العودة للرئيسية", callback_data="back_to_start")]
        ]
        
        await update.message.reply_text(
            "📝 اختر الخدمة المطلوبة:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        # حفظ النص مؤقتاً لمعالجته لاحقاً
        context.user_data['last_text'] = user_text
        
    except Exception as e:
        logger.error(f"Error handling text input: {str(e)}")
        await update.message.reply_text("⚠️ حدث خطأ أثناء معالجة النص")

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
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))
