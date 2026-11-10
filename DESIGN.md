# Farm Ajo — Design

**Farmers save together so they can afford fertilizer before planting.**

## The problem

Fertilizer is cheapest and most useful *before* planting season — and that
is exactly when a smallholder farmer has the least cash, because last
season's income is spent and this season's hasn't arrived. By the time a
farmer can pay retail, prices have spiked and planting is already late.
One farmer alone cannot fix that. Eight farmers saving together, ahead of
the season, can: pooled early money buys in bulk at pre-season prices.

Nigeria already has the savings technology for this — **Ajo** (also
*esusu*), the rotating savings circle: a trusted group, a fixed
contribution, a treasurer everyone watches. What Ajo doesn't have is a
treasurer whose records sit in public where everyone can check them,
and a purchase that fires the moment the money is complete. That is
the gap Farm Ajo fills.

## The product

Farm Ajo is an Ajo circle run by an agent treasurer, aimed at one shared
target: a bulk fertilizer purchase before planting.

- **Circle.** A fixed group of farmers (8 in the demo), each owing the
  same fixed contribution per round, saving toward a target the group
  chose (in the demo: 40,000 units — exactly 20 bulk bags of NPK
  15-15-15 at 2,000 per bag).
- **Agent treasurer** (the FastAPI service in `app/`). It tracks who has
  paid and who still owes (shortfalls), reminds the members who are
  behind, and — only when the pot reaches the target — fires the bulk
  purchase and produces the delivery + quality-check receipt.
- **NEAR testnet contract** (`contracts/ajo-circle/`) is the circle's
  public record: circle terms, every contribution, the pot, the circle
  state, and the final purchase/QC receipt. The receipt takes two
  signatures from two designated accounts set at circle creation — the
  supplier signs the delivery, a named QC verifier signs the quality
  attestation — and the contract rejects either role doing the other's
  job. Anyone can read it all back.

## User loop

1. A circle forms around a target: "20 bags of NPK before planting."
2. Each farmer contributes their fixed share in small payments, whenever
   cash comes in (after market day, after a side sale). Partial payments
   are normal and tracked, not penalised.
3. The agent watches the pot. Members who still owe get a clear shortfall
   figure — no arguments, the record is public.
4. The moment the pot reaches the target, the agent triggers the bulk
   purchase from the supplier — before the planting-season price spike.
5. The fertilizer is delivered, and the supplier records the delivery
   on-chain from its own account: bags, grade, total cost. A QC check
   then runs at delivery — bag count, sample weights against the
   nominal 50 kg, granule uniformity/caking, and batch-label grade
   against the ordered grade — and the circle's named QC verifier
   attests the result from *her* account. (The founder did production
   and quality control at a fertilizer blending plant; this step is
   written from that floor, not from a brochure.)
6. Only when both signatures exist and QC passed does the circle close
   as `verified` on NEAR testnet. Every member can verify what was
   bought, who delivered it, and who vouched for its quality.

## Demo scenario (seeded, deterministic)

Eight fictional Kaduna-area farmers (maize, sorghum, rice, soybean,
millet, tomatoes, groundnut, cowpea), one circle, target 40,000. When the
demo starts, six members have paid in full, Halima has paid half (owes
2,500), and Emeka hasn't paid yet (owes 5,000) — pot 32,500 of 40,000.
The walkthrough records Emeka's 5,000 and Halima's 2,500, the pot hits
the target exactly, the agent tick fires, and out comes the purchase
order (20 bags) plus the two exact payloads for the contract's
`record_delivery` (supplier) and `attest_quality` (verifier) calls.
Total demo time: about two minutes.

## What NEAR does, concretely

- **Circle state on testnet:** target, contribution amount, member list,
  per-member contributions, pot total, and state
  (`open` → `funded` → `delivered` → `verified`) live in the contract — not in the
  agent's private database. The agent mirrors them off-chain for the UI;
  the chain is the public copy — written once, readable by anyone, with
  every signature attached to it.
- **Receipts on testnet:** the delivery is written by
  `record_delivery` (supplier account only) and the QC result by
  `attest_quality` (verifier account only), and read back by anyone
  with `get_delivery` / `get_attestation` / `get_circle`. The chain
  proves the receipt existed and who signed it; it cannot prove the
  fertilizer was good — that trust sits with the named verifier, whose
  name and history are on the record. A later season's circle can
  point at the receipt as track record.
- **Why a chain at all:** an Ajo runs on trust in the treasurer. Putting
  the pot and the receipt on a public record is what lets a circle scale
  past the people who already know each other — and lets a cooperative or
  an input supplier trust a circle they've never met.

## Who attests the quality, and why should anyone trust them?

"Quality verified" is cheap to type — this is the question the design
has to survive, so it is answered in the mechanism, not in marketing:

- **A named verifier role, set at circle creation.** The contract
  stores one designated QC verifier account. Only that account's calls
  to `attest_quality` are accepted; everyone else's are rejected by
  the contract itself. In the demo the verifier is a named person —
  Fatima Sule, the co-operative's QC verifier.
- **The supplier cannot mark its own homework.** The supplier account
  can record the delivery and nothing else; the verifier account can
  attest and cannot invent a delivery. Both directions were attempted
  on testnet and both were rejected on-chain (DEPLOY_NOTES.md).
- **Production shape:** the verifier is the co-operative's known QC
  officer — a person with a name, a face, and a job on the line. The
  checks she signs were designed from the founder's own production/QC
  work at a fertilizer blending plant.
- **The verifier's name is their bond.** Their entire attestation
  history is public and permanent. Passing bad fertilizer once is
  visible forever, next to their name. Honesty is the only strategy
  that keeps the name valuable.

## Track fit

- **Real-World Money (`realworld`) — primary.** Payroll/invoicing/
  remittances are the examples; this is the same shape for farm inputs:
  ordinary people pooling ordinary money for something a normal business
  (here, a farm) would use tomorrow, on stablecoin-style rails.
- **Autonomous Business (`business`).** The agent treasurer *is* an
  autonomous business function: it collects, accounts, decides when the
  funding condition is met, executes the purchase, and files the receipt,
  with humans only setting the constraints (target, share, grade).
- **Social Money (`social`).** Ajo is social money in its original form:
  shared budgets and collective purchasing coordinated by reputation and
  a shared record.
- **Agent Economy (`agents`).** The agent doesn't just advise — it holds
  the books and acts (buys) when its condition fires, and its actions are
  verifiable on-chain afterwards.

## Scope for the remaining days (to Sat 14 Nov 23:59 UTC)

- **Done (phase 1):** this design; the Ajo circle contract with unit
  tests + wasm build; the FastAPI agent with seeded demo, shortfalls,
  the funding trigger, and QC receipt generation; judge-proof README.
- **Phase 2 (done, 2026-11-10):** contract deployed to NEAR testnet at
  `circle.farmajo-dev.testnet` (Muse-side faucet-funded infrastructure
  account — Dexter's wallet app offers no testnet account), and the
  full loop recorded on-chain end-to-end: 9 contributions → funded →
  purchase + QC receipt. See DEPLOY_NOTES.md. A demo status page
  (`GET /demo`) shows the circle at a glance, with the on-chain links.
- **Trust upgrade (done, 2026-11-10):** the single-signature receipt
  was replaced by the two-signature trust model (supplier delivery
  record + named-verifier QC attestation, role-gated in the contract),
  redeployed at `circle2.farmajo-dev.testnet` with the full loop —
  including two deliberate, rejected role-violation attempts — run
  on-chain to the final `verified` state. The demo video was produced
  the same day and its current cut (v3, with voiceover) shows the two
  signatures (see BUILD_NOTES.md).
- **Phase 3:** demo surface polish (a simple status page or Telegram
  view), the demo video, the public repo, the X demo post (Dexter posts
  from his phone), and the submission with the payout address
  `dexter01.near`.

## Honest limitations

- **Simulated payments.** Contributions in this build are demo records
  (SQLite + contract calls with integer demo units). No real or testnet
  token transfers happen in phase 1; the contract tracks amounts, it
  does not custody funds. Real custody would use a fungible-token
  contract and `ft_transfer_call`.
- **Simulated delivery/QC.** The demo delivery and its QC result are
  scripted demo data (marked as such inside the receipt's notes). The
  checks themselves are the real checks used at a blending plant; no
  real fertilizer moved.
- **Where the money moves.** This build demonstrates the record
  layer, and that split is deliberate. In production the money stays
  in naira and moves the way Ajo money moves today: farmers pay by
  bank transfer, USSD, mobile money, or cash to the co-operative,
  and the pooled money sits in the co-operative's bank account. The
  agent treasurer is the bookkeeping and trigger layer — it records
  each contribution against the circle's terms and issues the
  purchase instruction the moment the pot reaches the target; the
  release is authorised by the co-op account's signatories
  (mirroring the two-signature model) or, later, through a payment
  provider's transfer API — that integration is roadmap, not built.
  The supplier is paid by ordinary bank transfer and needs no
  crypto. NEAR is the public receipt book — contributions, purchase,
  delivery, QC attestation — not the payment rail: the public
  record is what settles the disputes a paper notebook cannot (who
  paid, what was delivered, who checked it).
- **Member identity.** The contract records contributions by member id
  because the demo's farmers are simulated by the agent. Production
  would bind contributions to each farmer's own NEAR account
  (`predecessor_account_id`).
- **Purchase permissions (fixed in the trust upgrade).** Delivery and
  attestation are role-gated in the contract: only the designated
  supplier account can record a delivery, only the designated
  verifier account can attest quality, and the two must be different
  accounts. Contributions are still recorded by the operator account
  on behalf of member ids (see Member identity above).
- **One circle per deployment.** Deliberate simplification: a factory
  contract that spawns circles is a phase-4 concern, not a demo one.
