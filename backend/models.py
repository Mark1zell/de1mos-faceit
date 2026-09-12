from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base


class User(Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(64), nullable=True)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    photo_url: Mapped[str] = mapped_column(String(512), nullable=True)
    standoff_id: Mapped[str] = mapped_column(String(64), nullable=True)          # ← новое
    custom_avatar: Mapped[str] = mapped_column(Text, nullable=True)              # ← новое (base64)
    elo: Mapped[int] = mapped_column(Integer, default=1000)
    level: Mapped[int] = mapped_column(Integer, default=1)
    matches_played: Mapped[int] = mapped_column(Integer, default=0)
    wins: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player1_id: Mapped[int] = mapped_column(ForeignKey("users.telegram_id"))
    player2_id: Mapped[int] = mapped_column(ForeignKey("users.telegram_id"))
    winner_id: Mapped[int] = mapped_column(Integer, nullable=True)
    elo_change: Mapped[int] = mapped_column(Integer, default=0)
    played_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Queue(Base):
    __tablename__ = "queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(Integer, index=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
