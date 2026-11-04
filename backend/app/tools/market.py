"""Four market tools over yfinance. They return plain dicts and never raise (errors become {"error": ...})."""
from datetime import datetime, timezone
from functools import wraps

import pandas as pd
import requests
import yfinance as yf

from app import config
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


_cik: dict[str, int] = {}


def _sec_get(url: str) -> dict:
    r = requests.get(url, headers={"User-Agent": config.SEC_USER_AGENT}, timeout=40)
    r.raise_for_status()
    return r.json()


def _window(r: dict) -> int:
    return (datetime.fromisoformat(r["end"]) - datetime.fromisoformat(r["start"])).days


def ttm_and_growth(rows: list[dict]) -> tuple[float | None, float | None]:
    """Trailing-twelve-month value and a growth rate from SEC duration facts (annual, quarterly, year-to-date)."""
    d = {(r["start"], r["end"]): r["val"] for r in rows if r.get("start")}
    spans = [(datetime.fromisoformat(s), datetime.fromisoformat(e), v) for (s, e), v in d.items()]

    def near(start, end, val_spans, tol=10):
        return next((v for s2, e2, v in val_spans if abs((s2 - start).days) <= tol and abs((e2 - end).days) <= tol), None)

    annual = [(s, e, v) for s, e, v in spans if 350 <= (e - s).days <= 380]
    if not annual:
        return None, None
    s_a, e_a, v_a = max(annual, key=lambda x: x[1])
    ytd = [(s, e, v) for s, e, v in spans if 60 < (e - s).days < 350 and e > e_a]
    if ytd:
        s_y, e_y, v_y = max(ytd, key=lambda x: (x[1], (x[1] - x[0]).days))
        prior = near(s_y.replace(year=s_y.year - 1), e_y.replace(year=e_y.year - 1), spans)
        if prior:
            return v_a + v_y - prior, (v_y / prior - 1) * 100 if prior > 0 else None
    prev = near(s_a.replace(year=s_a.year - 1), e_a.replace(year=e_a.year - 1), annual)
    return v_a, (v_a / prev - 1) * 100 if prev and prev > 0 else None


def _latest(facts: dict, tags: list[str], unit: str = "USD") -> list[dict]:
    """Rows for the first tag that has the most recent data (companies switch XBRL tags over time)."""
    best: list[dict] = []
    for t in tags:
        rows = facts.get(t, {}).get("units", {}).get(unit, [])
        if rows and (not best or max(r["end"] for r in rows) > max(r["end"] for r in best)):
            best = rows
    return best


def fundamentals_from_edgar(ticker: str) -> dict:
    """Fallback when Yahoo rate-limits cloud IPs: compute the figures from SEC EDGAR filings (no API key)."""
    if not config.SEC_USER_AGENT:
        raise ValueError("SEC_USER_AGENT is not set")
    if not _cik:
        _cik.update({v["ticker"]: v["cik_str"] for v in _sec_get("https://www.sec.gov/files/company_tickers.json").values()})
    cik = _cik.get(ticker.replace(".", "-"))
    if cik is None:
        raise ValueError(f"{ticker} is not an SEC filer")
    facts = _sec_get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json")["facts"].get("us-gaap", {})
    rev, growth = ttm_and_growth(_latest(facts, ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet", "RevenueFromContractWithCustomerIncludingAssessedTax"]))
    ni, _ = ttm_and_growth(_latest(facts, ["NetIncomeLoss", "ProfitLoss"]))
    eps, _ = ttm_and_growth(_latest(facts, ["EarningsPerShareDiluted"], "USD/shares"))
    price = float(_history(ticker, "5d")["Close"].iloc[-1])

    def instant(tags):
        rows = [r for r in _latest(facts, tags) if "start" not in r]
        return max(rows, key=lambda r: (r["end"], r["filed"]))["val"] if rows else None

    debt, equity = instant(["LongTermDebt", "LongTermDebtNoncurrent"]), instant(["StockholdersEquity"])
    out = {
        "ticker": ticker,
        "source": "computed from SEC filings: P/E and margin use the trailing four quarters, revenue growth is the latest year-to-date vs the same period last year, debt is long-term debt, no forward P/E",
        "forward_pe": None,
        "trailing_pe": round(price / eps, 2) if eps and eps > 0 else None,
        "profit_margin_pct": round(ni / rev * 100, 1) if ni is not None and rev else None,
        "revenue_growth_pct": round(growth, 1) if growth is not None else None,
        "debt_to_equity": round(debt / equity * 100, 2) if debt and equity and equity > 0 else None,
    }
    if all(out[k] is None for k in ("trailing_pe", "profit_margin_pct", "revenue_growth_pct", "debt_to_equity")):
        raise ValueError(f"no usable SEC data for {ticker}")
    return out


@safe
@cached
def get_fundamentals(ticker: str) -> dict:
    try:
        info = yf.Ticker(ticker).info
        if not info or (info.get("trailingPE") is None and info.get("forwardPE") is None and not info.get("longName")):
            raise ValueError(f"no fundamentals for {ticker}")
    except Exception:  # noqa: BLE001 - rate limit or empty answer: use SEC filings
        return fundamentals_from_edgar(ticker)

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
