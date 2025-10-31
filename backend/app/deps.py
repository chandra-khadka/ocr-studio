from fastapi import Header, HTTPException, status

from backend.core.config import settings


async def verify_api_key(x_api_key: str | None = Header(default=None)):
    if settings.API_KEY and x_api_key != settings.API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
