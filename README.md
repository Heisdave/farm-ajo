# Farm Ajo

**Farmers save together so they can afford fertilizer before planting.**

Farm Ajo is an agent-run **Ajo** (*rotating group savings circle*) for
smallholder farmers. A circle of farmers each contributes a small fixed
amount toward one shared target: a bulk purchase of fertilizer before
planting season, when prices spike. An agent treasurer tracks every
contribution and shortfall; the moment the pot reaches the target it
triggers the bulk purchase. The delivery and the quality check then
take **two signatures** on NEAR testnet: the supplier signs what it
delivered, and a named, independent QC verifier signs what the check
found. Neither can do the other's job, so "quality verified" is a
claim with a name and an account behind it, not a label anyone can
print.

Built for the NEAR Hackathon (Build Beyond Boundaries), primary track
**Real-World Money**, also fitting Autonomous Business, Social Money,
and Agent Economy.

**How does a farmer contribute?** The way Ajo already works: in
**naira**, by bank transfer, USSD, mobile money, or cash handed to the
co-operative. No wallet, no app to install, no coding. The farmer
never has to touch the software at all. The agent treasurer records
each contribution; NEAR is where the public receipt lives. (The full
answer is under "Where does the money actually move?" below.) The
farmer-facing surface in production is the channels farmers already
use: the co-operative officer, USSD, or a chat bot on
Telegram/WhatsApp talking to this same agent; this demo shows the
agent's book and the record it writes.

## Run it (do X, see Y)

Prerequisites: Python 3.11+. No API keys, no wallet needed.

```bash
cd farm-ajo
./run.sh
```

`run.sh` sets everything up itself. It creates the Python
environment, installs the dependencies, and starts the demo on port
8792. No manual venv steps. (Manual equivalent:
`python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/uvicorn app.main:app --port 8792`.)

Then, in another terminal:

```bash
# 1. See the circle, part-way funded: pot 32500 of 40000, state "open"
curl localhost:8792/circle

# 2. See who still owes: Halima 2500, Emeka 5000
curl localhost:8792/farmers

# 3. Run the agent below target: it lists shortfalls and refuses to buy
curl -X POST localhost:8792/agent/tick

# 4. Record the two missing contributions (simulated testnet/demo units)
curl -X POST localhost:8792/contributions -H 'Content-Type: application/json' \
  -d '{"farmer_id": "farmer-emeka-nwosu", "amount": 5000}'
curl -X POST localhost:8792/contributions -H 'Content-Type: application/json' \
  -d '{"farmer_id": "farmer-halima-usman", "amount": 2500}'

# 5. The pot is now exactly 40000. Run the agent again: it fires the bulk
#    purchase (20 bags of NPK 15-15-15) and generates BOTH signature
#    payloads: record_delivery for the supplier account and
#    attest_quality for the QC verifier account
curl -X POST localhost:8792/agent/tick

# 6. Read the stored two-signature receipt back ("Delivered by" and
#    "Quality attested by" are separate lines, signed by separate accounts)
curl localhost:8792/receipts
```

Run the tests any time:

```bash
.venv/bin/python -m pytest tests/ -q     # agent logic + demo page: 11 tests
```

Reset the demo to its seeded state:

```bash
rm data/farm_ajo.db   # it re-seeds on the next request
```

## What NEAR does here, in plain words

The agent keeps the working copy of the books. NEAR holds the public
copy: a record written there proves it existed and who signed it, and
it stays readable by anyone. The chain cannot prove a record was
*true* when it was written. That trust sits with the named people
whose signatures are on it (see the Q&A below). The Ajo circle
contract on NEAR testnet
stores the circle's target and contribution amount, every member's
contributions and the pot total, whether the circle is open, funded,
delivered, or verified, and, at the end, the two-signature receipt:
the supplier's delivery record (bags, blend grade, total cost) and the
QC verifier's attestation (the named checks, pass/fail, notes), each
signed by its own designated account. A farmer, a cooperative, or a
judge can read all of it back from the chain without trusting the
agent or this API.

An Ajo runs on trust in the treasurer. Putting the pot and the receipt
on a public record is what lets the circle grow beyond people who
already know each other.

## Who attests the quality, and why should anyone trust them?

The obvious attack on any "quality verified" badge is that anyone can
type it. Farm Ajo's answer is a **named verifier role**, enforced by
the contract, not by trust in this API:

- At circle creation, the contract records one designated **QC
  verifier account** (in the demo: the account of Fatima Sule, the
  co-operative's QC verifier). Only that account can call
  `attest_quality`. The call itself checks the caller.
- The **supplier cannot mark its own homework**: the supplier's
  account can only record the delivery. It tried to attest on testnet,
  in a real transaction, and the contract rejected it (tx
  `6DZRifxszL9c3Ji3BgBeprnKFN6gkdScw32zGRzYxLQW`. See
  DEPLOY_NOTES.md). The verifier likewise cannot invent a delivery.
- In production the verifier is a person the circle already has reason
  to hold accountable: the co-operative's known QC officer. The
  checks themselves were designed from the founder's own production
  and quality-control work at a fertilizer blending plant.
- And the verifier's **whole attestation history is public**. Every
  pass they ever sign sits next to their name, forever. A verifier who
  passes bad fertilizer burns the only asset they have in the system:
  their name. That is the bond.

## Where does the money actually move?

Not on the chain. In production the money moves the way Ajo money
already moves today: in naira, through the channels the farmers
already use:

- Each farmer pays their share by bank transfer, USSD, mobile money,
  or cash handed to the co-operative, exactly as a paper-notebook Ajo
  runs now. The pooled money sits in the co-operative's bank account,
  as it does today.
- The agent treasurer is the bookkeeping and trigger layer, not a
  wallet: it records each contribution against the circle's terms,
  shows who still owes, and issues the purchase instruction the
  moment the pot reaches the target.
- The supplier is paid in naira by ordinary bank transfer from the
  co-op's account, released by the account's signatories (mirroring
  the two-signature model the receipt uses), and never touches
  crypto. (Wiring that release to a payment provider's transfer API
  is roadmap, not built.)
- NEAR's job is the public receipt book: who paid what, when the
  purchase fired, what was delivered, and who signed for its
  quality. That is exactly what today's notebook cannot give the
  circle. When a dispute starts over who paid, or what actually
  arrived, there is nothing settled to point at. A public record
  everyone can check is what those arguments get settled against.

In this demo, nothing moves at all: contributions are records on
testnet, and the contract tracks amounts and does not custody funds.

## The contract

`contracts/ajo-circle/` (Rust, near-sdk pinned `=5.1.0`; see
BUILD_NOTES.md for why):

- `new(name, target, contribution_amount, members, supplier_account,
  verifier_account)`: create a circle and designate the two role
  accounts (they must differ)
- `contribute(member, amount)`: record a contribution; flips the
  circle to `funded` when the pot reaches the target
- `record_delivery(supplier_name, bags, grade, total_cost, notes)`:
  **supplier account only**; records what was delivered; flips
  `funded` to `delivered`
- `attest_quality(verifier_name, qc_passed, checks, notes)`:
  **QC verifier account only**, and only after a delivery; flips
  `delivered` to `verified` when QC passed
- `get_circle` / `get_member` / `get_delivery` / `get_attestation`:
  public read-backs

```bash
cd contracts/ajo-circle && cargo test     # 13 unit tests
bash ../../scripts/build_contract.sh      # -> res/farm_ajo_circle.wasm
```

Prefer a page over curl? Open **http://localhost:8792/demo** for a
one-page status view of the circle (pot progress, who has paid, who
still owes, the agent treasurer's own activity log, and the
purchase/QC receipt once the circle is funded), including the live
testnet contract and transaction links below. The log is also at
`GET /agent/log`. The demo video on the X post is `demo/farm-ajo-demo-friend-cut.mp4` (76 s, a community cut of this same demo, with the submission end card added). `demo/farm-ajo-live-run.mp4` (50 s) is a live-run proof: one command (`./run.sh`), the full circle, real output (capture and build script in `demo/proof/`). The in-house cut is `demo/farm-ajo-demo-v5_1.mp4` (59 s, Inspiring Gong voiceover; script in `demo/VOICEOVER.md`; v5.1 fixes the line-5 pace at 0:30–0:42; v5, v4 and v3 kept as fallbacks).

### Testnet deploy (EXECUTED 2026-11-10; see DEPLOY_NOTES.md)

The current (v2, two-signature) contract is live on NEAR testnet at
**`circle2.farmajo-dev.testnet`** and the full demo loop has been run
on-chain end-to-end: 9 contributions → pot 40,000 → funded → two
deliberate role-violation attempts rejected → delivery signed by
`supplier.farmajo-dev.testnet` → QC attestation signed by
`verifier.farmajo-dev.testnet` → state **`verified`**. Every
transaction hash and the explorer links are in
[DEPLOY_NOTES.md](DEPLOY_NOTES.md); the ids/hashes are also in
`onchain.json`. (The v1 single-signature deployment at
`circle.farmajo-dev.testnet` remains on-chain as the phase-2 record.)

Verify it yourself, from any account (near-cli-rs syntax):

```bash
near contract call-function as-read-only circle2.farmajo-dev.testnet \
  get_circle json-args '{}' network-config testnet now
# -> pot 40000, state "verified", member_count 8, both signatures present
near contract call-function as-read-only circle2.farmajo-dev.testnet \
  get_attestation json-args '{}' network-config testnet now
# -> the QC attestation, attested_by the verifier account
```

To redeploy from scratch: create a faucet-funded testnet account
(Muse-side build infrastructure; the prize payout address is a
separate mainnet account), give the contract account ~5 testnet NEAR
(storage staking for the 219 KB wasm), then deploy with the circle's
`new` init call. Note: this contract's `u128` fields take **JSON
numbers**, not strings. See DEPLOY_NOTES.md for the exact commands
as run.

## How this was built (disclosure)

Farm Ajo was built **from scratch inside the hackathon window** (the
concept was locked on 10 Nov 2026; the founder has no prior code repo
for it). It starts from a generic scaffold the same builder produced
earlier in the window: a FastAPI + SQLite service skeleton and the
pinned Rust/near-sdk contract toolchain, both concept-agnostic and
verified before the concept existed. Everything Farm Ajo-specific (
this design, the Ajo circle contract, the agent treasurer, the demo
scenario) is new work in the window. See DESIGN.md for the design and
the honest limitations (simulated payments and delivery, member-id
identity, one circle per deployment) and BUILD_NOTES.md for the full
verification record.

## The founder's angle

The QC receipt is not decoration. The founder spent a 6-month
industrial placement in production and quality control at a fertilizer
blending plant in Kaduna State, Nigeria, and is a final-year
agricultural engineering student. Bad or underweight fertilizer is a
real way smallholders lose money; the receipt records the checks that
catch it: bag count, sample weights against the nominal 50 kg,
granule uniformity and caking, batch-label grade. That is what
a delivery check actually looks like.
