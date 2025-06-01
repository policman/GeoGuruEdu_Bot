from aiogram import types, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)
import asyncpg

from bot.states.learning_states import MaterialSearch
from bot.config import DATABASE_URL
from deep_translator import GoogleTranslator

router = Router()
ITEMS_PER_PAGE = 3
translator = GoogleTranslator(source="auto", target="ru")


def back_to_search_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⬅️ Назад к поиску")]],
        resize_keyboard=True
    )


@router.callback_query(lambda c: c.data and c.data.startswith("fav:"))
async def save_favorite(callback: CallbackQuery, state: FSMContext):
    if not callback.data:
        return
    index = int(callback.data.split(":")[1])
    data = await state.get_data()
    results = data.get("results", [])

    if index >= len(results):
        await callback.answer("Ошибка: публикация не найдена")
        return

    user_id = callback.from_user.id
    item = results[index]
    title = item.get("title", "Без названия")
    # будем считать, что URL единственный идентификатор
    url = item.get("primary_location", {}).get("landing_page_url") or item.get("id", "")
    authors = ", ".join(
        auth.get("author", {}).get("display_name", "") for auth in item.get("authorships", [])
    )
    year = str(item.get("publication_year", ""))
    annotation = (
        " ".join(item.get("abstract_inverted_index", {}).keys())
        if item.get("abstract_inverted_index")
        else "Нет аннотации"
    )

    conn = await asyncpg.connect(DATABASE_URL)
    # Проверяем, нет ли уже такого URL в избранном у этого пользователя
    existing = await conn.fetchval(
        "SELECT 1 FROM favorite_materials WHERE user_id = $1 AND url = $2",
        user_id, url
    )
    if existing:
        await conn.close()
        await callback.answer("⚠️ Уже в избранном")
        return

    # Если не нашли – вставляем
    await conn.execute(
        """
        INSERT INTO favorite_materials (user_id, title, url, authors, year, annotation)
        VALUES ($1, $2, $3, $4, $5, $6)
        """,
        user_id, title, url, authors, year, annotation
    )
    await conn.close()
    await callback.answer("⭐ Добавлено в избранное")



async def show_favorites_paginated(message: Message, user_id: int, page: int, state: FSMContext):
    await state.update_data(fav_msg_ids=[])

    conn = await asyncpg.connect(DATABASE_URL)
    total: int = await conn.fetchval(
        "SELECT COUNT(*) FROM favorite_materials WHERE user_id = $1", user_id
    )
    max_page = (total - 1) // ITEMS_PER_PAGE if total > 0 else 0
    if page < 0:
        page = 0
    elif page > max_page:
        page = max_page

    rows = await conn.fetch(
        """
        SELECT id, title, url, authors, year, annotation
        FROM favorite_materials
        WHERE user_id = $1
        ORDER BY created_at DESC
        OFFSET $2 LIMIT $3
        """,
        user_id, page * ITEMS_PER_PAGE, ITEMS_PER_PAGE
    )
    await conn.close()

    if not rows:
        m = await message.answer("⭐ У вас нет избранных публикаций.")
        await state.update_data(fav_msg_ids=[m.message_id])
        return

    fav_msg_ids = []
    header = f"Страница {page + 1}/{max_page + 1}"
    m_header = await message.answer(header)
    fav_msg_ids.append(m_header.message_id)

    for row in rows:
        raw_title = row["title"] or "Без названия"
        ru_title = translator.translate(raw_title)
        if ru_title.strip().lower() != raw_title.strip().lower():
            display_title = f"{ru_title} (Переведено)"
        else:
            display_title = raw_title
        print(display_title)
        text = (
            f"<b>{display_title}</b>\n"
            f"👤 {row['authors']}\n"
            f"📅 {row['year']}\n\n"
            f"🔗 <a href='{row['url']}'>Ссылка</a>"
        )
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="❌ Удалить", callback_data=f"del_fav:{row['id']}")]
            ]
        )
        m = await message.answer(text, parse_mode="HTML", reply_markup=keyboard)
        fav_msg_ids.append(m.message_id)

    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="⬅️", callback_data=f"fav_page:{page - 1}")
        )
    if page < max_page:
        nav_buttons.append(
            InlineKeyboardButton(text="➡️", callback_data=f"fav_page:{page + 1}")
        )

    if nav_buttons:
        m_nav = await message.answer(
            "Навигация по избранному:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[nav_buttons])
        )
        fav_msg_ids.append(m_nav.message_id)

    await state.update_data(fav_msg_ids=fav_msg_ids, fav_page=page, fav_max_page=max_page)


@router.message(lambda m: m.text == "⭐ Избранное")
async def show_fav_materials(message: Message, state: FSMContext):
    await state.set_state(MaterialSearch.viewing_favorites)
    await state.update_data(fav_page=0)
    await message.answer(
        "📚 Ваши избранные материалы:", reply_markup=back_to_search_keyboard()
    )
    if not message.from_user:
        await message.answer("Ошибка: пользователь не определён.")
        return

    await show_favorites_paginated(message, message.from_user.id, 0, state)


@router.callback_query(lambda c: c.data and c.data.startswith("fav_page:"))
async def paginate_favorites(callback: CallbackQuery, state: FSMContext):
    if callback.data is None:
        await callback.answer("Ошибка: пустые данные.")
        return
    if callback.message is None or not isinstance(callback.message, Message):
        await callback.answer("Ошибка: сообщение недоступно.")
        return
    msg: Message = callback.message

    data = await state.get_data()
    fav_msg_ids: list = data.get("fav_msg_ids", [])

    bot = msg.bot
    if bot is None:
        await callback.answer("Ошибка: бот недоступен.")
        return
    
    chat_id = msg.chat.id
    for msg_id in fav_msg_ids:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=msg_id)
        except:
            pass

    parts = callback.data.split(":")
    try:
        page = int(parts[1])
    except (IndexError, ValueError):
        await callback.answer("Неверный номер страницы.")
        return

    await state.update_data(fav_page=page)

    # Сначала проверяем from_user, а потом берём его .id
    if not callback.from_user:
        await callback.answer("Ошибка: пользователь не определён.")
        return
    user_id = callback.from_user.id

    await show_favorites_paginated(msg, user_id, page, state)
    await callback.answer()



@router.callback_query(lambda c: c.data and c.data.startswith("del_fav:"))
async def confirm_delete_favorite(callback: CallbackQuery, state: FSMContext):
    if callback.data is None:
        await callback.answer("Ошибка: пустые данные.")
        return
    if callback.message is None or not isinstance(callback.message, Message):
        await callback.answer("Ошибка: сообщение недоступно.")
        return
    msg: Message = callback.message

    await msg.delete()

    parts = callback.data.split(":")
    try:
        fav_id = int(parts[1])
    except (IndexError, ValueError):
        await callback.answer("Некорректный ID.")
        return

    await state.update_data(delete_fav_id=fav_id)

    await msg.answer(
        "Вы уверены, что хотите удалить публикацию?",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="✅ Удалить"), KeyboardButton(text="❌ Отменить")]],
            resize_keyboard=True,
        ),
    )
    await callback.answer()


@router.message(lambda m: m.text == "✅ Удалить")
async def delete_favorite_item(message: Message, state: FSMContext):
    # Проверяем, что message.bot не None
    if message.bot is None:
        await message.answer("Ошибка: бот недоступен.")
        return

    data = await state.get_data()
    fav_id = data.get("delete_fav_id")
    if not fav_id:
        await message.answer("Ошибка: нет ID публикации.")
        return
    if not message.from_user:
        await message.answer("Ошибка: пользователь не определён.")
        return
    user_id = message.from_user.id

    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute(
        "DELETE FROM favorite_materials WHERE id = $1 AND user_id = $2",
        fav_id, user_id
    )
    total: int = await conn.fetchval(
        "SELECT COUNT(*) FROM favorite_materials WHERE user_id = $1",
        user_id
    )
    await conn.close()

    max_page = (total - 1) // ITEMS_PER_PAGE if total > 0 else 0
    page = data.get("fav_page", 0)
    if page > max_page:
        page = max_page

    old_ids: list = data.get("fav_msg_ids", [])
    bot = message.bot  # уже проверили, что не None
    chat_id = message.chat.id
    for msg_id in old_ids:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=msg_id)
        except:
            pass

    await message.answer("✅ Публикация удалена.")
    await show_favorites_paginated(message, user_id, page, state)
    await message.answer("📚 Ваши избранные материалы:", reply_markup=back_to_search_keyboard())



@router.message(lambda m: m.text == "❌ Отменить")
async def cancel_delete_favorite(message: Message, state: FSMContext):
    # Проверяем, что message.bot не None
    if message.bot is None:
        await message.answer("Ошибка: бот недоступен.")
        return

    data = await state.get_data()
    page = data.get("fav_page", 0)
    if not message.from_user:
        await message.answer("Ошибка: пользователь не определён.")
        return

    old_ids: list = data.get("fav_msg_ids", [])
    bot = message.bot
    chat_id = message.chat.id
    for msg_id in old_ids:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=msg_id)
        except:
            pass

    await message.answer("Отменено.")
    await show_favorites_paginated(message, message.from_user.id, page, state)
    await message.answer("📚 Ваши избранные материалы:", reply_markup=back_to_search_keyboard())
