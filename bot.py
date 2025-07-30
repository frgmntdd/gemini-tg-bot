# bot.py

import os
import logging
import google.generativeai as genai
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# Настройка логирования для отладки
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получаем токены из переменных окружения (более безопасный способ)
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Конфигурируем Gemini API
genai.configure(api_key=GEMINI_API_KEY)

# --- Клавиатуры и главное меню ---
def get_main_menu():
    """Возвращает клавиатуру главного меню."""
    keyboard = [
        [KeyboardButton("✨ Gemini 2.5 Pro"), KeyboardButton("⚡ Gemini 2.5 Flash")],
        [KeyboardButton("ℹ️ Помощь")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# --- Функции-обработчики команд ---
async def start(update: Update, context: CallbackContext) -> None:
    """Обработчик команды /start. Приветствует пользователя и показывает меню."""
    user = update.effective_user
    # Устанавливаем модель по умолчанию при старте
    context.user_data['model'] = 'gemini-2.5-flash'
    await update.message.reply_html(
        f"Привет, {user.mention_html()}!\n\n"
        f"Я твой личный помощник на базе моделей Gemini от Google. "
        f"Сейчас я использую быструю модель <b>Flash</b>.\n\n"
        f"Просто отправь мне свой вопрос или выбери другую модель в меню ниже.",
        reply_markup=get_main_menu()
    )

async def help_command(update: Update, context: CallbackContext) -> None:
    """Обработчик команды /help и кнопки 'Помощь'."""
    current_model_name = "Gemini 2.5 Pro" if context.user_data.get('model') == 'gemini-2.5-pro' else "Gemini 2.5 Flash"
    await update.message.reply_text(
        "Это бот, использующий нейросети Google Gemini.\n\n"
        "• Чтобы пообщаться, просто напиши мне сообщение.\n"
        "• Используй кнопки внизу, чтобы переключаться между моделями:\n"
        "  - `Gemini 2.5 Pro`: для сложных и креативных задач.\n"
        "  - `Gemini 2.5 Flash`: для быстрых ответов.\n\n"
        f"Текущая модель: <b>{current_model_name}</b>.",
        parse_mode='HTML',
        reply_markup=get_main_menu()
    )

# --- Обработчики сообщений ---
async def handle_message(update: Update, context: CallbackContext) -> None:
    """Основной обработчик текстовых сообщений."""
    text = update.message.text

    # Проверяем, не нажал ли пользователь на кнопку меню
    if text == "✨ Gemini 2.5 Pro":
        context.user_data['model'] = 'gemini-2.5-pro'
        await update.message.reply_text("Модель переключена на ✨ Gemini 2.5 Pro. Задавайте ваш вопрос!", reply_markup=get_main_menu())
        return
    elif text == "⚡ Gemini 2.5 Flash":
        context.user_data['model'] = 'gemini-2.5-flash'
        await update.message.reply_text("Модель переключена на ⚡ Gemini 2.5 Flash. Я готов отвечать быстро!", reply_markup=get_main_menu())
        return
    elif text == "ℹ️ Помощь":
        await help_command(update, context)
        return

    # Если это обычное сообщение, отправляем его в Gemini
    model_name = context.user_data.get('model', 'gemini-2.5-flash') # По умолчанию Flash
    await update.message.reply_text(f"Думаю над вашим вопросом с помощью {model_name.split('-')[1]}...")

    try:
        # Инициализируем модель
        model = genai.GenerativeModel(model_name)
        # Генерируем ответ
        response = await model.generate_content_async(text)

        # Отправляем ответ пользователю
        await update.message.reply_text(response.text, reply_markup=get_main_menu())

    except Exception as e:
        logger.error(f"Ошибка при работе с Gemini: {e}")
        await update.message.reply_text("Произошла ошибка. Попробуйте изменить запрос или повторить попытку позже.")


# --- Основная функция запуска бота ---
def main() -> None:
    """Запуск бота."""
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Запуск бота
    # Для Vercel мы будем использовать вебхуки, поэтому эта строка для локального теста
    # application.run_polling()
    # Для Vercel нам нужна будет другая конфигурация, которую мы сделаем в файле vercel.json

if __name__ == '__main__':
    # Эта часть не будет выполняться на Vercel, но полезна для локальной разработки
    main()