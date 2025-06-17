
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
BOT_TOKEN = os.getenv("7222903418:AAEmFCewivYsudEXTDEVdDAUrRNtKVDvuSo")
ADMIN_USERNAME = "@nikibelka"

# === GOOGLE SHEETS ===
def save_to_google_sheets(order, username):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("karate-orders-bot-72d967ae279a.json", scope)
    client = gspread.authorize(creds)

    sheet = client.open("Karate Orders").sheet1
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
        "Привет! Я бот для заказа японского кимоно для каратэ. Нажми 'Оформить заказ', чтобы начать.",
        reply_markup=main_menu
    )

@router.message(F.text == "🛒 Оформить заказ")
async def start_order(message: Message):
    order_data[message.chat.id] = {}
    await message.answer("Выберите бренд:", reply_markup=create_brand_buttons())
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
        await message.answer("Нужна ли нашивка JKA?", reply_markup=markup)

    elif field == 'jka_patch':
        order_data[user_id]['jka_patch'] = message.text == "Да"
        current_field[user_id] = 'name_embroidery'
        await message.answer("Введите имя для вышивки (или напишите 'Нет'):")

    elif field == 'name_embroidery':
        name = message.text
        order_data[user_id]['name_embroidery'] = None if name.lower() == 'нет' else name
        current_field[user_id] = 'label'
        markup = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="JKA"), KeyboardButton(text="WKF"), KeyboardButton(text="Без лейбла")]],
            resize_keyboard=True
        )
        await message.answer("Выберите лейбл:", reply_markup=markup)

    elif field == 'label':
        order_data[user_id]['label'] = message.text
        current_field[user_id] = None
        order = order_data[user_id]

        summary = (
            f"Ваш заказ:
"
            f"Бренд: {order['brand']}
"
            f"Модель: {order['model']}
"
            f"Размер куртки: {order['jacket_size']}
"
            f"Размер штанов: {order['pants_size']}
"
            f"Нашивка JKA: {'Да' if order['jka_patch'] else 'Нет'}
"
            f"Имя для вышивки: {order['name_embroidery'] or 'Нет'}
"
            f"Лейбл: {order['label']}"
        )

        await message.answer(summary)
        await message.answer("Спасибо за заказ! Мы свяжемся с вами для подтверждения.", reply_markup=main_menu)
        await bot.send_message(chat_id=ADMIN_USERNAME, text=f"📥 Новый заказ от @{message.from_user.username}:

{summary}")
        save_to_google_sheets(order, message.from_user.username or "Без username")

dp.include_router(router)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
