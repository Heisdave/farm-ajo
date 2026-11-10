# BUILD_NOTES — Farm Ajo, phase 1 (2026-11-10)

Concept locked by Dexter on 2026-11-10. Built from scratch in the
hackathon window on the concept-agnostic groundwork at
`~/workspace/projects/draintrap-near/` (FastAPI + SQLite scaffold pattern
and the pinned Rust/near-sdk toolchain — that folder is untouched and
remains the reference). Everything below was **run and observed**, not
assumed.

## 1. Python agent + API — VERIFIED

Environment (same recipe as the groundwork):

```bash
cd ~/workspace/projects/farm-ajo
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt   # fastapi 0.162.2, uvicorn, pydantic, httpx, pytest
.venv/bin/python -m pytest tests/ -q        # -> 8 passed in 0.04s
```

Pytest coverage (`tests/test_agent.py`): seeded shortfalls are exact
(Halima 2,500 / Emeka 5,000, total 7,500); seeded pot 32,500; the trigger
does **not** fire below target (no purchase, reminder actions only); it
fires exactly at target (20 bags, cost 40,000, leftover 0) and above
target (order sized on target, leftover kept); a QC receipt is generated
only when funded and its payload has exactly the contract's
`record_purchase` fields; no second purchase once purchased; contribution
validation rejects zero/negative/over-share/post-purchase.

Live API run (executed 2026-11-10, server on port 8792, fresh DB):

| Step | Call | Observed |
|---|---|---|
| health | `GET /health` | `{"status":"ok","service":"farm-ajo","data_mode":"demo"}` |
| seeded circle | `GET /circle` | pot **32500** of target 40000, state **open**, 6/8 fully paid, shortfall 7500 |
| members | `GET /farmers` | Halima paid 2500 owes 2500; Emeka paid 0 owes 5000; rest owe 0 |
| tick below target | `POST /agent/tick` | `funded:false`, purchase/receipt null, actions = 2 reminders + "no purchase below target" |
| over-share contribution | `POST /contributions` Emeka 6000 | **422** "exceeds Emeka Nwosu's remaining share of 5000" |
| contribute | Emeka 5000 | pot **37500**, state open |
| contribute | Halima 2500 | pot **40000**, state **funded** |
| tick at target | `POST /agent/tick` | purchase fired: **20 bags NPK 15-15-15, total 40000**; QC receipt stored (id 1), `qc_passed:true`, 4 named checks; response includes the exact `record_purchase` NEAR payload; circle state **purchased** |
| read-back | `GET /receipts` | receipt id 1 present with full notes, `near_tx_hash: null` (nothing sent on-chain — by design) |
| tick again | `POST /agent/tick` | idempotent: `purchase_generated_now:false`, "purchase already recorded" |
| contribute after purchase | `POST /contributions` | **422** "circle has already purchased; contributions are closed" |

Server stopped and `data/farm_ajo.db` deleted afterwards, so the next
start re-seeds to the demo's opening state.

## 2. NEAR contract — VERIFIED

Contract: `contracts/ajo-circle/` (Rust, near-sdk pinned `=5.1.0`, same
toolchain decision and rationale as the groundwork — plain cargo +
`wasm32-unknown-unknown`, no cargo-near).

```
$ cargo test
test tests::contributions_accumulate_per_member_and_in_pot ... ok
test tests::pot_reaching_target_flips_circle_to_funded ... ok
test tests::purchase_receipt_is_recorded_after_funding ... ok
test tests::zero_contribution_is_rejected - should panic ... ok
test tests::unknown_member_contribution_is_rejected - should panic ... ok
test tests::purchase_before_funding_is_rejected - should panic ... ok
test tests::contribution_after_funding_is_rejected - should panic ... ok
test result: ok. 7 passed; 0 failed

$ bash scripts/build_contract.sh
Finished `release` profile [optimized] target(s) in 28.40s
-rwxrwx--- 200K contracts/ajo-circle/res/farm_ajo_circle.wasm
```

Two compile/runtime gotchas hit and fixed during this build — recorded
so they are not rediscovered:

1. **Hand-written borsh derives on a state enum do not resolve** against
   near-sdk 5.1.0's re-exported borsh on this toolchain ("the trait
   BorshDeserialize is not implemented for CircleState", 4 errors). Fix:
   get borsh from the near macro — `#[near(serializers = [borsh])]` —
   the same pattern the structs already used. (Also noted in a comment
   at the enum in `src/lib.rs`.)
2. **`env::panic_str` aborts unit tests** (SIGABRT, "non-unwinding
   panic") instead of producing a catchable panic, which kills the whole
   test process and hides other results. The groundwork contract never
   had a test reach a `panic_str` path; this contract does (unknown
   member). Fix: plain `panic!("member is not in this circle")` in the
   two member-lookup paths. On-chain behaviour is equivalent (the call
   fails with the same message); test behaviour is catchable by
   `#[should_panic]`.

## 3. Not done (by design / next phases)

- **No deployment.** Dexter's wallet app offers no testnet account; the
  deploy is Muse-side build infrastructure needing a faucet-funded
  testnet account that does not exist yet. Exact deploy + call commands
  are documented in README.md. Until then, the API prepares exact
  contract payloads and stores everything locally.
- **No on-chain end-to-end run yet** — phase 2 wires the API payloads
  into real `near` CLI calls (create circle → contribute ×8 →
  record_purchase → view read-backs) once the testnet account exists.
- **No frontend, no public repo, no X post, no submission** — later
  phases, per the local-only constraint on this phase.
- Payout/mainnet facts for the eventual submission (already on record):
  payout address `dexter01.near`; Dexter's phone X app is logged in, so
  the demo post path works from his phone.

## Constraints honoured

Local files only · testnet/demo data only · no deployment · no real
funds · no secrets (`.gitignore` covers `.env`, key files, build output,
the SQLite db) · no public repo · nothing posted · nothing submitted ·
groundwork folder left intact.

---

# BUILD_NOTES — Farm Ajo, phase 2 (2026-11-10)

Full deployment record with every transaction hash: **DEPLOY_NOTES.md**.
Summary of what was run and observed:

## 4. Testnet deployment + on-chain end-to-end run — VERIFIED

- **Tooling:** near-cli-rs 0.31.1 (binary at `~/near-tools/`, outside
  the repo). Keys in the legacy keychain `~/.near-credentials/testnet/`
  — outside the repo tree; the repo `.gitignore` also covers `hidden/`,
  `*.testnet`, `neardev/`, `*.json.key` (verified).
- **Accounts:** `farmajo-dev.testnet` created via the faucet service
  (10 testnet NEAR; creation tx
  `4YAYJcfxVN84uUy15jH4fg2GvEuEYcgQZCNbTAfaKiF2`);
  `circle.farmajo-dev.testnet` created as its subaccount. Muse-side
  build infrastructure only — Dexter's mainnet payout account
  (`dexter01.near`) was not touched.
- **Deploy + init succeeded** on the third attempt:
  tx `5GK8AnDGZEBB9UQSCgDLUgncE5LJW7fY7iohLNUXuq1W`. Circle read back
  on-chain: pot 0 → `open`, 8 members.
- **Two failures first, both instructive** (details in DEPLOY_NOTES):
  (1) init rejected **string-encoded u128** — this contract's plain
  `u128` fields take JSON *numbers*, unlike the `U128` wrapper type;
  the tx rolled back completely. (2) ~2 NEAR does not cover storage
  staking for a 200 KB contract — topped the account up to ~5 NEAR.
- **Full loop on-chain:** 9 `contribute` calls mirroring the seeded
  demo (6 members × 5000, Halima 2500, Emeka 5000, Halima 2500) → pot
  **40000**, state flipped to **`funded`** on-chain. Then
  `record_purchase` (tx
  `3ot66BfcPX8krpYschuieomPRQMpLPjwgGjz4yGPUND5`) with the QC receipt —
  20 bags NPK 15-15-15, `qc_passed: true`, the 4 named QC checks in the
  notes. Read-backs: `get_purchase` returned the stored receipt;
  `get_circle` → pot 40000, state **`purchased`**. ✔

## 5. Demo status page — VERIFIED

- `GET /demo` added to the FastAPI app (server-rendered HTML, no new
  dependencies): opening line, circle name, status, pot progress bar
  (pot vs target + %), a per-farmer table (paid / still-owes chips),
  the purchase + QC receipt card when purchased, and an "On NEAR
  testnet" card with the contract account, deploy tx and purchase tx
  links, read from `onchain.json` (public ids/hashes only) when present.
- Live check (server on port 8793, fresh DB):
  - Seeded state: HTTP 200 — pot **32,500**, "Saving — circle open",
    Halima "Owes 2,500", Emeka "Owes 5,000", contract id shown.
  - After POSTing Emeka 5000 + Halima 2500 and `POST /agent/tick`:
    HTTP 200 — "**Purchased — receipt on NEAR testnet**", pot 40,000,
    receipt card with QC **PASSED** and the purchase tx hash linked.
- Server stopped afterwards and `data/farm_ajo.db` deleted, so the next
  start re-seeds to the demo's opening state.

## 6. Test suites re-run after phase-2 changes

```
.venv/bin/python -m pytest tests/ -q   # -> 8 passed
cargo test (contracts/ajo-circle)      # -> 7 passed; 0 failed
```

## Phase-2 constraints honoured

Testnet only · no mainnet · no real funds (faucet testnet NEAR only) ·
nothing public (no public repo, nothing posted, nothing submitted) ·
Dexter's accounts (`dexter01.near`, GitHub `Heisdave`) not logged into
or used · credentials outside the repo tree · groundwork folder intact.

---

# BUILD_NOTES — Farm Ajo, demo video (2026-11-10)

Deliverables: `demo/farm-ajo-demo.mp4` + `demo/poster.png` (local only,
nothing posted or submitted).

## How it was made (Dexter's established workflow)

- Ran the real FastAPI app (port 8792, fresh seeded DB) and drove it
  with Playwright (its own Chromium headless shell — the system
  `/opt/meta-chromium/chrome` refuses direct launch: "Hatch WebGL
  domain policy is required", so Playwright's chromium build was
  installed and used). Screenshots are genuine renders of `GET /demo`
  at each state: seeded (pot 32,500; Halima owes 2,500, Emeka owes
  5,000) -> Emeka contributes 5,000 via the API (members view) ->
  Halima contributes 2,500 (funded, pot 40,000) -> `POST /agent/tick`
  (purchased) -> the receipt card and the "On NEAR testnet" card as
  element screenshots. Working shots in `work_shots/`.
- Frames composited with Python/Pillow on a dark olive/brown smoky
  background (gradient + blurred blobs + vignette), captions burned in,
  pitch line from Dexter's framing note on the title and end cards:
  **"Ajo, but the pot has a job."** The phrase "decentralized
  fertilizer procurement" appears nowhere.
- Encoded with ffmpeg: 8 stills -> segments (0.45 s fades) -> concat.
  libx264, crf 18, yuv420p, 30 fps, 1920x1080, no audio (captions only).

## Verification (run, observed)

- ffprobe: duration **59.0 s**, 1920x1080, h264, yuv420p, 30/1 fps,
  2,318,002 bytes.
- Frames extracted from the final mp4 at t=3 (title), t=21 (members:
  Emeka "Paid in full", Halima "Owes 2,500"), t=47 (receipt/proof
  beats), t=56 (end card) and visually checked: all legible, real demo
  page (not mockups), dark olive/brown + sage palette — **no orange**
  (the page's "owes" chip is brown/tan, part of the real page),
  watermark "@heisdave01 / DEXTER WEB3" on title/end cards and small
  in the caption band of every page frame. No post-number badges.
- Beats: title (opening line + pitch line) -> the circle -> 
  contributions landing -> funded -> purchased + QC receipt close-up
  -> on-chain proof card (contract `circle.farmajo-dev.testnet`,
  purchase tx short hash `3ot66Bfc...GPUND5`, plus the real on-chain
  card from the page) -> end card ("Farm Ajo — Built at NEAR
  Hackathon").
- Server stopped and `data/farm_ajo.db` deleted afterwards — demo is
  back at its seeded opening state.

---

## Phase 3: two-signature trust model + pitch framing (2026-11-10)

Two steers from Dexter, folded in after the demo video was delivered
(the video was NOT re-cut; it stays truthful — the QC receipt exists —
and Friday's final cut will show the two signatures).

### Pitch framing
- Tagline locked: **"Ajo, but the pot has a job."** — added to the demo
  video's title card under the opening line. The banned phrase was
  checked for across video assets, README and DESIGN: absent.

### Contract v2 — role-gated signatures
`contracts/ajo-circle/src/lib.rs` rewritten:
- `new(...)` now also takes `supplier_account` + `verifier_account`
  and rejects a circle where they are the same account.
- `record_purchase` removed. In its place:
  - `record_delivery(supplier_name, bags, grade, total_cost, notes)` —
    predecessor must be the supplier account; funded-only; state
    funded -> delivered.
  - `attest_quality(verifier_name, qc_passed, checks, notes)` —
    predecessor must be the verifier account; requires a delivery;
    pass -> verified, fail -> attestation stored, state stays
    delivered.
- Views: `get_delivery`, `get_attestation`, `get_supplier_account`,
  `get_verifier_account`; `get_circle` returns roles + both records.
- **cargo test: 13 passed** (7 old + new: supplier cannot attest,
  verifier cannot deliver, stranger cannot deliver, attestation before
  delivery rejected, delivery before funding rejected, failed QC does
  not verify, same-account roles rejected). Wasm rebuilt: 219 KB.

### Agent / app
- `app/demo_data.py`: `ROLES` — supplier `supplier.farmajo-dev.testnet`
  ("Kaduna Agro Inputs Ltd (demo supplier)"), verifier
  `verifier.farmajo-dev.testnet` ("Fatima Sule — QC Verifier, Kaduna
  Farmers' Co-operative (demo)") — a named person, on purpose.
- `app/agent.py`: `DeliveryRecord` + `QualityAttestation` dataclasses
  mirroring the contract; the tick now builds BOTH payloads with
  `sign_as` and reports `verified` only when delivery exists AND QC
  passed. `validate_contribution` flag renamed to `circle_closed`.
- `app/main.py`: receipts store both signatures (delivered_by,
  supplier_account, attested_by, verifier_account, checks); local
  circle state is `verified` once a receipt exists; the /demo receipt
  card shows **"Delivered by"** and **"Quality attested by"** as
  separate lines; the chain card reads the contract id and the
  delivery/attestation txs from `onchain.json` (falls back to the v1
  purchase fields for the old file). Contribute payload now sends the
  amount as a JSON number, matching the contract.
- **pytest: 8 passed**, including a test pinning both payload shapes
  and `supplier_account != verifier_account`.

### On-chain (full detail in DEPLOY_NOTES.md v2 section)
- Created `circle2.farmajo-dev.testnet` (4 NEAR),
  `supplier.farmajo-dev.testnet` (0.3), `verifier.farmajo-dev.testnet`
  (0.3) under the phase-2 infrastructure account. V2 deployed fresh —
  NOT over v1 (borsh state layout changed); v1 stays as the phase-2
  record. Deploy+init tx `7YZLiKhmfXk5EiuwjuUeiukXwLhL3qLKbuuvDYJKrgR8`.
- 9 contributions -> pot 40,000, `funded`.
- **Two deliberate violations, both rejected on-chain:** supplier
  attesting (`6DZRifxszL9c3Ji3BgBeprnKFN6gkdScw32zGRzYxLQW`) and
  verifier delivering (`EUEgdTZ9VwxfLsBto8s5JnFH9xYKc5wh6FA5AAs4fEas`).
- Delivery signed by supplier (`BvkdEt8R3Df7QkJjKbUACoAgkUBDLgEfsXZhZ9TmUFtG`),
  attestation signed by verifier (`9dv6SwC2mBJrWezFLbrTwUHNmbkuepj7ozbwuTB9p57`).
  Final `get_circle` read-back: **pot 40000, state `verified`**, both
  signatures attributed to their accounts. `onchain.json` updated to
  v2 (v1 ids preserved inside it).
- Live local check: fresh DB -> seeded (32,500, open, /demo shows the
  v2 contract) -> contributions -> tick reports `verified_now` with
  both role payloads -> /demo shows "Purchased + verified — two
  signatures on NEAR testnet", both role lines, and both real tx
  hashes. Server stopped, demo DB reset afterwards.
- Docs: README + DESIGN carry the Q&A "Who attests the quality, and
  why should anyone trust them?" (named accountable verifier; supplier
  can't mark its own homework; the verifier's public history is the
  bond), and DESIGN's old "any account can call record_purchase"
  limitation is marked fixed.

Tests at close of phase: **pytest 8 passed, cargo test 13 passed**,
wasm builds via `scripts/build_contract.sh`.

## Fix round — external review of the demo video (2026-11-10)

An external review of the v1 video raised five fixes. All five are
done except two environment-blocked pieces, documented honestly
below (explorer screenshot, voiceover audio).

### Fix 1 — arithmetic (header vs members table)

- **What was wrong:** a v1 frame showed header "32,500 of 40,000 /
  6 of 8 paid in full" over a table summing to 37,500. Audit result:
  the seed data, the agent, and `/demo` were always internally
  consistent (verified by a scripted audit parsing header pot, table
  rows and `/circle` at five states — all agreed). The bug was in
  **v1 video assembly**: beats were composited from separate element
  screenshots captured at different states (seeded header +
  post-Emeka table in one frame).
- **Hardening anyway:** `demo_page()` now takes ONE farmer-state
  snapshot and `_circle_view(conn, farmers)` derives the header pot
  and paid-in-full count from that same snapshot the table renders —
  agreement is structural, not coincidental.
- **Regression test:** `tests/test_demo_page.py::
  test_demo_numbers_agree_at_every_state` renders `/demo` at seeded,
  after-tick, Emeka-paid, funded and verified states and asserts
  header pot == table sum and header count == full-share rows (and
  equality with `/circle`). This class of bug now fails CI.

### Fix 2 — receipt signatures + overclaim purge

- `/demo` receipt card now reads exactly: "Delivered by: **Kaduna
  Agro Inputs Ltd** (supplier.farmajo-dev.testnet)" and "Quality
  attested by: **Fatima Sule — QC Verifier**
  (verifier.farmajo-dev.testnet)", followed by the honest line: "The
  chain proves this record existed and who signed it. It cannot prove
  the fertilizer was good — that trust sits with the named verifier,
  whose name and history are on the record."
- Grep purge of overclaims across page/README/DESIGN/video captions:
  README's "the copy nobody can quietly change", DESIGN's "records
  nobody can quietly edit" / "the copy nobody can rewrite" /
  "a receipt cannot be edited after the fact", and v1's caption
  "Nobody can rewrite the record" are all replaced with the accurate
  version (chain proves existence + signers; truth of the QC claim
  rests on the named verifier). A test asserts the receipt card
  contains both signatures and the honest line, and no
  "nobody can rewrite".

### Fix 3 — agent treasurer activity log

- New SQLite table `agent_log` (timestamped lines, persisted), a
  `GET /agent/log` endpoint, and an "Agent treasurer — activity log"
  card on `/demo` (newest last). The agent writes its own lines:
  seeding ("circle seeded: pot 32,500 of 40,000…"), shortfall flags
  ("Shortfall: Halima Usman owes 2,500 · Emeka Nwosu owes 5,000"),
  contributions ("Contribution received: Emeka Nwosu +5,000
  (pot 37,500)"), below-target ticks, the trigger ("Pot reached
  40,000 — executing bulk purchase: 20 bags of NPK 15-15-15 for
  40,000"), both signature lines, and the verified close. Test:
  after a scripted run the log contains the shortfall flag, both
  contribution lines and the trigger line.

### Fix 4 — video v2 (`demo/farm-ajo-demo-v2.mp4`)

- Rebuilt with the v1 specs (1920×1080, h264, yuv420p, 30 fps,
  crf 18, dark olive/brown, no orange, watermark, tagline) by
  `demo/build_v2.py` from **whole-page single-state screenshots**
  (`demo/shots_v2/`, taken during a live scripted run of the app), so
  no frame can mix states. 59.1 s, 7 scenes: title → circle at
  32,500 (header and table agree on screen) → agent log shortfall
  flag → agent log contributions + purchase trigger → receipt with
  both named signatures (**6.5 s dwell**, vs ~21 s of receipt/proof
  beats in v1) → on-chain record → end card. Verified by extracting
  frames at 3/10/19/28/36/44/54 s and reading every number.
- **Explorer beat — FALLBACK USED, flagged:** a real browser render
  of the attestation tx (9dv6SwC2…) was attempted four ways
  (headless-shell and full Chromium, with and without the egress
  proxy, plus Playwright with authenticated proxy) against
  explorer.testnet.near.org and testnet.nearblocks.io. Headless
  Chromium in this VM cannot open a CONNECT tunnel through the
  authenticated egress proxy (`ERR_TUNNEL_CONNECTION_FAILED` /
  `ERR_NO_SUPPORTED_PROXIES`); nearblocks also fails via curl
  (the explorer page itself answers HTTP 200 via curl, so the tx
  page exists — it just cannot be rendered by a browser here).
  Per the brief's fallback: the beat shows the app's on-chain card
  enlarged, with the full attestation hash and the full explorer
  transaction URL on screen. If a future environment can render the
  explorer, swap that one beat (10.5 s) — nothing else changes.
- **Voiceover — SCRIPT READY, AUDIO BLOCKED, flagged:** Dexter's
  decision: generated calm Nigerian voice, no recording by him.
  Script written to `demo/VOICEOVER.md` (142 words, 7 scene lines,
  opens with the farmers line, names Fatima Sule out loud, closes
  with the tagline). edge-tts was installed and driven hard:
  en-NG-AbeoNeural (first choice) and en-NG-EzinneNeural, rate −10%,
  four connection configurations (default / egress CA bundle /
  proxy / proxy + combined CA bundle). The proxy + combined-CA route
  completes the TLS handshake, but the websocket audio stream then
  times out on read every time — this VM's egress blocks the
  speech.platform.bing.com stream. Per instructions, no robotic
  substitute was used: **v2 ships with captions**, and the VO can be
  generated and mixed in minutes wherever edge-tts can reach its
  service (script is per-scene so lines fit the existing cuts).

### Fix 4b — voiceover retry via the media pipeline (2026-11-10, later)

The edge-tts block above was routed around: the spoken-audio media
pipeline (`/opt/hatch/bin/tts`, a different network path from the VM
shell) synthesises fine from here, and its voice catalog contains
genuine Nigerian-accented voices. **v3 is the current cut:
`demo/farm-ajo-demo-v3.mp4`** — same video stream as v2 (copied,
not re-encoded) plus the voiceover.

- **Voice chosen:** "Pensive Hull"
  (`avocado_v2:vd2_r8_rep5k_3443_v068_28k_g5k`) — masculine,
  Nigerian accent, described in the catalog as "Very deep,
  Composed": the calmest Nigerian male on offer. Speed 125 on this
  slow-paced voice lands at ordinary conversational pace
  (~160 wpm) rather than rushed. (Runner-up tested: "Musing
  Chessboard", `avocado_v2:vg_ng_m26`, Nigerian, silky — timings
  near-identical; Hull won on calm/depth.)
- **Per-line files:** `demo/vo_final/hull/line1..7.mp3`, exact
  VOICEOVER.md wording. Durations (s): L1 3.79 · L2 8.30 · L3 7.82
  · L4 6.12 · L5 11.28 · L6 8.88 · L7 7.08 (total speech 53.3 s).
- **Fit:** lines placed at 0.4 / 5.3 / 15.9 / 24.1 / 30.6 / 42.3 /
  51.6 s against scene starts 0 / 5.1 / 15.7 / 23.8 / 32.9 / 39.0 /
  49.1 s. Six lines sit inside their scenes. Line 5 is the honest
  exception: its 30 words cannot fit the receipt shot's 6.5 s in
  any natural voice, so it starts 2.3 s early — over the purchase
  trigger, where its first sentence ("The supplier signs what it
  delivered") belongs — and runs into the explorer beat, which
  pushes lines 6–7 ~3 s behind their cards. No line overlaps
  another, none is clipped; the last word ends at 58.7 s of 59.13.
- **Verification:** ffprobe — h264 1920×1080 yuv420p 30 fps video
  (stream-copied from v2) + AAC 160 kbps audio, duration 59.13 s;
  limiter kept peaks at −1.0 dB (no clipping); speech confirmed
  present by volumedetect in the 0–5 / 30–42 / 42–51 / 51–59 s
  windows; only two >1.2 s silence gaps in the mixed track, both
  planned (before line 5, end-card tail). What could NOT be
  verified from here: an actual listen — pronunciation/accent
  quality rests on the catalog's Nigerian designation and the
  natural sentence-pause structure (0.4–0.7 s) in the renders.

### Fix 5 — end card

Tagline, "Track: Real-World Money", "Live on NEAR testnet:
circle2.farmajo-dev.testnet", the full explorer account URL
(explorer.testnet.near.org/accounts/circle2.farmajo-dev.testnet),
"Submission repo: github.com/Heisdave/farm-ajo", and the hackathon
line. Nothing was created or pushed on GitHub.

Tests at close of fix round: **pytest 11 passed** (8 + 3 new),
**cargo test 13 passed**. Local only; nothing published, posted or
submitted.
