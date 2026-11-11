# DEPLOY_NOTES — Farm Ajo on NEAR testnet (phase 2, 2026-11-10)

Everything below was executed and read back on-chain on 2026-11-10.
**Testnet only** — faucet funds, no real money, no mainnet. Dexter's
payout account (`dexter01.near`, mainnet) was not touched or used.

## Accounts

| Role | Account | Notes |
|---|---|---|
| Deploy infrastructure (Muse-side tooling) | `farmajo-dev.testnet` | Created via the NEAR faucet (`near account create-account sponsor-by-faucet-service`), funded with 10 testnet NEAR. Creation tx: `4YAYJcfxVN84uUy15jH4fg2GvEuEYcgQZCNbTAfaKiF2` |
| Contract account | `circle.farmajo-dev.testnet` | Subaccount created with 2 testnet NEAR, then topped up with 3 more (transfer tx `6psZmJ2V6UPWg1HSk2zsBX29JWv5oWyX6MtN1M51NAzX`) to cover contract storage staking. The create-account tx hash was not captured in the CLI output tail; the account and every tx below are verifiable on the explorer. |

**Keys:** full-access keys for both accounts live in the legacy keychain
at `~/.near-credentials/testnet/` — **outside the project repo tree**.
The repo's `hidden/` directory is in `.gitignore` (verified), as are
`*.testnet`, `neardev/` and `*.json.key`. No key material is in any file
that could be pushed to a public repo.
**Tool:** near-cli-rs 0.31.1, binary at `~/near-tools/` (outside the repo).

## Deployment

- Contract: `contracts/ajo-circle/res/farm_ajo_circle.wasm` (200 KB).
- **Successful deploy + init tx:**
  [`5GK8AnDGZEBB9UQSCgDLUgncE5LJW7fY7iohLNUXuq1W`](https://explorer.testnet.near.org/transactions/5GK8AnDGZEBB9UQSCgDLUgncE5LJW7fY7iohLNUXuq1W)
- Init args: name "Planting Season Circle - Kaduna (demo)",
  target 40000, contribution_amount 5000, the 8 demo member ids.
- Read-back right after deploy: `get_circle` → pot 0, state `open`,
  member_count 8. ✔

Two failed attempts came first — recorded because they taught things:

1. Tx `G5Hg2aW3gtbJDD5pnfdwegnfaiXoXskMWx5EZ74wgFW2` — init panicked:
   "Failed to deserialize input from JSON: invalid number". The
   contract's fields are **plain `u128`, which take JSON *numbers***,
   not the string encoding that the `U128` wrapper type uses. The whole
   transaction rolled back (no code was stored). Fix: pass
   `target: 40000` / `contribution_amount: 5000` as numbers. (Phase 1's
   README said strings — corrected in phase 2.)
2. Tx `FCcYfVGArWYvwzFNqMky4ARKdpSSfHYLNKwDbsL8rZAV` — "remaining
   balance will not be enough to cover storage": ~2 NEAR does not cover
   storage staking for a 200 KB contract plus state. Fix: top the
   contract account up to ~5 NEAR before deploying.

## On-chain end-to-end run (the full demo loop, signed by farmajo-dev.testnet)

Contributions, in order (each is a `contribute` call):

| # | Member | Amount | Tx |
|---|---|---|---|
| 1 | farmer-amina-bello | 5000 | `C4PWLfSioXFSJPK9JNWjgv9jZEQ6HDv6U6XtRF3rW56e` |
| 2 | farmer-yusuf-abdullahi | 5000 | `7rGLBHZgQYhY2UeDbRcwZgyNMCzK7zF9HvveD5La1ws2` |
| 3 | farmer-ibrahim-sani | 5000 | `63zRKtzqHZAkkTnZGDM7JKFAXmt7zVsruRYYLiejLYod` |
| 4 | farmer-ngozi-eze | 5000 | `Ajx9d4Avwjwfo6HnxX5L9zgrKSHjtUa52PoZ9a2xtSz8` |
| 5 | farmer-musa-garba | 5000 | `7ckx2Ho9JYSP5ZtJSbnWoguedwfbSLKU5dkZuVdc6YP` |
| 6 | farmer-funke-adebayo | 5000 | `5Rcf6du98ba4iCpFebVX4QzQLDbR9SRKpdz2sVG2oAFD` |
| 7 | farmer-halima-usman | 2500 | `2GiiHAmeywv6oE5sEB5dGoy48X1Un63gm8BoB3M4wBaw` |
| 8 | farmer-emeka-nwosu | 5000 | `EDhxUSQBKzL7AS5fQX7tk2TmfkLncCPLy8tL6yZNkDZa` |
| 9 | farmer-halima-usman | 2500 | `2L9B2ETaqazaX9uVzBbHrXRfEGpbRVXHjKvjTbd8g5FV` |

Explorer link pattern:
`https://explorer.testnet.near.org/transactions/<tx>`

After contribution 9: `get_circle` → **pot 40000, state `funded`**. ✔

Purchase + QC receipt (`record_purchase` — 20 bags of NPK 15-15-15 from
Kaduna Agro Inputs Ltd (demo supplier), `qc_passed: true`, notes
containing the 4 named QC checks: bag count matches the purchase order;
sample bags within ±2% of the nominal 50 kg; granules uniform, no
excessive caking; batch-label grade matches the ordered grade):

- Tx: [`3ot66BfcPX8krpYschuieomPRQMpLPjwgGjz4yGPUND5`](https://explorer.testnet.near.org/transactions/3ot66BfcPX8krpYschuieomPRQMpLPjwgGjz4yGPUND5)
- Read-back via `get_purchase` returned the full receipt
  (recorded_by `farmajo-dev.testnet`, block timestamp
  1794302751644126063 ns) and `get_circle` → **pot 40000, state
  `purchased`**. ✔

Contract account on the explorer:
https://explorer.testnet.near.org/accounts/circle.farmajo-dev.testnet

The same ids/hashes are in `onchain.json` (public data only) at the
project root; the demo status page (`GET /demo`) reads them from there.

---

# DEPLOY_NOTES — v2 two-signature trust model (2026-11-10)

Dexter's challenge, taken seriously: *"anyone can write 'quality
verified' — who attests it, and why should anyone trust them?"* The
single-signature `record_purchase` of v1 is replaced by a
**two-signature trust model**, deployed fresh to a new contract
account (v1 at `circle.farmajo-dev.testnet` stays on-chain untouched
as the phase-2 record; its purchase tx remains
`3ot66BfcPX8krpYschuieomPRQMpLPjwgGjz4yGPUND5`).

## The model

- At circle creation the contract takes two designated role accounts:
  a **supplier** account and a **QC verifier** account. `new` rejects
  a circle where both roles are the same account.
- `record_delivery(...)` — callable **only** by the supplier account
  (`predecessor_account_id` check), only once funded. Records bags,
  grade, total cost. State `funded -> delivered`.
- `attest_quality(...)` — callable **only** by the verifier account,
  only after a delivery exists. Records the 4 named QC checks and
  pass/fail. State `delivered -> verified` **only if QC passed**; a
  failed attestation is stored but the circle stays `delivered`.
- Neither role can perform the other's action — proven in unit tests
  (cargo test: 13 passed) and proven again on-chain (see the two
  deliberate failed attempts below).

## Accounts (all Muse-side testnet infrastructure, keys in
`~/.near-credentials/testnet/`, outside the repo)

| Role | Account | Created with | Creation tx |
|---|---|---|---|
| Contract (v2) | `circle2.farmajo-dev.testnet` | 4 testnet NEAR from `farmajo-dev.testnet` | not captured in CLI output tail — account + all txs below are on the explorer |
| Supplier (signature 1) | `supplier.farmajo-dev.testnet` | 0.3 testnet NEAR | `SJZPPtVTZ4TBcmT3i9frRhkhA8Z6aV2KG8Ann56RDZp` |
| QC verifier (signature 2) | `verifier.farmajo-dev.testnet` | 0.3 testnet NEAR | `AFiw6sL9ut6oLr6qPQh4vwRcELSuHSTNmQrx6ezHMuNT` |

In the demo scenario the verifier is the named person **Fatima Sule —
QC Verifier, Kaduna Farmers' Co-operative (demo)**; the supplier is
**Kaduna Agro Inputs Ltd (demo supplier)**.

## Deployment + run (all executed and read back, 2026-11-10)

- **Deploy + init tx:**
  [`7YZLiKhmfXk5EiuwjuUeiukXwLhL3qLKbuuvDYJKrgR8`](https://explorer.testnet.near.org/transactions/7YZLiKhmfXk5EiuwjuUeiukXwLhL3qLKbuuvDYJKrgR8)
  (init args include `supplier_account` and `verifier_account`; the v2
  wasm is 219 KB). Read-back: pot 0, `open`, 8 members, both roles set.
- **9 contributions** (same seeded order as v1; signed by
  `farmajo-dev.testnet` as the members' agent):

  | # | Member | Amount | Tx |
  |---|---|---|---|
  | 1 | farmer-amina-bello | 5000 | `8HLs6ewdsWouUEMv8839hwSsFiuSg34L5WXHdc86H5SZ` |
  | 2 | farmer-yusuf-abdullahi | 5000 | `6wQCYq7igsV2SfxiqYMQw2dUtEFvVwKVYtY3HdV9DCgz` |
  | 3 | farmer-ibrahim-sani | 5000 | `CQRkRW9a4zdG2Y4KLU6PtJyfLPNAufjWQCGMHSAQpT6A` |
  | 4 | farmer-ngozi-eze | 5000 | `7vTqDwqJAMVpNHBWNbaL6MsaV6oSBSBFTcFM6rquyfc8` |
  | 5 | farmer-musa-garba | 5000 | `8hejxiXpJK8ihbpDnLNLUf4uzqX2NR61hXkvyEU1Ntsx` |
  | 6 | farmer-funke-adebayo | 5000 | `DhmtinDs6vjA4PRshmbd2rgBnj8LpqJUCzKeuLRZoKzm` |
  | 7 | farmer-halima-usman | 2500 | `DmoCa3GNEPNAzK5Rne8GKp51vBi49f7tmxt8Qn8tQQUR` |
  | 8 | farmer-emeka-nwosu | 5000 | `SVVTudoAge5GM5Yjkf8YDhLgs9d1SavDncPiFXsnWJT` |
  | 9 | farmer-halima-usman | 2500 | `9TQKVMso3DtbCtSC3Dm4Esw8UshhkjcyWGDVUPauLF1S` |

  After #9: `get_circle` -> **pot 40000, state `funded`**. ✔

- **Two deliberate role violations — both rejected on-chain** (the
  transactions exist and failed with the contract's guard messages):
  - Supplier account tried to attest quality:
    tx `6DZRifxszL9c3Ji3BgBeprnKFN6gkdScw32zGRzYxLQW` — failed:
    *"only the designated QC verifier account can attest quality"*.
  - Verifier account tried to record the delivery:
    tx `EUEgdTZ9VwxfLsBto8s5JnFH9xYKc5wh6FA5AAs4fEas` — failed:
    *"only the designated supplier account can record the delivery"*.

- **Signature 1 — delivery**, signed by `supplier.farmajo-dev.testnet`:
  tx [`BvkdEt8R3Df7QkJjKbUACoAgkUBDLgEfsXZhZ9TmUFtG`](https://explorer.testnet.near.org/transactions/BvkdEt8R3Df7QkJjKbUACoAgkUBDLgEfsXZhZ9TmUFtG)
  (20 bags, NPK 15-15-15, total 40,000). State -> `delivered`.
- **Signature 2 — QC attestation**, signed by
  `verifier.farmajo-dev.testnet`:
  tx [`9dv6SwC2mBJrWezFLbrTwUHNmbkuepj7ozbwuTB9p57`](https://explorer.testnet.near.org/transactions/9dv6SwC2mBJrWezFLbrTwUHNmbkuepj7ozbwuTB9p57)
  (the 4 named QC checks, `qc_passed: true`).
- **Final read-back:** `get_circle` -> **pot 40000, state
  `verified`**, delivery `delivered_by supplier.farmajo-dev.testnet`,
  attestation `attested_by verifier.farmajo-dev.testnet`. ✔

Contract account on the explorer:
https://explorer.testnet.near.org/accounts/circle2.farmajo-dev.testnet

The same data is in `onchain.json` (v2; public ids/hashes only), and
the demo page reads it from there.

## Addendum, 2026-11-11: the agent payout (post-submission buffer)

After the submission was filed, one bounded addition was made in the
buffer window, answering the most common external criticism of the
demo (that no value ever moves). The contract, the submitted demo
flow and the default `./run.sh` behaviour are unchanged.

- `app/payout.py` (new): opt-in via `FARMAJO_PAYOUT_ENABLED=1`. When
  the purchase tick fires, the agent also sends one NEAR testnet
  transfer from `farmajo-dev.testnet` to
  `supplier.farmajo-dev.testnet` using near-cli-rs
  (`tokens ... send-near ... network-config testnet
  sign-with-legacy-keychain send`), and the API stores the tx hash in
  the receipt (`payout_*` columns) and shows it on the demo page.
  Exactly-once is structural: the purchase branch of the tick runs
  only when no receipt exists yet. Failures are reported, never
  raised, and never block the purchase.
- Tooling smoke test first (0.01 NEAR, same accounts):
  tx `HvTRt4eebgiKswsUvHWmxWW6iDA4Lxxyv8TAqLGt85qA`.
- Recorded agent run (fresh demo copy, payout enabled, the standard
  capture flow): the funding tick fired the payout.
  - **Payout tx:**
    [`HdK5yfGSXtpUgTBtmw9h5TjuB51TqeqM3pFSf5rbZann`](https://explorer.testnet.near.org/transactions/HdK5yfGSXtpUgTBtmw9h5TjuB51TqeqM3pFSf5rbZann)
    (0.3 NEAR, `farmajo-dev.testnet` -> `supplier.farmajo-dev.testnet`)
  - Verified by RPC afterwards: tx status `SuccessValue`, single
    Transfer action of 300000000000000000000000 yoctoNEAR; supplier
    balance 0.30966 -> 0.60966 NEAR (exactly +0.3).
- Tests: 16 passing (11 pre-existing + 5 new payout tests with the
  transfer faked: config gating, exactly-once, below-target silence,
  failure safety, demo page line).
- The amount is a stand-in: testnet NEAR has no value. In production
  the same trigger releases the co-operative's naira bank transfer;
  see README, "Does any money move in the demo?".
