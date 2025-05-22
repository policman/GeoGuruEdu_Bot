from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram.fsm.context import FSMContext
import asyncpg
import os
from dotenv import load_dotenv

from bot.services.event_service import EventService

router = Router()

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")


@router.callback_query(F.data.startswith("delete_event:"))
async def handle_delete_event(callback: CallbackQuery, state: FSMContext):
    if not callback.data:
        return
    _, event_id, source, page = callback.data.split(":")
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            "Вы уверены, что хотите удалить это событие?",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="✅ Да",
                            callback_data=f"confirm_delete_event:{event_id}:{source}:{page}"
                        ),
                        InlineKeyboardButton(
                            text="❌ Нет",
                            callback_data=f"event:{event_id}:{source}:{page}"
                        )
                    ]
                ]
            )
        )
    else:
        await callback.answer("Не удалось отредактировать сообщение.")


@router.callback_query(F.data.startswith("confirm_delete_event:"))
async def handle_confirm_delete_event(callback: CallbackQuery, state: FSMContext):
    if not callback.data:
        return
    _, event_id, source, page = callback.data.split(":")
    conn = await asyncpg.connect(DATABASE_URL)
    event_service = EventService(conn)
    await event_service.delete_event_by_id(int(event_id))
    await conn.close()
    if callback.message:
        if isinstance(callback.message, Message):
            await callback.message.edit_text("Событие успешно удалено.")
    else:
        await callback.answer("Событие успешно удалено.")


@router.callback_query(F.data.startswith("edit_event:"))
async def handle_edit_event(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Редактирование событий появится скоро!", show_alert=True)


@router.callback_query(F.data.startswith("invite_event:"))
async def handle_invite_event(callback: CallbackQuery, state: FSMContext):
    await callback.answer("Возможность рассылки приглашений появится скоро!", show_alert=True)
