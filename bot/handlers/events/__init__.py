from .registration import router
from .invitations import router as invitations_router

router.include_router(invitations_router)
__all__ = ["router"]
