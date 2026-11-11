"""Payout tests: the opt-in testnet transfer that fires with the purchase.

The NEAR transfer itself is faked throughout: no network, no keys, no
real CLI. What is under test is the wiring: config gating, exactly-once
firing on the purchase tick, persistence into the receipt, failure
safety, and the demo page line.
"""

import pytest
from fastapi.testclient import TestClient

from app import main as main_module
from app import payout as payout_module

FAKE_TX = "FakePayoutTxHash1111111111111111111111111111"


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main_module, "DB_PATH", tmp_path / "test.db")
    monkeypatch.delenv("FARMAJO_PAYOUT_ENABLED", raising=False)
    with TestClient(main_module.app) as c:
        yield c


def _fund(client):
    client.post("/contributions",
                json={"farmer_id": "farmer-emeka-nwosu", "amount": 5000})
    client.post("/contributions",
                json={"farmer_id": "farmer-halima-usman", "amount": 2500})


def _fake_ok(calls):
    def fake_fire(cfg, to_account):
        calls.append((cfg.from_account, to_account, cfg.amount_near))
        return {"status": "sent", "tx_hash": FAKE_TX,
                "explorer_url": "https://explorer.testnet.near.org/"
                                f"transactions/{FAKE_TX}",
                "from": cfg.from_account, "to": to_account,
                "amount_near": cfg.amount_near}
    return fake_fire


def test_config_off_by_default(monkeypatch):
    monkeypatch.delenv("FARMAJO_PAYOUT_ENABLED", raising=False)
    assert payout_module.config_from_env() is None
    monkeypatch.setenv("FARMAJO_PAYOUT_ENABLED", "1")
    cfg = payout_module.config_from_env()
    assert cfg is not None
    assert cfg.from_account == "farmajo-dev.testnet"
    assert cfg.amount_near == "0.3"
    assert cfg.network == "testnet"


def test_no_payout_when_disabled(client):
    _fund(client)
    body = client.post("/agent/tick").json()
    assert body["verified_now"] is True
    assert body["payout"] is None
    receipt = client.get("/receipts").json()["receipts"][-1]
    assert receipt["payout_tx"] is None


def test_payout_fires_exactly_once_at_purchase(client, monkeypatch):
    calls = []
    monkeypatch.setenv("FARMAJO_PAYOUT_ENABLED", "1")
    monkeypatch.setattr(payout_module, "fire_payout", _fake_ok(calls))

    _fund(client)
    body = client.post("/agent/tick").json()
    assert body["payout"]["status"] == "sent"
    assert body["payout"]["tx_hash"] == FAKE_TX
    assert calls == [("farmajo-dev.testnet",
                      "supplier.farmajo-dev.testnet", "0.3")]

    receipt = client.get("/receipts").json()["receipts"][-1]
    assert receipt["payout_tx"] == FAKE_TX
    assert receipt["payout_from"] == "farmajo-dev.testnet"
    assert receipt["payout_to"] == "supplier.farmajo-dev.testnet"
    assert receipt["payout_amount_near"] == "0.3"

    # Later ticks take the already-verified path: no second transfer.
    client.post("/agent/tick")
    assert len(calls) == 1

    # The receipt card on the demo page carries the payout and its hash.
    html = client.get("/demo").text
    assert "Purchase payout" in html
    assert FAKE_TX in html


def test_payout_never_fires_below_target(client, monkeypatch):
    calls = []
    monkeypatch.setenv("FARMAJO_PAYOUT_ENABLED", "1")
    monkeypatch.setattr(payout_module, "fire_payout", _fake_ok(calls))
    body = client.post("/agent/tick").json()   # seeded pot: 32,500 < 40,000
    assert body["funded"] is False
    assert body["payout"] is None
    assert calls == []


def test_payout_failure_does_not_break_the_purchase(client, monkeypatch):
    def fake_fail(cfg, to_account):
        return {"status": "failed", "error": "boom",
                "from": cfg.from_account, "to": to_account,
                "amount_near": cfg.amount_near}
    monkeypatch.setenv("FARMAJO_PAYOUT_ENABLED", "1")
    monkeypatch.setattr(payout_module, "fire_payout", fake_fail)

    _fund(client)
    body = client.post("/agent/tick").json()
    assert body["verified_now"] is True
    assert body["payout"]["status"] == "failed"
    receipt = client.get("/receipts").json()["receipts"][-1]
    assert receipt["payout_tx"] is None
    lines = [e["message"] for e in client.get("/agent/log").json()["log"]]
    assert any("Purchase payout failed" in line for line in lines)
