"""Long-term memory in SQLite: risk profile, watchlist and one-line summaries."""
import json
import sqlite3
import threading
from datetime import datetime, timezone

from app import config

_lock = threading.Lock()
RISKS = ("conservative", "balanced", "aggressive")


def _db() -> sqlite3.Connection:
    con = sqlite3.connect(config.DB_PATH)
    con.executescript(
        """CREATE TABLE IF NOT EXISTS profile (user_id TEXT PRIMARY KEY, risk_profile TEXT DEFAULT 'balanced',
             watchlist TEXT DEFAULT '[]', updated_at TEXT);
           CREATE TABLE IF NOT EXISTS analysis_log (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT,
             tickers TEXT, question TEXT, summary TEXT, created_at TEXT);"""
    )
    return con


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get_profile(user_id: str) -> dict:
    with _lock, _db() as con:
        row = con.execute("SELECT risk_profile, watchlist FROM profile WHERE user_id=?", (user_id,)).fetchone()
    return {"risk_profile": row[0], "watchlist": json.loads(row[1])} if row else {"risk_profile": "balanced", "watchlist": []}


def set_risk(user_id: str, risk: str) -> None:
    if risk not in RISKS:
        raise ValueError("invalid risk profile")
    with _lock, _db() as con:
        con.execute(
            "INSERT INTO profile (user_id, risk_profile, updated_at) VALUES (?,?,?) "
            "ON CONFLICT(user_id) DO UPDATE SET risk_profile=excluded.risk_profile, updated_at=excluded.updated_at",
            (user_id, risk, _now()),
        )


def add_watch(user_id: str, tickers: list[str]) -> list[str]:
    cur = get_profile(user_id)["watchlist"]
    new = [t for t in dict.fromkeys(tickers) if t not in cur]
    if new:
        with _lock, _db() as con:
            con.execute(
                "INSERT INTO profile (user_id, watchlist, updated_at) VALUES (?,?,?) "
                "ON CONFLICT(user_id) DO UPDATE SET watchlist=excluded.watchlist, updated_at=excluded.updated_at",
                (user_id, json.dumps((cur + new)[-20:]), _now()),
            )
    return new


def log_analysis(user_id: str, tickers: list[str], question: str, summary: str) -> None:
    with _lock, _db() as con:
        con.execute(
            "INSERT INTO analysis_log (user_id, tickers, question, summary, created_at) VALUES (?,?,?,?,?)",
            (user_id, json.dumps(tickers), question[:500], summary[:300], _now()),
        )


def recent(user_id: str, n: int = config.SUMMARY_LIMIT) -> list[dict]:
    with _lock, _db() as con:
        rows = con.execute(
            "SELECT created_at, tickers, summary FROM analysis_log WHERE user_id=? ORDER BY id DESC LIMIT ?", (user_id, n)
        ).fetchall()
    return [{"created_at": r[0], "tickers": json.loads(r[1]), "summary": r[2]} for r in rows]


def delete_user(user_id: str) -> None:
    with _lock, _db() as con:
        con.execute("DELETE FROM profile WHERE user_id=?", (user_id,))
        con.execute("DELETE FROM analysis_log WHERE user_id=?", (user_id,))
