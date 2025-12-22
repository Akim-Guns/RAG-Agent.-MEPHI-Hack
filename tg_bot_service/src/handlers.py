from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters
)
from loguru import logger

from src.session import session_manager
from src.agent_client import agent_client
from src.config import settings


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    session = session_manager.get_or_create_session(user.id)
    
    welcome_text = f"""
👋 Привет, {user.first_name}!

🤖 Я — интеллектуальный ассистент, который поможет вам с различными вопросами.

✨ Возможности:
• Отвечаю на вопросы на основе контекста
• Помогаю с обработкой информации
• Работаю в диалоговом режиме

💡 Как использовать:
Просто напишите ваш вопрос, и я постараюсь помочь!

🔄 Для сброса текущего диалога используйте команду /new

📝 Текущая сессия: {session.session_id}
"""
    
    # Создаем простую клавиатуру
    keyboard = [
        [KeyboardButton("/new - Новая сессия")],
        [KeyboardButton("/help - Помощь")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup
    )
    
    logger.info(f"User {user.id} started bot with session {session.session_id}")


async def new_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /new - сброс сессии"""
    user = update.effective_user
    old_session_id = None
    
    # Получаем старую сессию для логирования
    old_session = session_manager.get_session(user.id)
    if old_session:
        old_session_id = old_session.session_id
    
    # Создаем новую сессию
    new_session = session_manager.create_new_session(user.id)
    
    message = f"""
🔄 Сессия сброшена!

📝 Новая сессия создана:
{new_session.session_id}

Старая сессия: {old_session_id or 'не было'}

Теперь можете задавать вопросы в новом контексте.
"""
    
    await update.message.reply_text(message)
    
    logger.info(f"User {user.id} reset session: {old_session_id} -> {new_session.session_id}")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    help_text = """
📚 Доступные команды:

/start - Начало работы с ботом
/new - Создать новую сессию (сброс контекста)
/help - Эта справка

💡 Как работать с ботом:
1. Просто напишите ваш вопрос
2. Бот отправит его на обработку
3. Получите ответ с учетом контекста диалога

🔗 Каждая сессия имеет уникальный ID:
tg_ваш_id_время_уникальныйкод

Сессия сохраняет историю диалога для лучшего понимания контекста.
"""
    
    await update.message.reply_text(help_text)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    user = update.effective_user
    user_message = update.message.text
    
    # Пропускаем команды (они обрабатываются отдельно)
    if user_message.startswith('/'):
        return
    
    # Получаем или создаем сессию для пользователя
    session = session_manager.get_or_create_session(user.id)
    
    # Показываем статус "печатает"
    await update.message.chat.send_action(action="typing")
    
    logger.info(f"User {user.id} sent message: {user_message[:200]}...")
    
    # Отправляем запрос к Agent Service
    result = await agent_client.invoke(user_message, session.session_id)
    
    if result["success"]:
        # Отправляем ответ пользователю
        await update.message.reply_text(
            result["response"],
            parse_mode="Markdown" if "```" in result["response"] else None
        )
        
        logger.info(f"Successfully responded to user {user.id}")
    else:
        # Отправляем сообщение об ошибке
        error_message = result.get("error", "Произошла неизвестная ошибка")
        await update.message.reply_text(
            f"❌ {error_message}\n\nПопробуйте еще раз через некоторое время."
        )
        
        logger.error(f"Error for user {user.id}: {error_message}")


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Глобальный обработчик ошибок"""
    logger.error(f"Update {update} caused error {context.error}")
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "😕 Произошла непредвиденная ошибка. "
            "Пожалуйста, попробуйте еще раз или используйте /new для начала новой сессии."
        )


# Функция для регистрации всех обработчиков
def setup_handlers(application):
    """Настройка всех обработчиков команд и сообщений"""
    
    # Команды
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("new", new_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # Текстовые сообщения (кроме команд)
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )
    
    # Обработчик ошибок
    application.add_error_handler(error_handler)
    
    logger.info("Handlers setup completed")