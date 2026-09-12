# De1mos Faceit

Telegram Mini App для игры Standoff 2 с системой ELO и поиском матчей.

## 🏗️ Архитектура

- **Telegram Bot** (aiogram 3) — точка входа и уведомления
- **Backend API** (FastAPI + SQLite) — ELO, статистика, поиск матчей
- **Mini App** (HTML/JS) — интерфейс внутри Telegram

## 🚀 Быстрый старт

### 1. Клонирование и зависимости

```bash
git clone https://github.com/your-username/de1mos-faceit.git
cd de1mos-faceit
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
