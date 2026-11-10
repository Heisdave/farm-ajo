"""Agent-core tests: shortfalls, the funding trigger, and the two-signature
delivery + QC attestation payloads."""

import pytest

from app import agent as agent_core
from app.demo_data import CIRCLE, FARMERS, ROLES

FERT = CIRCLE["fertilizer"]


def _states(paid_override: dict[str, int] | None = None) -> list[agent_core.FarmerState]:
    paid_override = paid_override or {}
    return [
        agent_core.FarmerState(
            farmer_id=f["farmer_id"],
            name=f["name"],
            crop=f["crop"],
            expected=CIRCLE["contribution_amount"],
            paid=paid_override.get(f["farmer_id"], f["paid"]),
        )
        for f in FARMERS
    ]


def _tick(states, already_verified=False):
    return agent_core.agent_tick(
        states,
        target=CIRCLE["target"],
        price_per_bag=FERT["price_per_bag"],
        grade=FERT["grade"],
        supplier_name=ROLES["supplier"]["name"],
        supplier_account=ROLES["supplier"]["account"],
        verifier_name=ROLES["verifier"]["name"],
        verifier_account=ROLES["verifier"]["account"],
        already_verified=already_verified,
    )


def test_seeded_shortfalls_are_exact():
    owing = {s["farmer_id"]: s["shortfall"]
             for s in agent_core.member_shortfalls(_states())}
    # Halima paid half of 5,000; Emeka has paid nothing; everyone else is done.
    assert owing == {"farmer-halima-usman": 2_500, "farmer-emeka-nwosu": 5_000}


def test_seeded_pot_and_total_shortfall():
    result = _tick(_states())
    assert result.pot == 32_500
    assert result.total_shortfall == 7_500
    assert result.remaining_to_target == 7_500


def test_trigger_does_not_fire_below_target():
    result = _tick(_states())
    assert result.funded is False
    assert result.purchase is None
    assert result.delivery is None
    assert result.attestation is None
    assert result.verified is False
    # The agent's job below target is reminders, not buying.
    assert any(a.startswith("reminder:") for a in result.actions)
    assert any("no purchase below target" in a for a in result.actions)


def test_trigger_fires_exactly_at_target():
    full = {f["farmer_id"]: CIRCLE["contribution_amount"] for f in FARMERS}
    result = _tick(_states(full))
    assert result.pot == CIRCLE["target"] == 40_000
    assert result.funded is True
    assert result.shortfalls == []
    assert result.purchase is not None
    assert result.purchase.bags == 20           # 40,000 / 2,000 per bag
    assert result.purchase.total_cost == 40_000
    assert result.purchase.leftover == 0


def test_trigger_fires_above_target_and_keeps_leftover():
    # Pure-logic check of the >= rule (the API caps shares, so an API pot
    # cannot exceed the target; the agent must still behave if one does).
    full = {f["farmer_id"]: CIRCLE["contribution_amount"] for f in FARMERS}
    states = _states(full)
    states[0].paid += 1_000  # pot = 41,000
    result = _tick(states)
    assert result.funded is True
    assert result.purchase is not None
    assert result.purchase.total_cost == 40_000     # sized on the target
    assert result.purchase.leftover == 1_000


def test_two_signature_payloads_when_funded():
    full = {f["farmer_id"]: CIRCLE["contribution_amount"] for f in FARMERS}
    result = _tick(_states(full))

    delivery = result.delivery
    assert delivery is not None
    assert delivery.bags == 20
    assert delivery.grade == "NPK 15-15-15"
    assert delivery.total_cost == 40_000
    # The payload handed to the contract must have exactly the fields
    # record_delivery(supplier_name, bags, grade, total_cost, notes) takes.
    assert set(delivery.contract_args()) == {
        "supplier_name", "bags", "grade", "total_cost", "notes",
    }
    assert delivery.supplier_account == ROLES["supplier"]["account"]

    attestation = result.attestation
    assert attestation is not None
    assert attestation.qc_passed is True
    assert len(attestation.checks) == 4
    # attest_quality(verifier_name, qc_passed, checks, notes) — exactly.
    assert set(attestation.contract_args()) == {
        "verifier_name", "qc_passed", "checks", "notes",
    }
    assert attestation.verifier_account == ROLES["verifier"]["account"]
    assert attestation.verifier_name == ROLES["verifier"]["name"]

    # The whole point of the model: the two signatures belong to two
    # different accounts — the supplier cannot mark its own homework.
    assert delivery.supplier_account != attestation.verifier_account
    assert result.verified is True


def test_no_new_records_when_already_verified():
    full = {f["farmer_id"]: CIRCLE["contribution_amount"] for f in FARMERS}
    result = _tick(_states(full), already_verified=True)
    assert result.funded is True
    assert result.purchase is None
    assert result.delivery is None
    assert result.attestation is None


def test_contribution_validation():
    farmer = agent_core.FarmerState("f1", "Test Farmer", "maize",
                                    expected=5_000, paid=2_500)
    agent_core.validate_contribution(farmer, 2_500, circle_closed=False)
    with pytest.raises(ValueError):
        agent_core.validate_contribution(farmer, 0, circle_closed=False)
    with pytest.raises(ValueError):
        agent_core.validate_contribution(farmer, -5, circle_closed=False)
    with pytest.raises(ValueError):
        agent_core.validate_contribution(farmer, 2_501, circle_closed=False)
    with pytest.raises(ValueError):
        agent_core.validate_contribution(farmer, 100, circle_closed=True)
