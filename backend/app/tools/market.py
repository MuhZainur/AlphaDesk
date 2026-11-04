"""Four market tools over yfinance. They return plain dicts and never raise (errors become {"error": ...})."""
from datetime import datetime, timezone
from functools import wraps

import pandas as pd
import requests
import yfinance as yf

from app.tools.cache import cached


def safe(fn):
    @wraps(fn)
    def wrapper(ticker: str, *a):
        try:
            return fn(ticker.upper().strip(), *a)
        except Exception as e:  # noqa: BLE001
            return {"error": f"{type(e).__name__}: {str(e)[:120]}"}

    return wrapper


def _history(ticker: str, period: str) -> pd.DataFrame:
    h = yf.Ticker(ticker).history(period=period)
    if h.empty:
        raise ValueError(f"no price data for {ticker}")
    return h


def _pct(a: float, b: float) -> float:
    return round((a / b - 1) * 100, 2)


@safe
@cached
def get_price_snapshot(ticker: str) -> dict:
    c = _history(ticker, "1y")["Close"]
    last = float(c.iloc[-1])
    return {
        "ticker": ticker,
        "last_price": round(last, 2),
        "change_1m_pct": _pct(last, float(c.iloc[-22])) if len(c) > 22 else None,
        "change_6m_pct": _pct(last, float(c.iloc[-127])) if len(c) > 127 else None,
        "low_52w": round(float(c.min()), 2),
        "high_52w": round(float(c.max()), 2),
    }


def compute_technicals(close: pd.Series) -> dict:
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    rsi = 100 - 100 / (1 + gain / loss)
    macd = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    signal = macd.ewm(span=9, adjust=False).mean()
    last = float(close.iloc[-1])
    out = {
        "last_price": round(last, 2),
        "rsi14": round(float(rsi.iloc[-1]), 1),
        "macd": round(float(macd.iloc[-1]), 2),
        "macd_signal": round(float(signal.iloc[-1]), 2),
    }
    for n in (50, 200):
        if len(close) >= n:
            sma = float(close.rolling(n).mean().iloc[-1])
            out[f"sma{n}"] = round(sma, 2)
            out[f"price_vs_sma{n}_pct"] = _pct(last, sma)
    return out


@safe
@cached
def get_technicals(ticker: str) -> dict:
    return {"ticker": ticker, **compute_technicals(_history(ticker, "2y")["Close"])}


@safe
@cached
def get_fundamentals(ticker: str) -> dict:
    info = yf.Ticker(ticker).info
    if not info or info.get("trailingPE") is None and info.get("forwardPE") is None and not info.get("longName"):
        raise ValueError(f"no fundamentals for {ticker}")

    def pct(v):
        return round(v * 100, 1) if isinstance(v, (int, float)) else None

    def num(v):
        return round(v, 2) if isinstance(v, (int, float)) else None

    return {
        "ticker": ticker,
        "name": info.get("longName"),
        "trailing_pe": num(info.get("trailingPE")),
        "forward_pe": num(info.get("forwardPE")),
        "profit_margin_pct": pct(info.get("profitMargins")),
        "revenue_growth_pct": pct(info.get("revenueGrowth")),
        "debt_to_equity": num(info.get("debtToEquity")),
    }


@safe
@cached
def get_news(ticker: str, n: int = 5) -> dict:
    items = []
    try:  # yfinance's own news call is flaky, so the Yahoo search endpoint is the fallback
        for it in yf.Ticker(ticker).get_news(count=n):
            c = it.get("content", it)
            items.append({"title": c.get("title"), "publisher": (c.get("provider") or {}).get("displayName"), "date": c.get("pubDate")})
    except Exception:  # noqa: BLE001
        r = requests.get(
            "https://query1.finance.yahoo.com/v1/finance/search",
            params={"q": ticker, "newsCount": n},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=20,
        )
        r.raise_for_status()
        for it in r.json().get("news", [])[:n]:
            ts = it.get("providerPublishTime")
            date = datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d") if ts else None
            items.append({"title": it.get("title"), "publisher": it.get("publisher"), "date": date})
    items = [i for i in items if i["title"]][:n]
    if not items:
        raise ValueError(f"no news for {ticker}")
    return {"ticker": ticker, "headlines": items}


def _spec(name: str, desc: str) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": desc,
            "parameters": {"type": "object", "properties": {"ticker": {"type": "string"}}, "required": ["ticker"]},
        },
    }


REGISTRY = {
    "get_price_snapshot": (get_price_snapshot, _spec("get_price_snapshot", "Last price, 1-month and 6-month change, 52-week range.")),
    "get_technicals": (get_technicals, _spec("get_technicals", "RSI(14), MACD, SMA50, SMA200 and price versus each.")),
    "get_fundamentals": (get_fundamentals, _spec("get_fundamentals", "P/E, margins, revenue growth, debt to equity.")),
    "get_news": (get_news, _spec("get_news", "Up to five recent headlines.")),
}


def specs(names: list[str]) -> list[dict]:
    return [REGISTRY[n][1] for n in names]


def call(name: str, args: dict) -> dict:
    if name not in REGISTRY:
        return {"error": f"unknown tool {name}"}
    return REGISTRY[name][0](str(args.get("ticker", "")))
