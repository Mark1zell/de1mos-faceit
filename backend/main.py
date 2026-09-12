import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from .database import init_db, get_db
from .models import User, Match, Queue
from .schemas import AuthRequest, UserResponse, FindMatchRequest, MatchResultRequest

# Bot notification function (will be imported)
async def send_bot_notification(telegram_id: int, message: str):
    try:
        from bot.bot import notify_match_found
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


@app.post("/api/auth", response_model=UserResponse)
async def auth_user(data: AuthRequest, db: AsyncSession = Depends(get_db)):
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
async def find_match(data: FindMatchRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    # Add to queue
    queue_entry = Queue(telegram_id=data.telegram_id)
    db.add(queue_entry)
    await db.commit()

    background_tasks.add_task(simulate_match_found, data.telegram_id)
    return {"status": "searching", "message": "Поиск матча запущен"}


async def simulate_match_found(telegram_id: int):
    await asyncio.sleep(5)
    await send_bot_notification(
        telegram_id,
        "Карта: Sandstone\nРежим: 5v5\nСоперник: Team Alpha (ELO 1050)"
    )


@app.post("/api/match_result")
async def match_result(data: MatchResultRequest, db: AsyncSession = Depends(get_db)):
    # Get both players
    winner_result = await db.execute(select(User).where(User.telegram_id == data.winner_id))
    winner = winner_result.scalar_one_or_none()

    loser_result = await db.execute(select(User).where(User.telegram_id == data.loser_id))
    loser = loser_result.scalar_one_or_none()

    if not winner or not loser:
        raise HTTPException(status_code=404, detail="User not found")

    # ELO calculation (simple K-factor system)
    K = 32
    expected_winner = 1 / (1 + 10 ** ((loser.elo - winner.elo) / 400))
    expected_loser = 1 - expected_winner

    winner_new_elo = int(winner.elo + K * (1 - expected_winner))
    loser_new_elo = int(loser.elo + K * (0 - expected_loser))

    winner.elo = winner_new_elo
    winner.wins += 1
    winner.matches_played += 1

    loser.elo = loser_new_elo
    loser.matches_played += 1

    # Save match
    match = Match(
        player1_id=data.winner_id,
        player2_id=data.loser_id,
        winner_id=data.winner_id,
        elo_change=winner_new_elo - winner.elo
    )
    db.add(match)
    await db.commit()

    return {"status": "ok", "winner_new_elo": winner_new_elo, "loser_new_elo": loser_new_elo}


@app.get("/api/leaderboard")
async def leaderboard(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).order_by(User.elo.desc()).limit(10))
    users = result.scalars().all()
    return [
        {"display_name": u.display_name, "elo": u.elo, "level": u.level}
        for u in users
    ]


@app.get("/api/health")
async def health():
    return {"status": "ok"}
