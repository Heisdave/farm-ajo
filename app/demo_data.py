"""Bundled deterministic demo data — no live API keys, no network needed.

The farmers below are fictional demo people (plausible Nigerian smallholder
names/crops), created for this hackathon demo. Amounts are *demo units*
standing in for naira-denominated testnet credits — no real money, no real
payments. The seed is arranged so the demo tells the whole story:

  * the circle is part-way funded when you first look at it,
  * two members still owe money (one paid half, one has not paid yet),
  * recording those two shortfalls exactly reaches the target, so the
    agent tick can fire the bulk purchase and produce the QC receipt.

Circle economics (all demo units):
  8 members x 5,000 contribution            = 40,000 pot at full funding
  target                                    = 40,000
  bulk price                                =  2,000 per 50 kg bag
  => funded pot buys                        = 20 bags of NPK 15-15-15
"""

from __future__ import annotations

CIRCLE = {
    "name": "Planting Season Circle - Kaduna (demo)",
    "target": 40_000,
    "contribution_amount": 5_000,
    "fertilizer": {
        "grade": "NPK 15-15-15",
        "bag_kg": 50,
        "price_per_bag": 2_000,
        "supplier": "Kaduna Agro Inputs Ltd (demo supplier)",
    },
    "season_note": "Contributions close before planting, when fertilizer "
                   "prices spike; the circle buys in bulk ahead of the spike.",
}

# The two-signature trust model, as named roles in the demo scenario.
# The contract takes these two NEAR testnet accounts at circle creation
# and enforces them by caller: only the supplier account can record the
# delivery; only the verifier account can attest the quality. They are
# different accounts on purpose — the supplier cannot mark its own
# homework. (Testnet infrastructure accounts for the demo; see
# DEPLOY_NOTES.md.)
ROLES = {
    "supplier": {
        "name": CIRCLE["fertilizer"]["supplier"],
        "account": "supplier.farmajo-dev.testnet",
    },
    "verifier": {
        # A named, accountable person — in production this is the
        # co-operative's known QC officer. Her attestation history is
        # public on-chain, so her name is her bond.
        "name": "Fatima Sule — QC Verifier, Kaduna Farmers' Co-operative (demo)",
        "account": "verifier.farmajo-dev.testnet",
    },
}

# paid = amount already recorded for this member when the demo is seeded.
FARMERS: list[dict] = [
    {"farmer_id": "farmer-amina-bello",     "name": "Amina Bello",     "crop": "maize",    "location": "Kaduna",  "paid": 5_000},
    {"farmer_id": "farmer-yusuf-abdullahi", "name": "Yusuf Abdullahi", "crop": "sorghum",  "location": "Kaduna",  "paid": 5_000},
    {"farmer_id": "farmer-ibrahim-sani",    "name": "Ibrahim Sani",    "crop": "rice",     "location": "Kaduna",  "paid": 5_000},
    {"farmer_id": "farmer-ngozi-eze",       "name": "Ngozi Eze",       "crop": "soybean",  "location": "Makurdi", "paid": 5_000},
    {"farmer_id": "farmer-musa-garba",      "name": "Musa Garba",      "crop": "millet",   "location": "Katsina", "paid": 5_000},
    {"farmer_id": "farmer-funke-adebayo",   "name": "Funke Adebayo",   "crop": "tomatoes", "location": "Kaduna",  "paid": 5_000},
    # Paid half; balance due after market day (seeded shortfall: 2,500).
    {"farmer_id": "farmer-halima-usman",    "name": "Halima Usman",    "crop": "groundnut", "location": "Kano",   "paid": 2_500},
    # Has not paid yet (seeded shortfall: 5,000).
    {"farmer_id": "farmer-emeka-nwosu",     "name": "Emeka Nwosu",     "crop": "cowpea",   "location": "Kaduna",  "paid": 0},
]
