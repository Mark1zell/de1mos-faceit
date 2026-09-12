import os
import json
import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://mark1zell.github.io/de1mos-faceit/")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не задан в переменных окружения")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    kb = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(
                text="🎮 Открыть De1mos Faceit",
                web_app=WebAppInfo(url=WEBAPP_URL)
            )]
        ],
        resize_keyboard=True
    )
    await message.answer(
        "Добро пожаловать в **De1mos Faceit** для Standoff 2!\n\n"
        "Нажми на кнопку ниже, чтобы открыть приложение и начать играть.",
        reply_markup=kb,
        parse_mode="Markdown"
    )


@dp.message(F.content_type == types.ContentType.WEB_APP_DATA)
async def web_app_data(message: types.Message):
    try:
        data = json.loads(message.web_app_data.data)
        action = data.get("action")

        if action == "find_match":
            await message.answer(
                f"🔍 Поиск матча запущен!\n"
                f"Режим: {data.get('mode', 'Standoff 2')}\n\n"
                f"Уведомление придёт сюда, когда соперник будет найден."
            )
        else:
            await message.answer(f"📩 Данные получены: {json.dumps(data)}")
    except Exception as e:
        logging.error(f"WebApp data error: {e}")
        await message.answer("❌ Ошибка обработки данных.")


async def notify_match_found(user_id: int, match_info: str):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Принять", callback_data=f"accept_{user_id}")],
        [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"decline_{user_id}")]
    ])
    await bot.send_message(
        chat_id=user_id,
        text=f"🎮 **Матч найден!**\n\n{match_info}",
        reply_markup=kb,
        parse_mode="Markdown"
    )


@dp.callback_query(F.data.startswith("accept_"))
async def accept_match(callback: types.CallbackQuery):
    await callback.message.edit_text("✅ Вы приняли матч. Удачи!")
    await callback.answer()


@dp.callback_query(F.data.startswith("decline_"))
async def decline_match(callback: types.CallbackQuery):
    await callback.message.edit_text("❌ Вы отклонили матч.")
    await callback.answer()


async def main():
    logging.info("De1mos Faceit bot started.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
