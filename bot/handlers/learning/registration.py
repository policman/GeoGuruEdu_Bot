from aiogram import Router
from .menu import router as learning_menu_router
from .create_test import router as create_test_router
from .take_test import router as take_test_router
from .invite_test import router as invite_test_router
from .materials.favorites import router as favorites_router
from .materials.pagination import router as pagination_router
from bot.handlers.learning.materials.registration import router as materials_main_router
from .progress import router as progress_router

router = Router()
router.include_router(learning_menu_router)
router.include_router(materials_main_router)
router.include_router(create_test_router)
router.include_router(take_test_router)
router.include_router(invite_test_router)
router.include_router(favorites_router)
router.include_router(pagination_router)
router.include_router(progress_router)
