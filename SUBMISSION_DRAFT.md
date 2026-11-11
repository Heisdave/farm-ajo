# Farm Ajo — submission drafts (LOCAL ONLY — nothing here has been posted or submitted)

Prepared 2026-11-10 for the moved-up submission day: **Wednesday
2026-11-11**. Deadline remains Sat 2026-11-14 23:59 UTC; submitting
Wednesday leaves Thu–Sat as buffer for any request-changes.

Character counts below are X-weighted (every URL counts as 23
characters, as X counts it) unless stated raw. All drafts were scanned
against Dexter's banned list: no "leverage", "skeleton", "signal",
"Real talk —", "That's the difference between...", and no
Step 1/2/3 structure.

---

## 1. X demo post — MAIN DRAFT (4-post thread — story video on post 1, live-run proof on post 4)

Attach `demo/farm-ajo-demo-friend-cut.mp4` to post 1 (the friend's
cut with the end card added — chosen by Dexter on 2026-11-11 over the
in-house v5.1) and `demo/farm-ajo-live-run.mp4` to post 4. Dexter
posts from his phone (@heisdave01). Each post fits X's 280 on its own.

**Post 1** (237 / 280):

> Farmers save together so they can afford fertilizer before planting. I built Farm Ajo at the NEAR Hackathon — an Ajo circle with an agent treasurer, so the pot actually buys the fertilizer before prices spike. Ajo, but the pot has a job.

**Post 2** (272 / 280):

> 8 farmers save 5,000 toward 40,000 — 20 bags of NPK. The agent flags who still owes; the moment the pot fills, the purchase fires. The supplier signs the delivery, a named QC verifier signs the quality checks — both on NEAR testnet, checkable here: https://explorer.testnet.near.org/accounts/circle2.farmajo-dev.testnet

**Post 3** (275 / 280):

> Honest part: testnet demo, payments simulated — no real money moved, and the chain can't prove the fertilizer was good. Trust sits with the named verifier, whose name is on record. Built from my phone, mid test week.
> Repo: https://github.com/Heisdave/farm-ajo
> @NEARProtocol #NEARHackathon

**Post 4 — the proof clip** (attach `demo/farm-ajo-live-run.mp4`):

> Here it is running for real — one command, no edits: the circle at 32,500, the agent refusing to buy below target, the two missing shares landing, the purchase firing at 40,000, and the two-signature receipt at the end. Proof over polish.

Why a thread, not one post: the required pieces (opening line, pitch
line, both URLs, tags, honest downside) cannot fit one 280-character
post — the shortest honest compression still ran ~340 weighted.

## 2. X demo post — SHORTER ALTERNATE (single post, 276 / 280)

> Farmers save together so they can afford fertilizer before planting. Farm Ajo, built at NEAR Hackathon: agent-run Ajo, buys when the pot fills, delivery + QC signed by two people on NEAR testnet. Ajo, but the pot has a job.
> https://github.com/Heisdave/farm-ajo @NEARProtocol #NEARHackathon

Use this if Dexter prefers one post; the thread says more (shortfalls,
the agent firing, the honest downside in full).

## 3. Submission "idea" field — **1,685 characters** (allowed 20–2000)

> Farm Ajo — Ajo, but the pot has a job.
>
> PROBLEM: Fertilizer is cheapest before planting — exactly when a smallholder farmer has the least cash. Alone, each farmer buys late, at spiked retail prices. Eight farmers saving together, ahead of the season, can buy in bulk instead.
>
> PRODUCT: An agent-run Ajo (rotating savings circle) aimed at one target. Each farmer contributes a fixed share; the agent treasurer tracks every payment and shortfall in public, and the moment the pot reaches the target it fires the bulk purchase. Demo: 8 farmers x 5,000 = 40,000 units = 20 bags of NPK 15-15-15 at 2,000 per bag.
>
> HOW NEAR FITS: The circle lives in a NEAR testnet contract (circle2.farmajo-dev.testnet): terms, contributions, pot and state are public read-backs anyone can verify. The receipt takes two signatures from two designated accounts — the supplier signs the delivery, a named QC verifier signs the quality attestation — and the contract rejects either role doing the other's job. Both violations were attempted on testnet and rejected on-chain.
>
> FOUNDER FIT: The QC checks (bag count, sample weights against the nominal 50 kg, granule uniformity and caking, batch-label grade) were written from the founder's 6-month production and quality-control placement at a fertilizer blending plant in Kaduna State.
>
> HONEST SCOPE: Demo farmers, demo units. Payments and delivery are simulated on testnet; the contract tracks amounts and does not custody funds. In production, contributions move in naira through the co-operative's bank account, exactly as Ajo does today — NEAR is the public receipt book, not the payment rail, and the supplier is paid by bank transfer and needs no crypto.

## 4. Submission payload draft (DO NOT SEND — draft only)

```json
{
  "requestId": "TO-GENERATE-AT-SUBMISSION",
  "projectName": "Farm Ajo",
  "leadName": "Heisdave01(Dexter)",
  "email": "obirikwudavidstephen01@gmail.com",
  "size": "1",
  "tracks": ["realworld", "business", "social", "agents"],
  "nearAddress": "dexter01.near",
  "projectUrl": "https://github.com/Heisdave/farm-ajo",
  "demoUrl": "TO-FILL-AFTER-X-POST",
  "idea": "<the 1,685-character idea text in section 3 above>",
  "consent": false
}
```

Notes on the payload:

- `requestId` is generated ONCE at submission time and reused on any
  retry — never generate it in advance, never regenerate it.
- `tracks`: **Dexter confirms the final track list on Wednesday**
  before the payload is printed. The four above are the draft.
- `consent` stays `false` in this draft. It becomes `true` only after
  Dexter agrees to the organizers' notice, read to him verbatim:
  *"I agree that the organizers may use these details to review our
  submission and contact us about this hackathon."*
- There is deliberately **no `website` field** — a non-empty value
  there is a spam trap that rejects the submission.
- The submission is sent **once**. Mistakes afterwards go through
  the request-changes page, never a second submission.

## 5. Wednesday sequence (2026-11-11) — in order

1. **Repo public** — the local repo (already git-prepped) is pushed
  to `github.com/Heisdave/farm-ajo` and made public **only with
  Dexter's explicit confirmation**.
2. **Dexter posts the X demo** from his phone (@heisdave01): the
  thread in section 1 (or the alternate in section 2) — the friend's
  cut with the end card added (`demo/farm-ajo-demo-friend-cut.mp4`,
  chosen by Dexter on 2026-11-11) on post 1 and the live-run proof
  clip (`demo/farm-ajo-live-run.mp4`) on post 4. He sends back the
  post URL.
3. **Fill `demoUrl`** in the payload with that X post URL.
4. **Print the full payload** for Dexter, including the consent
  notice read verbatim.
5. **Dexter confirms** the exact payload (and the final track list).
6. **Submit ONCE** via the form or the API. A 201 means saved; report
  it to Dexter immediately.
