"""Demo-page tests: the fix round after the external video review.

1. ARITHMETIC GUARD — at every circle state, the /demo header pot must
   equal the sum of the members table's Paid column, and the header's
   paid-in-full count must equal the number of "Paid in full" rows.
   (The v1 video mixed element screenshots from different states and
   produced a frame whose header and table disagreed; the page itself
   now derives both from one snapshot, and this test keeps it so.)
2. AGENT LOG — after a scripted run, the persisted agent log contains
   the shortfall flag and the purchase-trigger line.
3. RECEIPT — the final receipt card names both signatures (supplier
   delivery + verifier attestation) and carries the honest trust line.
"""

import re

import pytest
from fastapi.testclient import TestClient

from app import main as main_module


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main_module, "DB_PATH", tmp_path / "test.db")
    with TestClient(main_module.app) as c:
        yield c


def _parse_demo(html: str) -> tuple[int, int, int, int]:
    pot_m = re.search(r"Pot: <strong>([\d,]+)</strong> of ([\d,]+)", html)
    cnt_m = re.search(r"(\d+) of (\d+) members paid in full", html)
    assert pot_m and cnt_m, "header numbers not found on /demo"
    rows = re.findall(
        r"<td>[^<]+</td><td>[^<]*</td><td>[^<]*</td><td>([\d,]+)</td>"
        r"<td><span class=\"chip (paid|owes)\"",
        html,
    )
    assert len(rows) == 8, f"expected 8 member rows, found {len(rows)}"
    header_pot = int(pot_m.group(1).replace(",", ""))
    header_full = int(cnt_m.group(1))
    table_sum = sum(int(paid.replace(",", "")) for paid, _ in rows)
    table_full = sum(1 for _, chip in rows if chip == "paid")
    return header_pot, header_full, table_sum, table_full


def _assert_consistent(client, expected_pot, expected_full):
    html = client.get("/demo").text
    header_pot, header_full, table_sum, table_full = _parse_demo(html)
    assert header_pot == table_sum == expected_pot
    assert header_full == table_full == expected_full
    view = client.get("/circle").json()
    assert view["pot"] == expected_pot
    assert view["members_fully_paid"] == expected_full


def test_demo_numbers_agree_at_every_state(client):
    _assert_consistent(client, 32_500, 6)          # seeded
    client.post("/agent/tick")
    _assert_consistent(client, 32_500, 6)          # tick changes nothing
    client.post("/contributions",
                json={"farmer_id": "farmer-emeka-nwosu", "amount": 5000})
    _assert_consistent(client, 37_500, 7)          # Emeka paid
    client.post("/contributions",
                json={"farmer_id": "farmer-halima-usman", "amount": 2500})
    _assert_consistent(client, 40_000, 8)          # funded
    client.post("/agent/tick")
    _assert_consistent(client, 40_000, 8)          # purchased / verified


def test_agent_log_records_shortfalls_contributions_and_trigger(client):
    client.post("/agent/tick")
    client.post("/contributions",
                json={"farmer_id": "farmer-emeka-nwosu", "amount": 5000})
    client.post("/contributions",
                json={"farmer_id": "farmer-halima-usman", "amount": 2500})
    client.post("/agent/tick")

    lines = [entry["message"] for entry in client.get("/agent/log").json()["log"]]
    joined = "\n".join(lines)

    shortfall_lines = [l for l in lines if l.startswith("Shortfall:")]
    assert shortfall_lines, "agent never flagged the shortfalls"
    assert any("Halima Usman owes 2,500" in l and "Emeka Nwosu owes 5,000" in l
               for l in shortfall_lines)
    assert "Contribution received: Emeka Nwosu +5,000 (pot 37,500)" in joined
    assert "Contribution received: Halima Usman +2,500 (pot 40,000)" in joined
    assert "Pot reached 40,000 — executing bulk purchase" in joined
    assert "Delivery signed by supplier" in joined
    assert "Quality attested by Fatima Sule" in joined

    # …and the log is rendered on the demo page itself.
    html = client.get("/demo").text
    assert "Agent treasurer — activity log" in html
    assert "Pot reached 40,000 — executing bulk purchase" in html


def test_receipt_card_shows_both_named_signatures(client):
    client.post("/contributions",
                json={"farmer_id": "farmer-emeka-nwosu", "amount": 5000})
    client.post("/contributions",
                json={"farmer_id": "farmer-halima-usman", "amount": 2500})
    client.post("/agent/tick")

    html = client.get("/demo").text
    assert "Delivered by:" in html
    assert "Kaduna Agro Inputs Ltd" in html
    assert "supplier.farmajo-dev.testnet" in html
    assert "Quality attested by:" in html
    assert "Fatima Sule — QC Verifier" in html
    assert "verifier.farmajo-dev.testnet" in html
    # The honest trust line — no overclaim about what the chain proves.
    assert "cannot prove the fertilizer was good" in html
    assert "nobody can rewrite" not in html.lower()
