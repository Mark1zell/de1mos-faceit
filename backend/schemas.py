from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AuthRequest(BaseModel):
    telegram_id: int
    username: Optional[str] = None
    first_name: str
    last_name: Optional[str] = None
    photo_url: Optional[str] = None


class UserResponse(BaseModel):
    telegram_id: int
    username: Optional[str]
    display_name: str
    photo_url: Optional[str]
    elo: int
    level: int
    matches_played: int
    wins: int
    winrate: float

    class Config:
        from_attributes = True


class FindMatchRequest(BaseModel):
    telegram_id: int
    mode: str = "standoff2"


class MatchHistory(BaseModel):
    id: int
    opponent_name: str
    result: str
    elo_change: int
    played_at: datetime
