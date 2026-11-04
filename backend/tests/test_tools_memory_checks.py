from types import SimpleNamespace

from app.graph import checks
from app.memory import store
from app.tools import market


def test_technicals_shape(prices):
    t = market.compute_technicals(prices)
    assert 0 < t["rsi14"] < 100
    assert {"macd", "macd_signal", "sma50", "sma200", "price_vs_sma200_pct"} <= t.keys()


def test_tool_never_raises(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("network down")

    monkeypatch.setattr(market.yf, "Ticker", boom)
    for name in market.REGISTRY:
        assert "error" in market.call(name, {"ticker": "ZZZ" + name})  # unique ticker avoids the cache


def test_unknown_tool():
    assert "error" in market.call("nope", {"ticker": "AAPL"})


def test_memory_roundtrip():
    store.set_risk("u1", "conservative")
    assert store.add_watch("u1", ["AAPL", "MSFT", "AAPL"]) == ["AAPL", "MSFT"]
    assert store.add_watch("u1", ["AAPL"]) == []
    store.log_analysis("u1", ["AAPL"], "q", "summary")
    p = store.get_profile("u1")
    assert p == {"risk_profile": "conservative", "watchlist": ["AAPL", "MSFT"]}
    assert store.recent("u1")[0]["summary"] == "summary"
    assert store.get_profile("u2")["watchlist"] == []  # a new user sees nothing
    store.delete_user("u1")
    assert store.recent("u1") == []


def test_critic_rules_catch_made_up_number_and_trade_advice():
    f = [SimpleNamespace(evidence={"rsi14": 61.2, "last_price": 190.5})]
    assert checks.ungrounded_numbers("RSI is 61.2 and price 190.5.", f) == []
    assert checks.ungrounded_numbers("RSI is 61.2 and P/E is 28.4.", f) == [28.4]
    issues = checks.rule_issues("You should buy now. P/E is 28.4.", f)
    assert len(issues) == 3  # ungrounded number, trade instruction, missing Risks section


def test_fundamentals_falls_back_to_statements_when_info_fails(monkeypatch):
    class T:
        @property
        def info(self):
            raise RuntimeError("YFRateLimitError")

    monkeypatch.setattr(market.yf, "Ticker", lambda t: T())
    monkeypatch.setattr(market, "fundamentals_from_statements", lambda t: {"ticker": t, "trailing_pe": 20.0})
    assert market.get_fundamentals("FALLBK") == {"ticker": "FALLBK", "trailing_pe": 20.0}
