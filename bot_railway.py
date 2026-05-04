"""
تلجرام بوت — نسخة Railway/VPS
- Deep linking: /start section_0 يفتح القسم مباشرة
- إرسال ملفات مربوطة بكل قسم (file_id من تيليجرام)
"""

import json
import logging
import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes,
)
from telegram.constants import ChatType

BOT_TOKEN   = os.environ.get("BOT_TOKEN",   "ضع_التوكن_هنا")
CHANNEL_ID  = os.environ.get("CHANNEL_ID",  "@your_channel")
GROUP_ID    = os.environ.get("GROUP_ID",    "@your_group")
CONFIG_FILE = "config.json"

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


def load_config() -> dict:
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"welcome": {"title": "المساعد", "body": "", "subscribe_msg": "اشترك أولاً"}, "sections": [], "faqs": []}
    except json.JSONDecodeError as e:
        logger.error(f"خطأ في config.json: {e}")
        return {"welcome": {}, "sections": [], "faqs": []}


def chat_link(chat_id) -> str:
    if isinstance(chat_id, str):
        return f"https://t.me/{chat_id.lstrip('@')}"
    return f"https://t.me/c/{str(chat_id).lstrip('-100')}"


async def is_subscribed(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        ch = await context.bot.get_chat_member(CHANNEL_ID, user_id)
        gr = await context.bot.get_chat_member(GROUP_ID, user_id)
        allowed = {ChatMember.MEMBER, ChatMember.ADMINISTRATOR, ChatMember.OWNER}
        return ch.status in allowed and gr.status in allowed
    except Exception as e:
        logger.error(f"خطأ في التحقق: {e}")
        return False


async def send_subscribe_message(update: Update, config: dict, deep_link_param: str = "") -> None:
    msg = config.get("welcome", {}).get("subscribe_msg", "للاستمرار يجب الاشتراك أولاً")
    callback_after = f"check_subscription|{deep_link_param}" if deep_link_param else "check_subscription"
    keyboard = [
        [
            InlineKeyboardButton("📢 القناة",  url=chat_link(CHANNEL_ID)),
            InlineKeyboardButton("👥 الجروب", url=chat_link(GROUP_ID)),
        ],
        [InlineKeyboardButton("✅ اشتركت، تحقق الآن", callback_data=callback_after)],
    ]
    text = f"🔒 *{msg}*\n\nاشترك في القناة والجروب ثم اضغط ✅ للتحقق!"
    markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text(text, reply_markup=markup, parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")


async def send_section_content(target, context: ContextTypes.DEFAULT_TYPE, section: dict, idx: int) -> None:
    back_btn = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data="back_to_menu")
    ]])
    text      = f"{section['icon']} *{section['name']}*\n\n{section['content']}"
    file_id   = section.get("file_id", "")
    file_type = section.get("file_type", "document")
    is_callback = hasattr(target, "edit_message_text")

    if file_id:
        send_map = {
            "document": context.bot.send_document,
            "photo":    context.bot.send_photo,
            "video":    context.bot.send_video,
            "audio":    context.bot.send_audio,
        }
        send_func = send_map.get(file_type, context.bot.send_document)
        if is_callback:
            chat_id = target.message.chat_id
            try:
                await target.message.delete()
            except Exception:
                pass
        else:
            chat_id = target.chat_id

        kwargs = {file_type: file_id, "caption": text, "reply_markup": back_btn, "parse_mode": "Markdown"}
        await send_func(chat_id=chat_id, **kwargs)
    else:
        if is_callback:
            await target.edit_message_text(text, reply_markup=back_btn, parse_mode="Markdown")
        else:
            await target.reply_text(text, reply_markup=back_btn, parse_mode="Markdown")


def build_main_keyboard(config: dict) -> InlineKeyboardMarkup:
    keyboard = []
    for i, sec in enumerate(config.get("sections", [])):
        keyboard.append([InlineKeyboardButton(f"{sec['icon']} {sec['name']}", callback_data=f"section_{i}")])
    if config.get("faqs"):
        keyboard.append([InlineKeyboardButton("❓ أسئلة شائعة", callback_data="show_faqs")])
    return InlineKeyboardMarkup(keyboard)


async def send_main_menu(source, context: ContextTypes.DEFAULT_TYPE, first_name: str) -> None:
    config  = load_config()
    welcome = config.get("welcome", {})
    text    = f"أهلاً بك *{first_name}* 👋\n\nأنا *{welcome.get('title','المساعد الذكي')}*\n\n{welcome.get('body','اختار من القائمة 👇')}"
    markup  = build_main_keyboard(config)
    if isinstance(source, Update):
        await source.message.reply_text(text, reply_markup=markup, parse_mode="Markdown")
    else:
        await source.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")


def require_subscription(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        if query.data.startswith("check_subscription"):
            return await func(update, context)
        if not await is_subscribed(query.from_user.id, context):
            await query.answer()
            await send_subscribe_message(update, load_config())
            return
        return await func(update, context)
    return wrapper


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.type != ChatType.PRIVATE:
        return
    user       = update.effective_user
    config     = load_config()
    deep_param = context.args[0] if context.args else ""

    if not await is_subscribed(user.id, context):
        await send_subscribe_message(update, config, deep_link_param=deep_param)
        return

    if deep_param.startswith("section_"):
        sections = config.get("sections", [])
        try:
            idx = int(deep_param.split("_")[1])
            await send_section_content(update.message, context, sections[idx], idx)
            return
        except (IndexError, ValueError):
            pass

    await send_main_menu(update, context, user.first_name)


async def check_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query      = update.callback_query
    config     = load_config()
    parts      = query.data.split("|")
    deep_param = parts[1] if len(parts) > 1 else ""

    if await is_subscribed(query.from_user.id, context):
        await query.answer("✅ تم التحقق!")
        if deep_param.startswith("section_"):
            sections = config.get("sections", [])
            try:
                idx = int(deep_param.split("_")[1])
                await send_section_content(query, context, sections[idx], idx)
                return
            except (IndexError, ValueError):
                pass
        await send_main_menu(query, context, query.from_user.first_name)
    else:
        await query.answer("❌ لم نجد اشتراكك! اشترك في القناة والجروب.", show_alert=True)


@require_subscription
async def section_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    config = load_config()
    try:
        idx     = int(query.data.split("_")[1])
        section = config["sections"][idx]
    except (IndexError, ValueError):
        await query.answer("⚠️ القسم غير موجود", show_alert=True)
        return
    await send_section_content(query, context, section, idx)


@require_subscription
async def show_faqs_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    config = load_config()
    faqs   = config.get("faqs", [])
    if not faqs:
        await query.answer("لا توجد أسئلة حتى الآن", show_alert=True)
        return
    keyboard = [[InlineKeyboardButton(f"❓ {f['q']}", callback_data=f"faq_{i}")] for i, f in enumerate(faqs)]
    keyboard.append([InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data="back_to_menu")])
    await query.edit_message_text("❓ *الأسئلة الشائعة*\n\nاضغط على أي سؤال لعرض الإجابة 👇",
                                  reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


@require_subscription
async def faq_answer_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    config = load_config()
    try:
        idx = int(query.data.split("_")[1])
        faq = config["faqs"][idx]
    except (IndexError, ValueError):
        await query.answer("⚠️ السؤال غير موجود", show_alert=True)
        return
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 رجوع للأسئلة",     callback_data="show_faqs")],
        [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="back_to_menu")],
    ])
    await query.edit_message_text(f"❓ *{faq['q']}*\n\n💬 {faq['a']}", reply_markup=keyboard, parse_mode="Markdown")


@require_subscription
async def back_to_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await send_main_menu(query, context, query.from_user.first_name)


async def group_mention_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not message or not message.text:
        return
    bot_username = context.bot.username
    if not bot_username or f"@{bot_username}" not in message.text:
        return
    await message.reply_text(
        f"أهلاً {message.from_user.first_name}! 👋\nللاستفسارات كلمني في البرايفت 👇",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💬 تحدث معي", url=f"https://t.me/{bot_username}")]]),
    )


def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start, filters=filters.ChatType.PRIVATE))
    app.add_handler(CallbackQueryHandler(check_subscription_callback, pattern="^check_subscription"))
    app.add_handler(CallbackQueryHandler(section_callback,            pattern="^section_\\d+$"))
    app.add_handler(CallbackQueryHandler(show_faqs_callback,          pattern="^show_faqs$"))
    app.add_handler(CallbackQueryHandler(faq_answer_callback,         pattern="^faq_\\d+$"))
    app.add_handler(CallbackQueryHandler(back_to_menu_callback,       pattern="^back_to_menu$"))
    app.add_handler(MessageHandler(filters.ChatType.GROUPS & filters.TEXT, group_mention_handler))
    logger.info("✅ البوت شغال على Railway!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
