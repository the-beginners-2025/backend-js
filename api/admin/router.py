from fastapi import APIRouter, Depends

from api.admin.status.router import router as status_router
from middlewares.auth import admin_only_middleware

router = APIRouter(prefix="/admin", dependencies=[Depends(admin_only_middleware)])

router.include_router(status_router)
