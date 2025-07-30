# bot.py
# --- ЭТОТ КОД ДОЛЖЕН РАБОТАТЬ ---

import os
import logging
import asyncio
import google.generativeai as genai

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackContext,
)
from telegram.constants import ParseMode

# --- Конфигурация ---
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Проверяем, что ключи установлены
if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
    raise ValueError("Переменные окружения TELEGRAM_TOKEN и GEMINI_API_KEY должны быть установлены на Vercel.")

# Конфигурируем Gemini API
genai.configure(api_key=GEMINI_API_KEY)

# --- Логирование ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Актуальные названия моделей
MODEL_PRO = 'gemini-2.5-pro'
MODEL_FLASH = 'gemini-2.5-flash'

# --- Клавиатуры ---
def get_main_menu():
    keyboard = [
        [KeyboardButton("✨ Gemini 1.5 Pro"), KeyboardButton("⚡ Gemini 1.5 Flash")],
        [KeyboardButton("ℹ️ Помощь")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

# --- Обработчики команд ---
async def start(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    context.user_data['model'] = MODEL_FLASH
    await update.message.reply_html(
        f"Привет, {user.mention_html()}!\n\n"
        f"Я чат-бот на базе моделей Gemini от Google. "
        f"Сейчас выбрана быстрая модель <b>Flash</b>.\n\n"
        f"Выбери другую модель в меню или просто отправь мне свой вопрос.",
        reply_markup=get_main_menu()
    )

async def help_command(update: Update, context: CallbackContext) -> None:
    model_key = context.user_data.get('model', MODEL_FLASH)
    model_display_name = "Pro" if "pro" in model_key else "Flash"
    await update.message.reply_text(
        "<b>Как пользоваться ботом:</b>\n\n"
        "1️⃣ Просто отправь мне любой вопрос или текст.\n"
        "2️⃣ Используй кнопки внизу для переключения между моделями:\n"
        f"   • <b>✨ Gemini 1.5 Pro</b>: Мощная модель для сложных и креативных задач.\n"
        f"   • <b>⚡ Gemini 1.5 Flash</b>: Сверхбыстрая модель для мгновенных ответов.\n\n"
        f"<i>Текущая модель: {model_display_name}</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=get_main_menu()
    )

async def set_model(update: Update, context: CallbackContext) -> None:
    text = update.message.text
    if 'Pro' in text:
        context.user_data['model'] = MODEL_PRO
        model_display_name = "Gemini 1.5 Pro"
    else:
        context.user_data['model'] = MODEL_FLASH
        model_display_name = "Gemini 1.5 Flash"
    await update.message.reply_text(
        f"✅ Модель переключена на <b>{model_display_name}</b>. Теперь можешь задавать свой вопрос!",
        parse_mode=ParseMode.HTML,
        reply_markup=get_main_menu()
    )

async def handle_text(update: Update, context: CallbackContext) -> None:
    user_message = update.message.text
    model_name = context.user_data.get('model', MODEL_FLASH)
    model_display_name = "Pro" if "pro" in model_name else "Flash"
    thinking_message = await update.message.reply_text(
        f"<i>🤖 Думаю с помощью {model_display_name}...</i>",
        parse_mode=ParseMode.HTML
    )
    try:
        model = genai.GenerativeModel(model_name)
        response = await model.generate_content_async(user_message)
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=thinking_message.message_id,
            text=response.text
        )
    except Exception as e:
        logger.error(f"Ошибка при обращении к Gemini: {e}")
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=thinking_message.message_id,
            text="❌ Ой, что-то пошло не так. Попробуйте переформулировать запрос или повторите попытку позже."
        )

# --- Создание приложения ---
# ВОТ ЭТА ЧАСТЬ САМАЯ ВАЖНАЯ ДЛЯ VERCEL!
# Мы создаем объект `application` в глобальной области видимости.
application = Application.builder().token(TELEGRAM_TOKEN).build()

# --- Регистрация обработчиков ---
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(MessageHandler(filters.Regex(r'^(✨ Gemini 1.5 Pro|⚡ Gemini 1.5 Flash)'), set_model))
application.add_handler(MessageHandler(filters.Regex(r'^ℹ️ Помощь$'), help_command))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
