
import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types, Router, F
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, Message
from aiogram.filters import Command
from dotenv import load_dotenv
from datetime import datetime

import gspread
from oauth2client.service_account import ServiceAccountCredentials

# === ENV ===
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 813197581

# === GOOGLE SHEETS ===
def save_to_google_sheets(order, username):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("karate-orders-bot-72d967ae279a.json", scope)
    client = gspread.authorize(creds)

    sheet = client.open("Заказы из ТГ бота").sheet1
    sheet.append_row([
        datetime.now().strftime("%Y-%m-%d %H:%M"),
        username,
        order['brand'],
        order['model'],
        order['jacket_size'],
        order['pants_size'],
        "Да" if order['jka_patch'] else "Нет",
        order['name_embroidery'] or "Нет",
        order['label']
    ])

# === TELEGRAM BOT ===
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()

main_menu = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="🛒 Оформить заказ")]],
    resize_keyboard=True
)

order_data = {}
brands = ["Hayate", "Shureido", "Hirota", "Takaido"]
current_field = {}

@router.message(Command("start"))
async def start_command(message: Message):
    await message.answer(
        "Добро пожаловать! \n Я бот для заказа кимоно для каратэ из Японии. \n Я помогу с заказом, тебе нужно лишь ответить на следующие вопросы. \n\n Нажми 'Оформить заказ', чтобы начать.",
        reply_markup=main_menu
    )

@router.message(F.text == "🛒 Оформить заказ")
async def start_order(message: Message):
    order_data[message.chat.id] = {}
    await message.answer("Давай для начала определимся с брендом!", reply_markup=create_brand_buttons())
    current_field[message.chat.id] = 'brand'

def create_brand_buttons():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=brand)] for brand in brands],
        resize_keyboard=True
    )

@router.message()
async def handle_message(message: Message):
    user_id = message.chat.id
    if user_id not in order_data:
        await message.answer("Пожалуйста, нажмите 'Оформить заказ', чтобы начать.")
        return

    field = current_field.get(user_id)
    if not field:
        await message.answer("Что-то пошло не так. Попробуйте начать заказ заново.", reply_markup=main_menu)
        return

    if field == 'brand':
        if message.text not in brands:
            await message.answer("Пожалуйста, выберите бренд из списка.")
            return
        order_data[user_id]['brand'] = message.text
        current_field[user_id] = 'model'
        await message.answer("Введите название модели кимоно:")

    elif field == 'model':
        order_data[user_id]['model'] = message.text
        current_field[user_id] = 'jacket_size'
        await message.answer("Введите размер куртки:")

    elif field == 'jacket_size':
        order_data[user_id]['jacket_size'] = message.text
        current_field[user_id] = 'pants_size'
        await message.answer("Введите размер штанов:")

    elif field == 'pants_size':
        order_data[user_id]['pants_size'] = message.text
        current_field[user_id] = 'jka_patch'
        markup = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Да"), KeyboardButton(text="Нет")]],
            resize_keyboard=True
        )
        await message.answer("Нужна ли нашивка JKA на груди?", reply_markup=markup)

    elif field == 'jka_patch':
        order_data[user_id]['jka_patch'] = message.text == "Да"
        current_field[user_id] = 'name_embroidery'
        await message.answer("Введите имя для вышивки на катакана (если не знаете как пишется, то на английском) или напишите 'Нет':")

    elif field == 'name_embroidery':
        name = message.text
        order_data[user_id]['name_embroidery'] = None if name.lower() == 'нет' else name
        current_field[user_id] = 'label'
        markup = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="JKA"), KeyboardButton(text="WKF"), KeyboardButton(text="Без лейбла"), KeyboardButton(text="Другое")]],
            resize_keyboard=True
        )
        await message.answer("Выберите лейбл:", reply_markup=markup)

    elif field == 'label':
        order_data[user_id]['label'] = message.text
        current_field[user_id] = None
        order = order_data[user_id]

        summary = (
    f"Ваш заказ:\n"
    f"Бренд: {order['brand']}\n"
    f"Модель: {order['model']}\n"
    f"Размер куртки: {order['jacket_size']}\n"
    f"Размер штанов: {order['pants_size']}\n"
    f"Нашивка JKA: {'Да' if order['jka_patch'] else 'Нет'}\n"
    f"Имя для вышивки: {order['name_embroidery'] or 'Нет'}\n"
    f"Лейбл: {order['label']}"
)


        await message.answer(summary)
        await message.answer("Спасибо за заказ! Мы свяжемся с вами для подтверждения.", reply_markup=main_menu)
        await bot.send_message(chat_id=ADMIN_ID, text=f"📥 Новый заказ от @{message.from_user.username}:\n\n{summary}")
        save_to_google_sheets(order, message.from_user.username or "Без username")

dp.include_router(router)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())


@router.message(Command("get_id"))
async def get_id(message: Message):
    await message.answer(f"Ваш ID чата: {message.chat.id}")

