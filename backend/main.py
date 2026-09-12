import os
import uuid
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from .database import supabase, STORAGE_BUCKET
from .schemas import (
    AuthRequest, UserResponse, FindMatchRequest,
    MatchResultRequest, UpdateProfileRequest
)

load_dotenv()


async def send_bot_notification(telegram_id: int, message: str):
    try:
        from bot.bot import notify_match_found
        await notify_match_found(telegram_id, message)
    except Exception as e:
        print(f"Failed to notify: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("De1mos Faceit API started with Supabase backend")
    yield


app = FastAPI(title="De1mos Faceit API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def build_user_response(user: dict) -> UserResponse:
    played = user.get("matches_played") or 0
    wins = user.get("wins") or 0
    winrate = (wins / played * 100) if played > 0 else 0.0
    return UserResponse(
        telegram_id=user["telegram_id"],
        username=user.get("username"),
        display_name=user["display_name"],
        photo_url=user.get("photo_url"),
        standoff_id=user.get("standoff_id"),
        custom_avatar=user.get("custom_avatar"),
        elo=user.get("elo") or 1000,
        level=user.get("level") or 1,
        matches_played=played,
        wins=wins,
        winrate=round(winrate, 1),
    )


# ═══════════════════════════════════════════════════
# AUTH
# ═══════════════════════════════════════════════════
@app.post("/api/auth", response_model=UserResponse)
async def auth_user(data: AuthRequest):
    try:
        result = supabase.table("users").select("*").eq("telegram_id", data.telegram_id).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Supabase error: {e}")

    if not result.data:
        new_user = {
            "telegram_id": data.telegram_id,
            "username": data.username,
            "display_name": data.first_name + (f" {data.last_name}" if data.last_name else ""),
            "photo_url": data.photo_url,
            "elo": 1000,
            "level": 1,
            "matches_played": 0,
            "wins": 0,
        }
        result = supabase.table("users").insert(new_user).execute()
        user = result.data[0]
    else:
        user = result.data[0]
        updates = {}
        if data.username and user.get("username") != data.username:
            updates["username"] = data.username
        if data.photo_url and user.get("photo_url") != data.photo_url:
            updates["photo_url"] = data.photo_url
        if updates:
            result = supabase.table("users").update(updates).eq("telegram_id", data.telegram_id).execute()
            user = result.data[0]

    return build_user_response(user)


# ═══════════════════════════════════════════════════
# PROFILE
# ═══════════════════════════════════════════════════
@app.get("/api/profile/{telegram_id}", response_model=UserResponse)
async def get_profile(telegram_id: int):
    result = supabase.table("users").select("*").eq("telegram_id", telegram_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")
    return build_user_response(result.data[0])


@app.post("/api/profile/update", response_model=UserResponse)
async def update_profile(data: UpdateProfileRequest):
    result = supabase.table("users").select("*").eq("telegram_id", data.telegram_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")

    updates = {}
    if data.standoff_id is not None:
        sid = data.standoff_id.strip()
        if len(sid) > 64:
            raise HTTPException(status_code=400, detail="Standoff ID слишком длинный")
        updates["standoff_id"] = sid or None

    if data.custom_avatar is not None:
        updates["custom_avatar"] = data.custom_avatar or None

    if not updates:
        return build_user_response(result.data[0])

    result = supabase.table("users").update(updates).eq("telegram_id", data.telegram_id).execute()
    return build_user_response(result.data[0])


# ═══════════════════════════════════════════════════
# AVATAR UPLOAD
# ═══════════════════════════════════════════════════
@app.post("/api/profile/avatar", response_model=UserResponse)
async def upload_avatar(
    telegram_id: int = Form(...),
    file: UploadFile = File(...)
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Только изображения")

    contents = await file.read()
    if len(contents) > 2_000_000:
        raise HTTPException(status_code=400, detail="Файл слишком большой (макс 2MB)")

    result = supabase.table("users").select("*").eq("telegram_id", telegram_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="User not found")

    ext = file.filename.split(".")[-1] if file.filename and "." in file.filename else "jpg"
    filename = f"{telegram_id}_{uuid.uuid4().hex[:8]}.{ext}"

    try:
        supabase.storage.from_(STORAGE_BUCKET).upload(
            path=filename,
            file=contents,
            file_options={"content-type": file.content_type}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Storage error: {e}")

    public_url = supabase.storage.from_(STORAGE_BUCKET).get_public_url(filename)

    old_avatar = result.data[0].get("custom_avatar")
    if old_avatar and STORAGE_BUCKET in old_avatar:
        try:
            old_filename = old_avatar.split("/")[-1]
            supabase.storage.from_(STORAGE_BUCKET).remove([old_filename])
        except Exception as e:
            print(f"Failed to delete old avatar: {e}")

    result = supabase.table("users").update({"custom_avatar": public_url}).eq("telegram_id", telegram_id).execute()
    return build_user_response(result.data[0])


# ═══════════════════════════════════════════════════
# FIND MATCH
# ═══════════════════════════════════════════════════
@app.post("/api/find_match")
async def find_match(data: FindMatchRequest, background_tasks: BackgroundTasks):
    supabase.table("queue").insert({"telegram_id": data.telegram_id}).execute()
    background_tasks.add_task(simulate_match_found, data.telegram_id)
    return {"status": "searching", "message": "Поиск матча запущен"}


async def simulate_match_found(telegram_id: int):
    await asyncio.sleep(5)
    await send_bot_notification(
        telegram_id,
        "Карта: Sandstone\nРежим: 5v5\nСоперник: Team Alpha (ELO 1050)"
    )


# ═══════════════════════════════════════════════════
# MATCH RESULT
# ═══════════════════════════════════════════════════
@app.post("/api/match_result")
async def match_result(data: MatchResultRequest):
    winner_res = supabase.table("users").select("*").eq("telegram_id", data.winner_id).execute()
    loser_res = supabase.table("users").select("*").eq("telegram_id", data.loser_id).execute()

    if not winner_res.data or not loser_res.data:
        raise HTTPException(status_code=404, detail="User not found")

    winner = winner_res.data[0]
    loser = loser_res.data[0]

    K = 32
    expected_winner = 1 / (1 + 10 ** ((loser["elo"] - winner["elo"]) / 400))
    expected_loser = 1 - expected_winner

    winner_new_elo = int(winner["elo"] + K * (1 - expected_winner))
    loser_new_elo = int(loser["elo"] + K * (0 - expected_loser))

    supabase.table("users").update({
        "elo": winner_new_elo,
        "wins": (winner.get("wins") or 0) + 1,
        "matches_played": (winner.get("matches_played") or 0) + 1,
    }).eq("telegram_id", data.winner_id).execute()

    supabase.table("users").update({
        "elo": loser_new_elo,
        "matches_played": (loser.get("matches_played") or 0) + 1,
    }).eq("telegram_id", data.loser_id).execute()

    supabase.table("matches").insert({
        "player1_id": data.winner_id,
        "player2_id": data.loser_id,
        "winner_id": data.winner_id,
        "elo_change": K,
    }).execute()

    return {"status": "ok", "winner_new_elo": winner_new_elo, "loser_new_elo": loser_new_elo}


# ═══════════════════════════════════════════════════
# LEADERBOARD
# ═══════════════════════════════════════════════════
@app.get("/api/leaderboard")
async def leaderboard():
    result = supabase.table("users").select(
        "display_name, elo, level, custom_avatar, photo_url"
    ).order("elo", desc=True).limit(10).execute()
    return result.data


# ═══════════════════════════════════════════════════
# HEALTH
# ═══════════════════════════════════════════════════
@app.get("/api/health")
async def health():
    return {"status": "ok", "backend": "supabase"}
