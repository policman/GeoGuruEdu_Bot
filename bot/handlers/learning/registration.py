from aiogram import Router
from .menu import learning_entry
from .materials import materials_router

router = Router()

@router.message(lambda m: m.text == "📚 Обучение")
async def entry(message, state):
    await learning_entry(message)

router.include_router(materials_router)
