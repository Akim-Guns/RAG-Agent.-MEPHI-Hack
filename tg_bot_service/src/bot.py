import asyncio
from loguru import logger
from telegram import Update
from telegram.ext import ApplicationBuilder

from src.config import settings
from src.handlers import setup_handlers


async def main():
    """Основная функция запуска бота"""
    
    # Настройка логирования
    logger.add(
        "logs/bot.log",
        rotation="10 MB",
        retention="30 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
    )
    
    logger.info("Starting Telegram Bot...")
    logger.info(f"Agent Service URL: {settings.AGENT_SERVICE_URL}")
    
    # Создаем приложение бота
    application = (
        ApplicationBuilder()
        .token(settings.TELEGRAM_TOKEN)
        .concurrent_updates(True)
        .build()
    )
    
    # Настраиваем обработчики
    setup_handlers(application)
    
    # Запускаем бота
    await application.initialize()
    await application.start()
    await application.updater.start_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )
    
    logger.info("Bot started successfully! Press Ctrl+C to stop.")
    
    # Бесконечный цикл
    try:
        while True:
            await asyncio.sleep(3600)  # Спим 1 час
    except KeyboardInterrupt:
        logger.info("Received stop signal, shutting down...")
    finally:
        await application.stop()


if __name__ == "__main__":
    asyncio.run(main())