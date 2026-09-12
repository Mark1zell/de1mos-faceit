import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .database import init_db, get_db
from .models import User, Match
from .schemas import AuthRequest, UserResponse, FindMatchRequest

# Импорт функции уведомления из бота (ленивый импорт чтобы избежать цикла)
async def notify_user(telegram_id: int, message: str):
    try:
        from bot import notify_match_found
        await notify_match_found(telegram_id, message)
    except Exception as e:
        print(f"Failed to notify: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="De1mos Faceit API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Раздача статики (Mini App)
app.mount("/webapp", StaticFiles(directory="webapp", html=True), name="webapp")


@app.post("/api/auth", response_model=UserResponse)
async def auth_user(data: AuthRequest, db: AsyncSession = Depends(get_db)):
    """Автоматическая регистрация/авторизация по данным Telegram."""
    result = await db.execute(select(User).where(User.telegram_id == data.telegram_id))
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            telegram_id=data.telegram_id,
            username=data.username,
            display_name=data.first_name + (f" {data.last_name}" if data.last_name else ""),
            photo_url=data.photo_url,
            elo=1000,
            level=1,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    winrate = (user.wins / user.matches_played * 100) if user.matches_played > 0 else 0.0

    return UserResponse(
        telegram_id=user.telegram_id,
        username=user.username,
        display_name=user.display_name,
        photo_url=user.photo_url,
        elo=user.elo,
        level=user.level,
        matches_played=user.matches_played,
        wins=user.wins,
        winrate=round(winrate, 1),
    )


@app.get("/api/profile/{telegram_id}", response_model=UserResponse)
async def get_profile(telegram_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    winrate = (user.wins / user.matches_played * 100) if user.matches_played > 0 else 0.0
    return UserResponse(
        telegram_id=user.telegram_id,
        username=user.username,
        display_name=user.display_name,
        photo_url=user.photo_url,
        elo=user.elo,
        level=user.level,
        matches_played=user.matches_played,
        wins=user.wins,
        winrate=round(winrate, 1),
    )


@app.post("/api/find_match")
async def find_match(data: FindMatchRequest):
    """Запуск поиска матча. В MVP — имитация с уведомлением через 5 секунд."""
    asyncio.create_task(simulate_match_found(data.telegram_id))
    return {"status": "searching", "message": "Поиск матча запущен"}


async def simulate_match_found(telegram_id: int):
    """Имитация найденного матча (задержка + уведомление)."""
    await asyncio.sleep(5)
    await notify_user(
        telegram_id,
        "Карта: Sandstone\nРежим: 5v5\nСоперник: Team Alpha (ELO 1050)"
    )


@app.get("/api/health")
async def health():
    return {"status": "ok"}
