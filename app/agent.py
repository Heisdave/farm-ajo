"""Farm Ajo agent core — pure Python, no web dependencies, deterministic.

The agent is the circle's treasurer. It does three jobs:

  1. Book-keeping: track what each member has paid against their fixed
     contribution share, and work out who still owes what (shortfalls).
  2. Trigger: when — and only when — the pot reaches the circle's target,
     it fires the bulk fertilizer purchase.
  3. Two-signature receipt: when the purchase fires, it produces BOTH
     payloads the NEAR testnet Ajo circle contract expects, in exactly
     the shapes of its two role-gated methods:
       * `record_delivery` — signed by the designated *supplier*
         account: what was delivered (bags, grade, total cost).
       * `attest_quality` — signed by the designated *QC verifier*
         account, a different account: the named quality checks and
         pass/fail.
     The circle is final ("verified") on-chain only when both
     signatures exist and QC passed — the supplier cannot mark its own
     homework, and the verifier cannot invent a delivery.

Amounts are integer demo units (see demo_data.py). Nothing here touches a
network, a wallet, or real money.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FarmerState:
    farmer_id: str
    name: str
    crop: str
    expected: int          # member's fixed contribution share
    paid: int = 0          # total recorded so far

    @property
    def shortfall(self) -> int:
        return max(0, self.expected - self.paid)

    def to_dict(self) -> dict:
        return {
            "farmer_id": self.farmer_id,
            "name": self.name,
            "crop": self.crop,
            "expected": self.expected,
            "paid": self.paid,
            "shortfall": self.shortfall,
            "fully_paid": self.shortfall == 0,
        }


@dataclass
class PurchaseOrder:
    supplier: str
    grade: str
    bags: int
    price_per_bag: int
    total_cost: int
    leftover: int          # pot minus spend (stays in the circle)

    def to_dict(self) -> dict:
        return {
            "supplier": self.supplier,
            "grade": self.grade,
            "bags": self.bags,
            "price_per_bag": self.price_per_bag,
            "total_cost": self.total_cost,
            "leftover": self.leftover,
        }


@dataclass
class DeliveryRecord:
    """Signature 1 of 2 — the supplier's delivery record.

    Field names in `contract_args` match the contract's
    `record_delivery` method exactly. The signing account is NOT an
    argument: on-chain it is the caller, and the contract rejects any
    caller other than the designated supplier account.
    """

    supplier_name: str
    supplier_account: str    # the only account allowed to sign this
    bags: int
    grade: str
    total_cost: int
    notes: str = ""

    def contract_args(self) -> dict:
        return {
            "supplier_name": self.supplier_name,
            "bags": self.bags,
            "grade": self.grade,
            "total_cost": self.total_cost,
            "notes": self.notes,
        }

    def to_dict(self) -> dict:
        body = self.contract_args()
        body["signed_by"] = self.supplier_account
        return body


@dataclass
class QualityAttestation:
    """Signature 2 of 2 — the named QC verifier's quality attestation.

    Field names in `contract_args` match the contract's
    `attest_quality` method exactly. On-chain the caller must be the
    designated verifier account — a different account from the
    supplier's, enforced by the contract, not by politeness.
    """

    verifier_name: str
    verifier_account: str    # the only account allowed to sign this
    qc_passed: bool
    checks: list[str] = field(default_factory=list)
    notes: str = ""

    def contract_args(self) -> dict:
        return {
            "verifier_name": self.verifier_name,
            "qc_passed": self.qc_passed,
            "checks": list(self.checks),
            "notes": self.notes,
        }

    def to_dict(self) -> dict:
        body = self.contract_args()
        body["signed_by"] = self.verifier_account
        return body


@dataclass
class TickResult:
    pot: int
    target: int
    remaining_to_target: int
    funded: bool
    shortfalls: list[dict]           # only members who still owe
    total_shortfall: int
    actions: list[str]               # what the agent did / will do next
    purchase: PurchaseOrder | None = None
    delivery: DeliveryRecord | None = None
    attestation: QualityAttestation | None = None

    @property
    def verified(self) -> bool:
        """Final only when BOTH signatures exist and QC passed."""
        return (
            self.delivery is not None
            and self.attestation is not None
            and self.attestation.qc_passed
        )

    def to_dict(self) -> dict:
        return {
            "pot": self.pot,
            "target": self.target,
            "remaining_to_target": self.remaining_to_target,
            "funded": self.funded,
            "shortfalls": self.shortfalls,
            "total_shortfall": self.total_shortfall,
            "actions": self.actions,
            "purchase": self.purchase.to_dict() if self.purchase else None,
            "delivery": self.delivery.to_dict() if self.delivery else None,
            "attestation": self.attestation.to_dict() if self.attestation else None,
            "verified": self.verified,
        }


# The quality checks a blending-plant QC hand actually runs at delivery.
# The founder did production / QC at a fertilizer blending plant, so the
# attestation records checks, not just "delivered".
QC_CHECKS = [
    "bag count matches the purchase order",
    "sample bags weigh within +/-2% of the nominal 50 kg",
    "granules uniform in size and colour; no excessive caking",
    "blend grade on batch labels matches the ordered grade",
]


def member_shortfalls(farmers: list[FarmerState]) -> list[dict]:
    """Per-member shortfall list (only members who still owe), in order."""
    return [f.to_dict() for f in farmers if f.shortfall > 0]


def plan_purchase(pot: int, target: int, price_per_bag: int) -> PurchaseOrder | None:
    """Bulk order for a *funded* pot. Returns None if not funded.

    The order is sized on the target (the amount the circle set out to
    raise), not on any accidental excess in the pot; any leftover stays
    in the circle for the next round.
    """
    if pot < target:
        return None
    bags = target // price_per_bag
    total_cost = bags * price_per_bag
    return PurchaseOrder(
        supplier="",  # filled by caller from circle config
        grade="",     # filled by caller from circle config
        bags=bags,
        price_per_bag=price_per_bag,
        total_cost=total_cost,
        leftover=pot - total_cost,
    )


def build_delivery(order: PurchaseOrder, supplier_name: str,
                   supplier_account: str) -> DeliveryRecord:
    """Signature 1: the supplier's delivery record for the fired order."""
    notes = (
        f"Demo delivery record: {order.bags} bags of {order.grade} "
        f"delivered by {supplier_name} against the circle's bulk order, "
        f"total {order.total_cost} demo units. Simulated delivery on "
        "testnet/demo data - no real goods moved."
    )
    return DeliveryRecord(
        supplier_name=supplier_name,
        supplier_account=supplier_account,
        bags=order.bags,
        grade=order.grade,
        total_cost=order.total_cost,
        notes=notes,
    )


def build_attestation(order: PurchaseOrder, verifier_name: str,
                      verifier_account: str) -> QualityAttestation:
    """Signature 2: the named verifier's QC attestation for the delivery.

    In the demo the delivery is simulated and every check passes; the
    attestation is honest about the simulation in its notes. A failed
    check would set qc_passed=False and the circle would stay
    delivered-but-disputed instead of closing as verified.
    """
    notes = (
        f"Attested at delivery by {verifier_name}. Sample bags within "
        "+/-2% of 50 kg, granules uniform, no excessive caking, batch "
        "labels match the ordered grade. Simulated delivery on "
        "testnet/demo data - no real goods moved."
    )
    return QualityAttestation(
        verifier_name=verifier_name,
        verifier_account=verifier_account,
        qc_passed=True,
        checks=list(QC_CHECKS),
        notes=notes,
    )


def agent_tick(
    farmers: list[FarmerState],
    target: int,
    price_per_bag: int,
    grade: str,
    supplier_name: str,
    supplier_account: str,
    verifier_name: str,
    verifier_account: str,
    already_verified: bool = False,
) -> TickResult:
    """Run one agent tick over the current circle state.

    Rules:
      * funded  <=>  pot >= target. Below target the agent NEVER creates
        a purchase — it only reports shortfalls and sends reminders.
      * At/above target it generates the bulk purchase order plus BOTH
        signature payloads (supplier delivery record, verifier QC
        attestation), unless the circle is already verified.
    """
    pot = sum(f.paid for f in farmers)
    owing = member_shortfalls(farmers)
    total_shortfall = sum(s["shortfall"] for s in owing)
    funded = pot >= target
    actions: list[str] = []
    purchase: PurchaseOrder | None = None
    delivery: DeliveryRecord | None = None
    attestation: QualityAttestation | None = None

    if not funded:
        for s in owing:
            actions.append(
                f"reminder: {s['name']} still owes {s['shortfall']} "
                f"of their {s['expected']} share"
            )
        actions.append(
            f"hold: pot is {pot} of {target}; no purchase below target"
        )
    elif already_verified:
        actions.append("circle already verified; nothing to do")
    else:
        planned = plan_purchase(pot, target, price_per_bag)
        assert planned is not None  # funded guarantees an order
        purchase = PurchaseOrder(
            supplier=supplier_name,
            grade=grade,
            bags=planned.bags,
            price_per_bag=price_per_bag,
            total_cost=planned.total_cost,
            leftover=planned.leftover,
        )
        delivery = build_delivery(purchase, supplier_name, supplier_account)
        attestation = build_attestation(purchase, verifier_name, verifier_account)
        actions.append(
            f"target reached: pot {pot} >= target {target}"
        )
        actions.append(
            f"bulk purchase fired: {purchase.bags} bags of {grade} "
            f"from {supplier_name} for {purchase.total_cost}"
        )
        actions.append(
            f"signature 1 of 2: delivery record ready for the supplier "
            f"account {supplier_account}"
        )
        actions.append(
            f"signature 2 of 2: QC attestation ready for the verifier "
            f"account {verifier_account} ({verifier_name})"
        )
        actions.append(
            "circle closes as verified only when both signatures are "
            "recorded on NEAR testnet and QC passed"
        )

    return TickResult(
        pot=pot,
        target=target,
        remaining_to_target=max(0, target - pot),
        funded=funded,
        shortfalls=owing,
        total_shortfall=total_shortfall,
        actions=actions,
        purchase=purchase,
        delivery=delivery,
        attestation=attestation,
    )


def validate_contribution(
    farmer: FarmerState, amount: int, circle_closed: bool
) -> None:
    """Agent-level contribution rules. Raises ValueError on any violation.

    (The NEAR contract enforces its own simpler rules on-chain: known
    member, positive amount, circle still open. The per-member share cap
    is an Ajo fairness rule and lives here, with the treasurer.)
    """
    if circle_closed:
        raise ValueError("circle is already verified; contributions are closed")
    if amount <= 0:
        raise ValueError("contribution amount must be positive")
    if amount > farmer.shortfall:
        raise ValueError(
            f"contribution {amount} exceeds {farmer.name}'s remaining "
            f"share of {farmer.shortfall}"
        )
