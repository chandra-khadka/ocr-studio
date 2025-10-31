from fastapi import APIRouter

from backend.app.api.v1.endpoints import health, models, ocr, correction, chat, ocr_premium

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(models.router, prefix="/models", tags=["models"])
api_router.include_router(ocr.router, prefix="/ocr", tags=["ocr"])
api_router.include_router(ocr_premium.router, prefix="/ocr_premium", tags=["ocr premium"])
api_router.include_router(correction.router, prefix="/correct", tags=["correction"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
