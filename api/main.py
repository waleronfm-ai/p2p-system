"""FastAPI приложение P2P System."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import ai, banks, health, info, makers, market, position, sessions, trades
from config.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="P2P System API",
    description="Мониторинг P2P курсов: Binance + Bybit / USDT + USDC / UAH",
    version="0.3.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(info.router, prefix="/api")
app.include_router(market.router, prefix="/api")
app.include_router(makers.router, prefix="/api")
app.include_router(banks.router, prefix="/api")
app.include_router(trades.router, prefix="/api")
app.include_router(sessions.router, prefix="/api")
app.include_router(position.router, prefix="/api")
app.include_router(ai.router, prefix="/api")
