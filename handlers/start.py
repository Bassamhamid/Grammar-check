from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler, MessageHandler, filters
from utils.limits import limiter
from handlers.subscription import check_subscription, send_subscription_message
from config import Config
import time
import logging

logger = logging.getLogger(__name__)

# حالات المستخدم
NORMAL_TEXT_INPUT = 1

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not await check_subscription(update, context):
            await send_subscription_message(update, context)
            return
        
        user_id = update.effective_user.id
        user_data = limiter.db.get_user(user_id) or {}
        request_count = user_data.get('request_count', 0)
        reset_time = user_data.get('reset_time', time.time() + (Config.RESET_HOURS * 3600))
        
        current_time = time.time()
        time_left = max(0, reset_time - current_time)
        hours_left = max(0, int(time_left // 3600))
        remaining_uses = max(0, Config.REQUEST_LIMIT - request_count)
        
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
        char_limit = Config.CHAR_LIMIT
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

async def handle_correction_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = int(query.data.split('_')[1])
        if query.from_user.id != user_id:
            await query.answer("⚠️ هذا الطلب ليس لك!", show_alert=True)
            return
        
        if not limiter.can_make_request(user_id):
            await query.edit_message_text("⚠️ لقد استنفذت عدد الطلبات اليومية. يرجى المحاولة لاحقاً.")
            return
        
        user_text = context.user_data.get('last_text', '')
        if not user_text:
            await query.edit_message_text("⚠️ لم يتم العثور على النص المطلوب معالجته.")
            return
        
        # إرسال رسالة الانتظار
        await query.edit_message_text("⏳ جاري معالجة النص...")
        
        # هنا يجب استدعاء دالة التصحيح من openrouter.py
        # corrected_text = await correct_text(user_text)
        corrected_text = user_text.replace("الجو", "الطقس").replace("جميله", "جميلة")  # مثال مؤقت
        
        # زيادة عداد الطلبات
        limiter.increment_request_count(user_id)
        
        # إرسال النتيجة
        await query.edit_message_text(
            f"📝 <b>النص الأصلي:</b>\n{user_text}\n\n"
            f"🛠 <b>النص المصحح:</b>\n{corrected_text}\n\n"
            f"📊 الطلبات المتبقية: {limiter.get_remaining_requests(user_id)}",
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Error in correction handler: {str(e)}")
        await query.edit_message_text("⚠️ حدث خطأ أثناء تصحيح النص")

async def handle_paraphrase_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = int(query.data.split('_')[1])
        if query.from_user.id != user_id:
            await query.answer("⚠️ هذا الطلب ليس لك!", show_alert=True)
            return
        
        if not limiter.can_make_request(user_id):
            await query.edit_message_text("⚠️ لقد استنفذت عدد الطلبات اليومية. يرجى المحاولة لاحقاً.")
            return
        
        user_text = context.user_data.get('last_text', '')
        if not user_text:
            await query.edit_message_text("⚠️ لم يتم العثور على النص المطلوب معالجته.")
            return
        
        # إرسال رسالة الانتظار
        await query.edit_message_text("⏳ جاري إعادة صياغة النص...")
        
        # هنا يجب استدعاء دالة إعادة الصياغة من openrouter.py
        # paraphrased_text = await paraphrase_text(user_text)
        paraphrased_text = f"يمكن القول أن {user_text}"  # مثال مؤقت
        
        # زيادة عداد الطلبات
        limiter.increment_request_count(user_id)
        
        # إرسال النتيجة
        await query.edit_message_text(
            f"📝 <b>النص الأصلي:</b>\n{user_text}\n\n"
            f"🔄 <b>النص المعاد صياغته:</b>\n{paraphrased_text}\n\n"
            f"📊 الطلبات المتبقية: {limiter.get_remaining_requests(user_id)}",
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Error in paraphrase handler: {str(e)}")
        await query.edit_message_text("⚠️ حدث خطأ أثناء إعادة صياغة النص")

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
    application.add_handler(CallbackQueryHandler(handle_correction_choice, pattern='^correct_'))
    application.add_handler(CallbackQueryHandler(handle_paraphrase_choice, pattern='^paraphrase_'))
