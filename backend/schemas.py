from pydantic import BaseModel
from typing import Optional


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
    standoff_id: Optional[str]
    custom_avatar: Optional[str]
    elo: int
    level: int
    matches_played: int
    wins: int
    winrate: float


class UpdateProfileRequest(BaseModel):
    telegram_id: int
    standoff_id: Optional[str] = None
    custom_avatar: Optional[str] = None


class FindMatchRequest(BaseModel):
    telegram_id: int
    mode: str = "standoff2"


class MatchResultRequest(BaseModel):
    winner_id: int
    loser_id: int
