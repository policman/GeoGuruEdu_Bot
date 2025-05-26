from .registration import router
from .invitations import router as invitations_router

router.include_router(invitations_router)

__all__ = ["router"]
# from .visit_event import router as visit_event_router
# # ...
# router.include_router(visit_event_router)
