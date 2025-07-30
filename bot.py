# bot.py

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
    """Возвращает клавиатуру главного меню."""
    keyboard = [
        [KeyboardButton("✨ Gemini 2.5 Pro"), KeyboardButton("⚡ Gemini 2.5 Flash")],
        [KeyboardButton("ℹ️ Помощь")]
    ]
    # resize_keyboard=True делает кнопки компактнее
    # one_time_keyboard=False оставляет клавиатуру видимой после нажатия
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

# --- Обработчики команд ---
async def start(update: Update, context: CallbackContext) -> None:
    """Обработчик команды /start."""
    user = update.effective_user
    # Устанавливаем модель по умолчанию при первом запуске
    context.user_data['model'] = MODEL_FLASH
        
    await update.message.reply_html(
        f"Привет, {user.mention_html()}!\n\n"
        f"Я чат-бот на базе моделей Gemini от Google. "
        f"Сейчас выбрана быстрая модель <b>Flash</b>.\n\n"
        f"Выбери другую модель в меню или просто отправь мне свой вопрос.",
        reply_markup=get_main_menu()
    )

async def help_command(update: Update, context: CallbackContext) -> None:
    """Обработчик команды /help и кнопки 'Помощь'."""
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
    """Переключает модель Gemini по нажатию кнопки."""
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
    """Обрабатывает текстовые сообщения и обращается к Gemini."""
    user_message = update.message.text
    # Получаем модель из данных пользователя, по умолчанию — Flash
    model_name = context.user_data.get('model', MODEL_FLASH)
    model_display_name = "Pro" if "pro" in model_name else "Flash"
    
    # Даем пользователю знать, что бот начал думать
    thinking_message = await update.message.reply_text(
        f"<i>🤖 Думаю с помощью {model_display_name}...</i>",
        parse_mode=ParseMode.HTML
    )

    try:
        model = genai.GenerativeModel(model_name)
        response = await model.generate_content_async(user_message)
        
        # Редактируем сообщение "Думаю..." на готовый ответ
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
# ЭТО КЛЮЧЕВОЕ ИЗМЕНЕНИЕ!
# Мы создаем объект `application` в глобальной области видимости.
# Vercel найдет эту переменную и будет использовать ее для обработки запросов.
application = Application.builder().token(TELEGRAM_TOKEN).build()

# --- Регистрация обработчиков ---
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
# Обрабатываем нажатия на кнопки с моделями
application.add_handler(MessageHandler(filters.Regex(r'^(✨ Gemini 1.5 Pro|⚡ Gemini 1.5 Flash)'), set_model))
application.add_handler(MessageHandler(filters.Regex(r'^ℹ️ Помощь$'), help_command))
# Этот обработчик должен быть последним, чтобы ловить обычный текст
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))