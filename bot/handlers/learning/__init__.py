from aiogram import Router
from .registration import router as registration_router


learning_router = Router()
learning_router.include_router(registration_router)
