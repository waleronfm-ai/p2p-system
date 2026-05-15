"""FastAPI приложение P2P System."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import banks, health, info, makers, market, trades


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
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(info.router, prefix="/api")
app.include_router(market.router, prefix="/api")
app.include_router(makers.router, prefix="/api")
app.include_router(banks.router, prefix="/api")
app.include_router(trades.router, prefix="/api")
