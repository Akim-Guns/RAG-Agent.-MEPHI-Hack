from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import aiohttp
import asyncio
import logging

# Конфигурация
API_URL = "http://localhost:8000"
TELEGRAM_TOKEN = "your_token"

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

async def query_agent(text: str, user_id: str) -> dict:
    """Запрос к AI агенту"""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{API_URL}/query",
            json={"query": text, "user_id": user_id}
        ) as response:
            return await response.json()

@dp.message(Command("start", "help"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Привет! Я AI-агент для поиска статей. "
        "Задайте мне вопрос по интересующей теме, и я найду релевантные статьи."
    )

@dp.message()
async def handle_message(message: types.Message):
    """Обработка всех сообщений"""
    # Показываем индикатор набора
    await bot.send_chat_action(message.chat.id, "typing")
    
    try:
        # Отправляем запрос агенту
        response = await query_agent(
            text=message.text,
            user_id=str(message.from_user.id)
        )
        
        # Отправляем ответ пользователю
        await message.answer(response["response"])
        
        # Если есть статьи, отправляем их отдельно
        if response.get("articles"):
            articles_text = "\n\n".join([
                f"📚 {art['title']}\n🔗 {art.get('url', 'Нет ссылки')}"
                for art in response["articles"][:3]  # Ограничиваем количество
            ])
            await message.answer(f"Найденные статьи:\n{articles_text}")
            
    except Exception as e:
        logging.error(f"Error: {e}")
        await message.answer("Извините, произошла ошибка. Попробуйте позже.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())