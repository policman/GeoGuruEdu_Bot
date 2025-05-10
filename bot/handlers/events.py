from aiogram import types
from aiogram.dispatcher import Dispatcher, FSMContext
from aiogram.dispatcher.filters import Text
from datetime import datetime
import asyncpg
import os
from dotenv import load_dotenv
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from bot.keyboards.menu import main_reply_keyboard
from bot.states.event_states import EventCreation
from bot.keyboards.events import event_menu_keyboard, confirmation_keyboard
from bot.services.event_repo import insert_event, add_participant
from bot.database.user_repo import get_user_by_telegram_id
from bot.keyboards.common import confirm_photos_keyboard, confirm_skip_video_keyboard
from bot.keyboards.common import my_events_keyboard
from bot.services.event_repo import get_created_events, get_active_events, get_archive_events



load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")



# Старт раздела "События"
async def events_entry(message: types.Message):
    await message.answer("Выберите действие:", reply_markup=event_menu_keyboard)

# Начало создания события
async def start_event_creation(message: types.Message, state: FSMContext):
    await message.answer("Введите название события:")
    await EventCreation.waiting_for_title.set()

async def set_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("Введите описание события:")
    await EventCreation.waiting_for_description.set()

async def set_description(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer("Введите дату (формат: дд.мм.гггг или дд.мм.гггг-дд.мм.гггг или список дат через запятую):")
    await EventCreation.waiting_for_dates.set()

async def set_dates(message: types.Message, state: FSMContext):
    text = message.text.strip()
    try:
        if '-' in text:
            start_str, end_str = text.split('-')
            start_date = datetime.strptime(start_str.strip(), "%d.%m.%Y").date()
            end_date = datetime.strptime(end_str.strip(), "%d.%m.%Y").date()
        elif ',' in text:
            dates = [datetime.strptime(d.strip(), "%d.%m.%Y").date() for d in text.split(',')]
            start_date = dates[0]
            end_date = dates[-1]
        else:
            start_date = end_date = datetime.strptime(text.strip(), "%d.%m.%Y").date()
        await state.update_data(start_date=start_date, end_date=end_date)
        await message.answer("Кто организатор события? (ФИО или название организации):")
        await EventCreation.waiting_for_organizers.set()
    except Exception:
        await message.answer("Некорректный формат даты. Повторите:")

async def set_organizers(message: types.Message, state: FSMContext):
    await state.update_data(organizers=message.text)
    await message.answer("Введите цену участия в рублях или 'бесплатно':")
    await EventCreation.waiting_for_price.set()

async def set_price(message: types.Message, state: FSMContext):
    text = message.text.lower().strip()
    price = 0 if text == "бесплатно" else int(text)
    await state.update_data(price=price)
    await message.answer("Прикрепите фото (1–5):")
    await EventCreation.waiting_for_photos.set()

from bot.keyboards.common import confirm_photos_keyboard

async def set_photos(message: types.Message, state: FSMContext):
    if not message.photo:
        await message.answer("Отправьте хотя бы одну фотографию")
        return

    data = await state.get_data()
    current_photos = data.get("photos", [])
    current_photos.append(message.photo[-1].file_id)
    await state.update_data(photos=current_photos)

    count = len(current_photos)
    if count >= 5:
        await message.answer("Фото загружены. Отправьте видео (0–2) или нажмите 'Пропустить':", reply_markup=confirm_skip_video_keyboard)
        await EventCreation.waiting_for_videos.set()
    else:
        await message.answer(f"Фото получено ({count}/5). Можете отправить ещё или нажмите '✅ Готово':", reply_markup=confirm_photos_keyboard)

async def confirm_photos(message: types.Message, state: FSMContext):
    data = await state.get_data()
    photos = data.get("photos", [])
    if not photos:
        await message.answer("Сначала загрузите хотя бы одно фото.")
        return

    await message.answer("Теперь отправьте видео (0–2) или нажмите 'Пропустить':", reply_markup=confirm_skip_video_keyboard)
    await EventCreation.waiting_for_videos.set()


async def set_videos(message: types.Message, state: FSMContext):
    data = await state.get_data()
    current_videos = data.get("videos", [])

    if message.text and message.text.lower() == 'пропустить':
        await state.update_data(videos=[])
    elif message.video:
        current_videos.append(message.video.file_id)
        await state.update_data(videos=current_videos)

        if len(current_videos) < 2:
            await message.answer("Можете прикрепить ещё одно видео или нажмите '✅ Готово':", reply_markup=confirm_photos_keyboard)
            return
    else:
        await message.answer("Прикрепите видео или нажмите 'Пропустить'")
        return

    # Показываем событие в одном сообщении
    data = await state.get_data()
    price_display = 'бесплатно' if data['price'] == 0 else f"{data['price']}₽"

    media = []
    if data.get("photos"):
        media.append(types.InputMediaPhoto(media=data['photos'][0], caption=(
            f"📌 <b>{data['title']}</b>\n"
            f"📝 {data['description']}\n"
            f"📅 {data['start_date']} — {data['end_date']}\n"
            f"👤 Организатор: {data['organizers']}\n"
            f"💰 Стоимость: {price_display}"
        ), parse_mode="HTML"))

        for photo_id in data['photos'][1:]:
            media.append(types.InputMediaPhoto(media=photo_id))

    if media:
        await message.answer_media_group(media)

    for video_id in data.get("videos", []):
        await message.answer_video(video_id)

    await message.answer("Проверьте информацию и подтвердите создание:", reply_markup=confirmation_keyboard)
    await EventCreation.confirmation.set()


async def confirm_event(message: types.Message, state: FSMContext):
    if message.text != "✅ Готово":
        await message.answer("Пожалуйста, нажмите кнопку ✅ Готово для подтверждения.")
        return
    data = await state.get_data()

    conn = await asyncpg.connect(DATABASE_URL)

    user = await get_user_by_telegram_id(conn, message.from_user.id)
    if not user:
        await message.answer("❌ Ошибка: пользователь не найден.")
        await conn.close()
        return

    event_data = {
        "author_id": user["id"],
        "title": data["title"],
        "description": data["description"],
        "start_date": data["start_date"],
        "end_date": data["end_date"],
        "organizers": data["organizers"],
        "price": data["price"],
        "photos": data["photos"],
        "videos": data["videos"],
        "is_draft": False,
    }

    event_id = await insert_event(conn, event_data)
    await add_participant(conn, event_id, user["id"])
    await conn.close()

    await message.answer("✅ Событие успешно сохранено!", reply_markup=event_menu_keyboard)
    await state.finish()


async def cancel_creation(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("Создание события отменено.", reply_markup=event_menu_keyboard)


    # Кнопка Назад (в гл меню)
async def back_to_main_from_events(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("🔙 Возврат в главное меню", reply_markup=main_reply_keyboard)

    # мои события
async def show_my_events_menu(message: types.Message, state: FSMContext):
    await message.answer("Мои события:", reply_markup=my_events_keyboard)

# Вывод активных событий
async def show_active_events(message: types.Message):
    conn = await asyncpg.connect(DATABASE_URL)
    user = await get_user_by_telegram_id(conn, message.from_user.id)
    events = await get_active_events(conn, user["id"])
    await conn.close()
######################
    print("user:", user)
    print("active events count:", len(events))
    for ev in events:
        print(ev["id"], ev["title"])


    if not events:
        await message.answer("У вас нет активных событий.")
        return

    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    for event in events:
        keyboard.add(KeyboardButton(text=f"📌 {event['title']}"))

    keyboard.add(KeyboardButton("⬅️ Назад"))
    await message.answer("Ваши активные события:", reply_markup=keyboard)

# Вывод созданных событий
async def show_created_events(message: types.Message):
    conn = await asyncpg.connect(DATABASE_URL)
    user = await get_user_by_telegram_id(conn, message.from_user.id)
    events = await get_created_events(conn, user["id"])
    await conn.close()

    if not events:
        await message.answer("Вы еще не создавали событий.")
        return

    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    for event in events:
        keyboard.add(KeyboardButton(text=f"🛠 {event['title']}"))

    keyboard.add(KeyboardButton("⬅️ Назад"))
    await message.answer("События, созданные вами:", reply_markup=keyboard)

# Вывод архивных событий
async def show_archive_events(message: types.Message):
    conn = await asyncpg.connect(DATABASE_URL)
    user = await get_user_by_telegram_id(conn, message.from_user.id)
    events = await get_archive_events(conn, user["id"])
    await conn.close()

    if not events:
        await message.answer("Архивных событий не найдено.")
        return

    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    for event in events:
        keyboard.add(KeyboardButton(text=f"📦 {event['title']}"))

    keyboard.add(KeyboardButton("⬅️ Назад"))
    await message.answer("Архивные события:", reply_markup=keyboard)

# Подробности по событию (можно доработать фильтрацией по базе)
async def show_event_details(message: types.Message):
    title = message.text.strip("📌🛠📦 ").strip()
    conn = await asyncpg.connect(DATABASE_URL)
    event = await conn.fetchrow("SELECT * FROM events WHERE title = $1", title)
    await conn.close()

    if not event:
        await message.answer("Событие не найдено.")
        return

    price = "бесплатно" if event["price"] == 0 else f"{event['price']}₽"

    text = (
        f"📌 <b>{event['title']}</b>\n"
        f"📝 {event['description']}\n"
        f"📅 {event['start_date']} — {event['end_date']}\n"
        f"👤 Организатор: {event['organizers']}\n"
        f"💰 Стоимость: {price}"
    )

    await message.answer(text, parse_mode="HTML")

    if event["photos"]:
        await message.answer_media_group([
            types.InputMediaPhoto(media=photo) for photo in event["photos"]
        ])

    if event["videos"]:
        for video in event["videos"]:
            await message.answer_video(video)

    # Регистрация хендлеров

def register_event_handlers(dp: Dispatcher):
    dp.register_message_handler(events_entry, lambda m: m.text == "📅 События")
    dp.register_message_handler(start_event_creation, lambda m: m.text == "📝 Создать событие", state="*")
    dp.register_message_handler(set_title, state=EventCreation.waiting_for_title)
    dp.register_message_handler(set_description, state=EventCreation.waiting_for_description)
    dp.register_message_handler(set_dates, state=EventCreation.waiting_for_dates)
    dp.register_message_handler(set_organizers, state=EventCreation.waiting_for_organizers)
    dp.register_message_handler(set_price, state=EventCreation.waiting_for_price)
    dp.register_message_handler(set_photos, content_types=types.ContentType.PHOTO, state=EventCreation.waiting_for_photos)
    dp.register_message_handler(set_photos, content_types=types.ContentType.PHOTO, state=EventCreation.waiting_for_photos)
    dp.register_message_handler(confirm_photos, lambda m: m.text == "✅ Готово", state=EventCreation.waiting_for_photos)
    dp.register_message_handler(set_videos, content_types=[types.ContentType.VIDEO, types.ContentType.TEXT],                          
    state=EventCreation.waiting_for_videos)
    dp.register_message_handler(confirm_event, lambda m: m.text == "✅ Готово", state=EventCreation.confirmation)
    dp.register_message_handler(cancel_creation, lambda m: m.text == "🗑 Отменить", state=EventCreation.confirmation)
    dp.register_message_handler(back_to_main_from_events, lambda m: m.text == "⬅️ Назад", state="*")
    dp.register_message_handler(show_my_events_menu, lambda m: m.text == "Мои события", state="*")
    dp.register_message_handler(show_active_events, lambda m: m.text == "Активные")
    dp.register_message_handler(show_created_events, lambda m: m.text == "Созданные")
    dp.register_message_handler(show_archive_events, lambda m: m.text == "Архивные")
    dp.register_message_handler(show_event_details, lambda m: any(m.text.startswith(prefix) for prefix in ["📌", "🛠", "📦"]))


