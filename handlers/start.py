from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler, MessageHandler, filters
from utils.limits import limiter
from utils.openrouter import query_openrouter
from handlers.subscription import check_subscription, send_subscription_message
from config import Config
import time
import logging

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id

        if not await check_subscription(update, context):
            await send_subscription_message(update, context)
            return

        is_premium = limiter.is_premium_user(user_id)
        user_data = limiter.db.get_user(user_id) or {}

        # إذا المستخدم جديد (أي لا يوجد له بيانات)
        if not user_data:
            limiter.db.update_stats({
                'total_users': limiter.db.count_users(),
                'premium_users': limiter.db.count_premium_users()
            })

        current_time = time.time()
        request_limit = Config.PREMIUM_REQUEST_LIMIT if is_premium else Config.REQUEST_LIMIT
        char_limit = Config.PREMIUM_CHAR_LIMIT if is_premium else Config.CHAR_LIMIT
        reset_hours = Config.PREMIUM_RESET_HOURS if is_premium else Config.RESET_HOURS

        request_count = user_data.get('request_count', 0)
        reset_time = user_data.get('reset_time', current_time + (reset_hours * 3600))

        try:
            time_left = max(0, float(reset_time) - current_time)
            hours_left = max(0, int(time_left // 3600))
        except (TypeError, ValueError) as e:
            logger.error(f"Error calculating time left: {str(e)}")
            time_left = reset_hours * 3600
            hours_left = reset_hours
            reset_time = current_time + time_left
            limiter.db.update_user(user_id, {'reset_time': reset_time})

        remaining_uses = max(0, request_limit - request_count)

        welcome_msg = f"""
<b>✍️ مساعد الكتابة AI</b>

<b>📊 إحصائيات حسابك:</b>
- الطلبات المتبقية: <code>{remaining_uses}/{request_limit}</code>
- وقت التجديد: بعد <code>{hours_left}</code> ساعة
- الحد الأقصى للنص: <code>{char_limit}</code> حرفاً

<b>💡 الخدمات المتاحة:</b>
- تصحيح الأخطاء النحوية والإملائية
- إعادة صياغة النصوص باحترافية

📬 للاستفسارات: @info_all_tech
"""

        keyboard = [
            [InlineKeyboardButton("📝 الطريقة العادية", callback_data="normal_usage")],
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
        
        await query.edit_message_text(
            "📝 أرسل النص الذي تريد معالجته الآن:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 الرئيسية", callback_data="back_to_start")]
            ])
        )
        
    except Exception as e:
        logger.error(f"Error in normal usage guide: {str(e)}")
        await query.edit_message_text("⚠️ حدث خطأ في عرض الإرشادات")

async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        is_premium = limiter.is_premium_user(user_id)
        user_text = update.message.text
        
        # تحديد الحدود بناءً على نوع المستخدم
        char_limit = Config.PREMIUM_CHAR_LIMIT if is_premium else Config.CHAR_LIMIT
        request_limit = Config.PREMIUM_REQUEST_LIMIT if is_premium else Config.REQUEST_LIMIT
        
        if not user_text or len(user_text.strip()) == 0:
            await update.message.reply_text("⚠️ يرجى إرسال نص صالح للمعالجة")
            return
            
        if len(user_text) > char_limit:
            await update.message.reply_text(f"⚠️ النص يتجاوز الحد المسموح ({char_limit} حرفاً)")
            return
        
        user_data = limiter.db.get_user(user_id) or {}
        if user_data.get('request_count', 0) >= request_limit:
            await update.message.reply_text(
    f"⚠️ عذراً، الحد الأقصى المسموح به هو {char_limit} حرفاً.\n"
    f"عدد أحرف نصك: {len(user_text)}"
            )
            return
        
        keyboard = [
            [InlineKeyboardButton("🛠 تصحيح الأخطاء", callback_data=f"correct_{user_id}")],
            [InlineKeyboardButton("🔄 إعادة صياغة", callback_data=f"paraphrase_{user_id}")],
            [InlineKeyboardButton("🏠 الرئيسية", callback_data="back_to_start")]
        ]
        
        await update.message.reply_text(
            "📝 اختر الخدمة المطلوبة:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        context.user_data['last_text'] = user_text.strip()
        
    except Exception as e:
        logger.error(f"Error handling text input: {str(e)}")
        await update.message.reply_text("⚠️ حدث خطأ أثناء معالجة النص")

async def handle_correction_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        
        user_id = int(query.data.split('_')[1])
        is_premium = limiter.is_premium_user(user_id)
        user_text = context.user_data.get('last_text', '')
        
        if not user_text:
            await query.edit_message_text("⚠️ لم يتم العثور على النص المطلوب معالجته.")
            return
        
        await query.edit_message_text("⏳ جاري تصحيح الأخطاء النحوية...")
        
        # استدعاء OpenRouter للتصحيح
        prompt = f"صحح الأخطاء النحوية والإملائية في النص التالي بدون ذكر النص الأصلي:\n{user_text}"
        corrected_text = query_openrouter(prompt, user_id if is_premium else None)
        
        # تحديث عدد الطلبات
        current_user_data = limiter.db.get_user(user_id) or {}
        new_count = current_user_data.get('request_count', 0) + 1
        limiter.db.update_user(user_id, {
            'request_count': new_count,
            'reset_time': current_user_data.get('reset_time', time.time() + (Config.PREMIUM_RESET_HOURS * 3600 if is_premium else Config.RESET_HOURS * 3600))
        })
        
        await query.edit_message_text(
            f"🛠 <b>النص المصحح:</b>\n{corrected_text}",
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
        is_premium = limiter.is_premium_user(user_id)
        user_text = context.user_data.get('last_text', '')
        
        if not user_text:
            await query.edit_message_text("⚠️ لم يتم العثور على النص المطلوب معالجته.")
            return
        
        await query.edit_message_text("⏳ جاري إعادة صياغة النص...")
        
        # استدعاء OpenRouter لإعادة الصياغة
        prompt = f"أعد صياغة النص التالي بلغة عربية سليمة بدون ذكر النص الأصلي:\n{user_text}"
        paraphrased_text = query_openrouter(prompt, user_id if is_premium else None)
        
        # تحديث عدد الطلبات
        current_user_data = limiter.db.get_user(user_id) or {}
        new_count = current_user_data.get('request_count', 0) + 1
        limiter.db.update_user(user_id, {
            'request_count': new_count,
            'reset_time': current_user_data.get('reset_time', time.time() + (Config.PREMIUM_RESET_HOURS * 3600 if is_premium else Config.RESET_HOURS * 3600))
        })
        
        await query.edit_message_text(
            f"🔄 <b>النص المعاد صياغته:</b>\n{paraphrased_text}",
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Error in paraphrase handler: {str(e)}")
        await query.edit_message_text("⚠️ حدث خطأ أثناء إعادة صياغة النص")

async def show_api_usage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        
        api_guide = f"""
<b>🔑 طريقة استخدام API شخصي:</b>

1. احصل على مفتاح API مجاني من:
   <a href="https://openrouter.ai">OpenRouter.ai</a>

2. أرسل المفتاح للبوت بهذا الشكل:
   <code>/setapi مفتاحك_السري</code>

3. المميزات التي ستحصل عليها:
   - {Config.PREMIUM_REQUEST_LIMIT} طلب يومياً
   - حد {Config.PREMIUM_CHAR_LIMIT} حرفاً للنص
   - أولوية في المعالجة

📬 للاستفسارات: @info_all_tech
"""
        
        await query.edit_message_text(
            api_guide,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔗 الذهاب لموقع OpenRouter", url="https://openrouter.ai")],
                [InlineKeyboardButton("🏠 الرئيسية", callback_data="back_to_start")]
            ])
        )
        
    except Exception as e:
        logger.error(f"Error in API usage guide: {str(e)}")
        await query.edit_message_text("⚠️ حدث خطأ في عرض إرشادات API")

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
