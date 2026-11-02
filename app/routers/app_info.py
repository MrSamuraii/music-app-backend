from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter(prefix="/app", tags=["app"])


class AppVersionOut(BaseModel):
    latest_version: str
    min_version: str
    download_url: str
    release_notes: str


@router.get("/version", response_model=AppVersionOut)
def get_app_version():
    """Публичный эндпоинт без авторизации: клиент сравнивает свою версию с актуальной."""
    return AppVersionOut(
        latest_version=settings.APP_LATEST_VERSION,
        min_version=settings.APP_MIN_VERSION,
        download_url=settings.APP_DOWNLOAD_URL,
        release_notes=settings.APP_RELEASE_NOTES,
    )
