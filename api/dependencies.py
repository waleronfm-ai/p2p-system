from fastapi import Header, HTTPException

from config.settings import settings


async def require_api_key(x_api_key: str | None = Header(default=None)):
    if not x_api_key or x_api_key != settings.api_key:
        raise HTTPException(status_code=403, detail="Invalid or missing API key")
