"""Fast tests with no network: search, outcome labels, spending limits, and the budget fitter against a real
LMSR cost curve."""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from delphi_kit.client import SHARE, Delphi, DelphiError
from delphi_kit.limits import Guard, LimitExceeded, Limits
from delphi_kit.models import Market
from delphi_kit.search import rank


def _m(addr: str, q: str, outcomes=("Yes", "No"), rules: str = "", hours: float = 24) -> Market:
    return Market(address=addr, deployment="lmsr", mechanism="lmsr", status="open", question=q,
                  outcomes=list(outcomes), probabilities=[0.5] * len(outcomes), prices=[0.5] * len(outcomes),
                  trading_closes_at=datetime.now(timezone.utc) + timedelta(hours=hours),
                  settlement_deadline=None, rules=rules)


# ------------------------------------------------------------------ search

def test_search_prefers_question_then_outcomes_then_rules():
    a = _m("0xa", "Will the Lakers win tonight?")
    b = _m("0xb", "Who wins the game?", outcomes=("Lakers", "Celtics"))
    c = _m("0xc", "Total points over 220?", rules="Use the final score of the Lakers game.")
    d = _m("0xd", "Will it rain in Lagos?")
    assert [m.address for m in rank([c, d, b, a], "lakers")] == ["0xa", "0xb", "0xc"]


def test_search_prefix_and_stop_words():
    a = _m("0xa", "Who wins the 2026 election in Brazil?")
    assert rank([a], "elect") == [a]
    assert rank([a], "el") == []          # prefixes shorter than 3 letters don't count
    assert rank([a], "the will") == [a]   # only stop words: everything comes back unfiltered


def test_search_ties_go_to_soonest_close():
    late = _m("0xl", "Bitcoin above $100k?", hours=48)
    soon = _m("0xs", "Bitcoin above $90k?", hours=2)
    assert [m.address for m in rank([late, soon], "bitcoin")] == ["0xs", "0xl"]


# ------------------------------------------------------------------ outcomes

def test_outcome_index_by_label_or_number():
    m = _m("0xa", "q", outcomes=("Yes", "No"))
    assert m.outcome_index("yes") == 0 and m.outcome_index(" No ") == 1
    assert m.outcome_index(1) == 1 and m.outcome_index("0") == 0
    with pytest.raises(ValueError):
        m.outcome_index("Maybe")
    with pytest.raises(ValueError):
        m.outcome_index(2)


# ------------------------------------------------------------------ limits

def _guard(tmp_path, **kw) -> Guard:
    return Guard(Limits(**kw), ledger=tmp_path / "spend.json")


def test_trading_off_by_default(tmp_path):
    with pytest.raises(LimitExceeded, match="trading is off"):
        _guard(tmp_path).check("0xa", 1)


def test_per_trade_daily_and_allow_list(tmp_path):
    g = _guard(tmp_path, trading_enabled=True, max_trade_usd=5, max_daily_usd=8, allowed_markets=frozenset({"0xa"}))
    with pytest.raises(LimitExceeded, match="per-trade"):
        g.check("0xa", 6)
    with pytest.raises(LimitExceeded, match="ALLOWED"):
        g.check("0xB", 1)
    g.check("0xA", 5)                 # allow-list is case-insensitive
    g.record(5)
    with pytest.raises(LimitExceeded, match="remaining budget of \\$3.00"):
        g.check("0xa", 4)
    g.check("0xa", 3)
    # the ledger survives a restart
    assert _guard(tmp_path, trading_enabled=True).spent_today() == 5


def test_limits_from_env(monkeypatch):
    monkeypatch.setenv("DELPHI_ALLOW_TRADING", "true")
    monkeypatch.setenv("DELPHI_MAX_TRADE_USD", "2.5")
    monkeypatch.setenv("DELPHI_ALLOWED_MARKETS", "0xA, 0xb")
    lim = Limits.from_env()
    assert lim.trading_enabled and lim.max_trade_usd == 2.5 and lim.allowed_markets == {"0xa", "0xb"}


# ------------------------------------------------------------------ budget fitting

def _lmsr_stub(b: float = 1.0, q=(0.0, 0.0), fee: float = 0.02):
    """Something shaped like Delphi with an exact LMSR cost function (USDC has 6 decimals)."""
    def cost(qs):
        return b * math.log(sum(math.exp(x / b) for x in qs))

    def quote_raw(m, idx, shares_raw, side):
        s = shares_raw / SHARE
        after = list(q)
        after[idx] += s
        return math.ceil((cost(after) - cost(q)) * (1 + fee) * 1e6)

    return SimpleNamespace(network=SimpleNamespace(token_decimals=6), _quote_raw=quote_raw)


@pytest.mark.parametrize("usd", [0.05, 0.5, 3, 20])
def test_fit_budget_never_overspends_and_gets_close(usd):
    stub = _lmsr_stub()
    m = _m("0xa", "q")
    raw, spent = Delphi._fit_budget(stub, m, 0, int(usd * 1e6))
    assert spent <= usd * 1e6
    assert spent >= usd * 1e6 * 0.99
    assert stub._quote_raw(m, 0, raw, "buy") == spent


def test_fit_budget_too_small():
    stub = SimpleNamespace(network=SimpleNamespace(token_decimals=6), _quote_raw=lambda *a: 10**9)
    with pytest.raises(DelphiError, match="too small"):
        Delphi._fit_budget(stub, _m("0xa", "q"), 0, 1)
