from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from datetime import datetime
from aiogram.types import InputMediaPhoto
from .format_event_dates import format_event_dates
from bot.states.event_states import EventCreation
from bot.keyboards.events import confirm_photos_keyboard, confirm_skip_video_keyboard
from bot.keyboards.events import confirmation_keyboard, event_menu_keyboard
from bot.keyboards.menu import main_menu_keyboard

from bot.database.user_repo import get_user_by_telegram_id
from bot.services.event_service import EventService

import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

async def start_event_creation(message: Message, state: FSMContext):
    await message.answer("Введите название события:")
    await state.set_state(EventCreation.waiting_for_title)

async def set_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("Введите описание события:")
    await state.set_state(EventCreation.waiting_for_description)

async def set_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await message.answer("Введите дату (формат: дд.мм.гггг или дд.мм.гггг-дд.мм.гггг или список дат через запятую):")
    await state.set_state(EventCreation.waiting_for_dates)

async def set_dates(message: Message, state: FSMContext):
    text = (message.text or "").strip()
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
            start_date = end_date = datetime.strptime(text, "%d.%m.%Y").date()
        await state.update_data(start_date=start_date, end_date=end_date)
        await message.answer("Кто организатор события? (ФИО или название организации):")
        await state.set_state(EventCreation.waiting_for_organizers)
    except Exception:
        await message.answer("Некорректный формат даты. Повторите:")

async def set_organizers(message: Message, state: FSMContext):
    await state.update_data(organizers=message.text)
    await message.answer("Введите цену участия в рублях или 'бесплатно':")
    await state.set_state(EventCreation.waiting_for_price)

async def set_price(message: Message, state: FSMContext):
    text = (message.text or "").lower().strip()
    price = 0 if text == "бесплатно" else int(text)
    await state.update_data(price=price)
    await message.answer("Прикрепите фото (1–5):")
    await state.set_state(EventCreation.waiting_for_photos)

async def set_photos(message: Message, state: FSMContext):
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
        await state.set_state(EventCreation.waiting_for_videos)
    else:
        await message.answer(f"Фото получено ({count}/5). Можете отправить ещё или нажмите '✅ Готово':", reply_markup=confirm_photos_keyboard)

async def confirm_photos(message: Message, state: FSMContext):
    data = await state.get_data()
    photos = data.get("photos", [])
    if not photos:
        await message.answer("Сначала загрузите хотя бы одно фото.")
        return

    await message.answer("Теперь отправьте видео (0–2) или нажмите 'Пропустить':", reply_markup=confirm_skip_video_keyboard)
    await state.set_state(EventCreation.waiting_for_videos)

async def set_videos(message: Message, state: FSMContext):
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

    price_display = 'бесплатно' if data['price'] == 0 else f"{data['price']}₽"
    media = []
    if data.get("photos"):
        media.append(InputMediaPhoto(media=data['photos'][0], caption=(
            f"<b>{data['title']}</b>\n"
            f"{data['description']}\n\n"
            f"📅 {format_event_dates(data['start_date'], data['end_date'])}\n\n"
            f"👤 Организатор: {data['organizers']}\n"
            f"💰 Стоимость: {price_display}"
        ), parse_mode="HTML"))

        for photo_id in data['photos'][1:]:
            media.append(InputMediaPhoto(media=photo_id))

    if media:
        await message.answer_media_group(media)

    for video_id in data.get("videos", []):
        await message.answer_video(video_id)

    await message.answer("Проверьте информацию и подтвердите создание:", reply_markup=confirmation_keyboard)
    await state.set_state(EventCreation.confirmation)

async def confirm_event(message: Message, state: FSMContext):
    if message.text != "✅ Готово":
        await message.answer("Пожалуйста, нажмите кнопку ✅ Готово для подтверждения.")
        return

    data = await state.get_data()
    conn = await asyncpg.connect(DATABASE_URL)
    event_service = EventService(conn)
    user_id = message.from_user.id if message.from_user else None
    if user_id is None:
        await message.answer("❌ Ошибка: пользователь не найден.")
        await conn.close()
        return
    user = await get_user_by_telegram_id(conn, user_id)
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

    event_id = await event_service.insert_event(event_data)
    await event_service.add_participant(event_id, user["id"])
    await conn.close()

    await message.answer("✅ Событие успешно сохранено!", reply_markup=event_menu_keyboard)
    await state.clear()

async def cancel_creation(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Создание события отменено.", reply_markup=event_menu_keyboard)
