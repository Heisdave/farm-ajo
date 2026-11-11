"""Farm Ajo — NEAR Hackathon entry API.

Farmers save together so they can afford fertilizer before planting.

Endpoints
  GET  /health          liveness
  GET  /farmers         demo circle members + what each has paid / still owes
  GET  /circle          circle state: pot vs target, open / funded / verified
  POST /contributions   record one member's contribution (SQLite)
  POST /agent/tick      run the agent treasurer once: report shortfalls, and
                        when the pot reaches the target, fire the bulk
                        purchase and generate BOTH signature payloads of
                        the two-signature trust model, in the exact shapes
                        of the NEAR testnet contract's role-gated methods:
                        `record_delivery` (supplier account only) and
                        `attest_quality` (QC verifier account only)
  GET  /receipts        two-signature purchase / QC receipts generated so far

Demo data only: simulated contributions in demo units. No API keys and
no real payments. By default nothing is sent on-chain by this API. One
opt-in exception: with FARMAJO_PAYOUT_ENABLED set, the tick that fires
the purchase also sends a single testnet NEAR transfer (the purchase
payout, a symbolic stand-in with no real value) and records its hash in
the receipt. See app/payout.py.
"""

from __future__ import annotations

import html
import json
import sqlite3
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from . import agent as agent_core
from . import payout as payout_mod
from .demo_data import CIRCLE, FARMERS, ROLES

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "farm_ajo.db"
ONCHAIN_PATH = Path(__file__).resolve().parent.parent / "onchain.json"
FERT = CIRCLE["fertilizer"]

app = FastAPI(title="Farm Ajo — NEAR Hackathon entry", version="0.1.0")


def _db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS contributions (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               farmer_id TEXT NOT NULL,
               amount INTEGER NOT NULL,
               created_at INTEGER NOT NULL,
               seeded INTEGER NOT NULL DEFAULT 0
           )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS receipts (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               supplier TEXT NOT NULL,
               bags INTEGER NOT NULL,
               grade TEXT NOT NULL,
               qc_passed INTEGER NOT NULL,
               notes TEXT NOT NULL,
               total_cost INTEGER NOT NULL,
               created_at INTEGER NOT NULL,
               near_tx_hash TEXT,
               delivered_by TEXT,
               supplier_account TEXT,
               attested_by TEXT,
               verifier_account TEXT,
               checks TEXT
           )"""
    )
    receipt_cols = {row[1] for row in
                    conn.execute("PRAGMA table_info(receipts)")}
    for col in ("payout_tx", "payout_from", "payout_to",
                "payout_amount_near"):
        if col not in receipt_cols:
            conn.execute(f"ALTER TABLE receipts ADD COLUMN {col} TEXT")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS agent_log (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               created_at INTEGER NOT NULL,
               message TEXT NOT NULL
           )"""
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)"
    )
    _seed(conn)
    return conn


def _append_log(conn: sqlite3.Connection, message: str,
                ts: int | None = None) -> None:
    conn.execute(
        "INSERT INTO agent_log (created_at, message) VALUES (?, ?)",
        (ts if ts is not None else int(time.time()), message),
    )


def _shortfall_line(states: list[agent_core.FarmerState]) -> str | None:
    owing = [f for f in states if f.shortfall > 0]
    if not owing:
        return None
    return "Shortfall: " + " · ".join(
        f"{f.name} owes {f.shortfall:,}" for f in owing
    )


def _agent_log(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT created_at, message FROM agent_log ORDER BY id"
    ).fetchall()
    return [
        {"ts": ts,
         "time": time.strftime("%H:%M:%S", time.localtime(ts)),
         "message": msg}
        for ts, msg in rows
    ]


def _seed(conn: sqlite3.Connection) -> None:
    """Insert the demo members' opening contributions exactly once."""
    row = conn.execute("SELECT value FROM meta WHERE key = 'seeded'").fetchone()
    if row is not None:
        return
    now = int(time.time())
    with conn:
        for f in FARMERS:
            if f["paid"] > 0:
                conn.execute(
                    "INSERT INTO contributions (farmer_id, amount, created_at, seeded)"
                    " VALUES (?, ?, ?, 1)",
                    (f["farmer_id"], f["paid"], now),
                )
        conn.execute("INSERT INTO meta (key, value) VALUES ('seeded', '1')")
        seeded_states = [
            agent_core.FarmerState(
                farmer_id=f["farmer_id"], name=f["name"], crop=f["crop"],
                expected=CIRCLE["contribution_amount"], paid=f["paid"],
            )
            for f in FARMERS
        ]
        pot = sum(f.paid for f in seeded_states)
        _append_log(
            conn,
            f"Agent treasurer on duty — circle seeded: pot {pot:,} of "
            f"{CIRCLE['target']:,} ({len(seeded_states)} members, share "
            f"{CIRCLE['contribution_amount']:,} each)",
            ts=now,
        )
        line = _shortfall_line(seeded_states)
        if line:
            _append_log(conn, line, ts=now)


def _farmer_states(conn: sqlite3.Connection) -> list[agent_core.FarmerState]:
    paid = dict(
        conn.execute(
            "SELECT farmer_id, SUM(amount) FROM contributions GROUP BY farmer_id"
        ).fetchall()
    )
    return [
        agent_core.FarmerState(
            farmer_id=f["farmer_id"],
            name=f["name"],
            crop=f["crop"],
            expected=CIRCLE["contribution_amount"],
            paid=int(paid.get(f["farmer_id"], 0)),
        )
        for f in FARMERS
    ]


def _receipts(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT id, supplier, bags, grade, qc_passed, notes, total_cost,"
        " created_at, near_tx_hash, delivered_by, supplier_account,"
        " attested_by, verifier_account, checks, payout_tx, payout_from,"
        " payout_to, payout_amount_near FROM receipts ORDER BY id"
    ).fetchall()
    keys = ["id", "supplier", "bags", "grade", "qc_passed", "notes",
            "total_cost", "created_at", "near_tx_hash", "delivered_by",
            "supplier_account", "attested_by", "verifier_account", "checks",
            "payout_tx", "payout_from", "payout_to", "payout_amount_near"]
    out = []
    for row in rows:
        d = dict(zip(keys, row))
        d["qc_passed"] = bool(d["qc_passed"])
        try:
            d["checks"] = json.loads(d["checks"]) if d["checks"] else []
        except ValueError:
            d["checks"] = []
        out.append(d)
    return out


def _contract_id() -> str:
    """Deployed testnet contract id from onchain.json, when present."""
    oc = _onchain()
    if oc and oc.get("contract_account_id"):
        return oc["contract_account_id"]
    return "<deployed-ajo-circle>.testnet  (after deploy - see README)"


def _circle_view(conn: sqlite3.Connection,
                 farmers: list[agent_core.FarmerState] | None = None) -> dict:
    # Header numbers (pot, paid-in-full count) and the members table are
    # ALWAYS derived from this one farmer-state snapshot, so they can
    # never disagree with each other. Callers that also render the table
    # pass their snapshot in instead of re-reading the DB.
    if farmers is None:
        farmers = _farmer_states(conn)
    pot = sum(f.paid for f in farmers)
    receipts = _receipts(conn)
    if receipts:
        state = "verified"
    elif pot >= CIRCLE["target"]:
        state = "funded"
    else:
        state = "open"
    return {
        "name": CIRCLE["name"],
        "data_mode": "demo",
        "amount_unit": "demo units (simulated testnet credits)",
        "target": CIRCLE["target"],
        "contribution_amount": CIRCLE["contribution_amount"],
        "pot": pot,
        "remaining_to_target": max(0, CIRCLE["target"] - pot),
        "state": state,
        "member_count": len(farmers),
        "members_fully_paid": sum(1 for f in farmers if f.shortfall == 0),
        "total_shortfall": sum(f.shortfall for f in farmers),
        "fertilizer": FERT,
        "season_note": CIRCLE["season_note"],
    }


class ContributionRequest(BaseModel):
    farmer_id: str = Field(..., description="Demo farmer id, e.g. farmer-emeka-nwosu")
    amount: int = Field(..., description="Contribution in demo units (positive)")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "farm-ajo", "data_mode": "demo"}


@app.get("/farmers")
def farmers() -> dict:
    conn = _db()
    states = _farmer_states(conn)
    conn.close()
    return {
        "data_mode": "demo",
        "note": "Fictional demo farmers; amounts are simulated testnet/demo units.",
        "farmers": [
            {**f.to_dict(),
             "crop": next(x["crop"] for x in FARMERS if x["farmer_id"] == f.farmer_id),
             "location": next(x["location"] for x in FARMERS if x["farmer_id"] == f.farmer_id)}
            for f in states
        ],
    }


@app.get("/circle")
def circle() -> dict:
    conn = _db()
    view = _circle_view(conn)
    conn.close()
    return view


@app.post("/contributions")
def record_contribution(req: ContributionRequest) -> dict:
    conn = _db()
    try:
        states = {f.farmer_id: f for f in _farmer_states(conn)}
        farmer = states.get(req.farmer_id)
        if farmer is None:
            raise HTTPException(status_code=404, detail=f"unknown farmer_id: {req.farmer_id}")
        closed = len(_receipts(conn)) > 0
        try:
            agent_core.validate_contribution(farmer, req.amount, closed)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        now = int(time.time())
        with conn:
            conn.execute(
                "INSERT INTO contributions (farmer_id, amount, created_at, seeded)"
                " VALUES (?, ?, ?, 0)",
                (req.farmer_id, req.amount, now),
            )
            new_pot = sum(f.paid for f in _farmer_states(conn))
            _append_log(
                conn,
                f"Contribution received: {farmer.name} "
                f"+{req.amount:,} (pot {new_pot:,})",
                ts=now,
            )
        return {
            "recorded": True,
            "farmer_id": req.farmer_id,
            "amount": req.amount,
            "circle": _circle_view(conn),
            "near_contract_call": {
                "contract": _contract_id(),
                "method": "contribute",
                "args": {"member": req.farmer_id, "amount": req.amount},
                "note": "Payload prepared locally. The same call was run "
                        "on-chain in the testnet deployment — see "
                        "DEPLOY_NOTES.md. Nothing is sent by this API.",
            },
        }
    finally:
        conn.close()


@app.post("/agent/tick")
def agent_tick() -> dict:
    conn = _db()
    try:
        states = _farmer_states(conn)
        existing = _receipts(conn)
        result = agent_core.agent_tick(
            states,
            target=CIRCLE["target"],
            price_per_bag=FERT["price_per_bag"],
            grade=FERT["grade"],
            supplier_name=ROLES["supplier"]["name"],
            supplier_account=ROLES["supplier"]["account"],
            verifier_name=ROLES["verifier"]["name"],
            verifier_account=ROLES["verifier"]["account"],
            already_verified=len(existing) > 0,
        )
        body = result.to_dict()
        body["circle_state"] = _circle_view(conn)["state"]
        body["verified_now"] = False
        body["payout"] = None
        if (result.delivery is not None and result.attestation is not None
                and result.purchase is not None):
            now = int(time.time())
            with conn:
                cur = conn.execute(
                    "INSERT INTO receipts (supplier, bags, grade, qc_passed,"
                    " notes, total_cost, created_at, delivered_by,"
                    " supplier_account, attested_by, verifier_account,"
                    " checks) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        result.delivery.supplier_name,
                        result.delivery.bags,
                        result.delivery.grade,
                        int(result.attestation.qc_passed),
                        result.attestation.notes,
                        result.purchase.total_cost,
                        now,
                        result.delivery.supplier_name,
                        result.delivery.supplier_account,
                        result.attestation.verifier_name,
                        result.attestation.verifier_account,
                        json.dumps(result.attestation.checks),
                    ),
                )
                receipt_id = cur.lastrowid
            payout_cfg = payout_mod.config_from_env()
            if payout_cfg is not None:
                # Opt-in: the purchase tick also fires the real testnet
                # payout transfer. This branch runs exactly once per
                # circle (later ticks see the receipt and take the
                # already-verified path), so the payout cannot double.
                payout_result = payout_mod.fire_payout(
                    payout_cfg, result.delivery.supplier_account)
                body["payout"] = payout_result
                if payout_result.get("status") == "sent":
                    with conn:
                        conn.execute(
                            "UPDATE receipts SET payout_tx = ?,"
                            " payout_from = ?, payout_to = ?,"
                            " payout_amount_near = ? WHERE id = ?",
                            (payout_result["tx_hash"],
                             payout_result["from"],
                             payout_result["to"],
                             payout_result["amount_near"],
                             receipt_id),
                        )
            body["verified_now"] = result.verified
            body["circle_state"] = "verified"
            body["receipt_id"] = receipt_id
            with conn:
                _append_log(
                    conn,
                    f"Pot reached {result.pot:,} — executing bulk "
                    f"purchase: {result.purchase.bags} bags of "
                    f"{result.purchase.grade} for "
                    f"{result.purchase.total_cost:,}",
                    ts=now,
                )
                if body["payout"] is not None:
                    if body["payout"].get("status") == "sent":
                        _append_log(
                            conn,
                            f"Purchase payout fired on NEAR testnet: "
                            f"{body['payout']['amount_near']} NEAR to "
                            f"{body['payout']['to']} "
                            f"(tx {body['payout']['tx_hash']})",
                            ts=now,
                        )
                    else:
                        _append_log(
                            conn,
                            "Purchase payout failed on NEAR testnet: "
                            f"{body['payout'].get('error', 'unknown error')}",
                            ts=now,
                        )
                _append_log(
                    conn,
                    f"Delivery signed by supplier: "
                    f"{result.delivery.supplier_name} "
                    f"({result.delivery.supplier_account})",
                    ts=now,
                )
                _append_log(
                    conn,
                    f"Quality attested by {result.attestation.verifier_name} "
                    f"({result.attestation.verifier_account}) — "
                    f"QC {'passed' if result.attestation.qc_passed else 'FAILED'}",
                    ts=now,
                )
                if result.verified:
                    _append_log(
                        conn,
                        "Circle verified — both signatures recorded; "
                        "receipt closed",
                        ts=now,
                    )
            body["near_contract_calls"] = [
                {
                    "contract": _contract_id(),
                    "method": "record_delivery",
                    "args": result.delivery.contract_args(),
                    "sign_as": result.delivery.supplier_account,
                    "note": "Signature 1 of 2. The contract rejects any "
                            "caller other than the supplier account.",
                },
                {
                    "contract": _contract_id(),
                    "method": "attest_quality",
                    "args": result.attestation.contract_args(),
                    "sign_as": result.attestation.verifier_account,
                    "note": "Signature 2 of 2. The contract rejects any "
                            "caller other than the QC verifier account. "
                            "Both calls were run on-chain during the "
                            "testnet deployment; see DEPLOY_NOTES.md. "
                            "This API does not send them.",
                },
            ]
        elif existing:
            body["receipt_id"] = existing[-1]["id"]
            with conn:
                _append_log(
                    conn,
                    "Agent tick — circle already verified; nothing to do",
                )
        else:
            with conn:
                _append_log(
                    conn,
                    f"Agent tick — pot {result.pot:,} of "
                    f"{result.target:,}; holding, no purchase below target",
                )
                line = _shortfall_line(states)
                if line:
                    _append_log(conn, line)
        body["agent_log"] = _agent_log(conn)
        return body
    finally:
        conn.close()


@app.get("/agent/log")
def agent_log() -> dict:
    conn = _db()
    try:
        return {"agent": "Farm Ajo agent treasurer", "log": _agent_log(conn)}
    finally:
        conn.close()


@app.get("/receipts")
def receipts() -> dict:
    conn = _db()
    rows = _receipts(conn)
    conn.close()
    return {"receipts": rows}


def _onchain() -> dict | None:
    """Public on-chain record of the deployed demo (ids + tx hashes only)."""
    try:
        return json.loads(ONCHAIN_PATH.read_text())
    except (OSError, ValueError):
        return None


@app.get("/demo", response_class=HTMLResponse)
def demo_page() -> str:
    """One-page, at-a-glance view of the circle for demos and judges.

    Server-rendered from the same local seeded data as the JSON API; when
    `onchain.json` exists (after the testnet deploy) it also shows the real
    contract account and transaction links.
    """
    conn = _db()
    states = _farmer_states(conn)
    view = _circle_view(conn, states)   # one snapshot for header + table
    receipts = _receipts(conn)
    logs = _agent_log(conn)
    conn.close()
    onchain = _onchain()
    esc = html.escape

    pct = min(100, round(100 * view["pot"] / view["target"])) if view["target"] else 0
    state_label = {"open": "Saving — circle open",
                   "funded": "Funded — awaiting delivery + QC attestation",
                   "verified": "Purchased + verified — two signatures on NEAR testnet"}[view["state"]]

    farmer_rows = ""
    for f in states:
        d = f.to_dict()
        loc = next(x["location"] for x in FARMERS if x["farmer_id"] == f.farmer_id)
        chip = ('<span class="chip paid">Paid in full</span>' if d["fully_paid"]
                else f'<span class="chip owes">Owes {d["shortfall"]:,}</span>')
        farmer_rows += (
            f"<tr><td>{esc(d['name'])}</td><td>{esc(d['crop'])}</td>"
            f"<td>{esc(loc)}</td><td>{d['paid']:,}</td><td>{chip}</td></tr>"
        )

    log_rows = "".join(
        f'<div class="logline"><span class="logtime">{esc(l["time"])}</span>'
        f'{esc(l["message"])}</div>'
        for l in logs
    )
    log_html = f"""
        <section class="card">
          <h2>Agent treasurer — activity log</h2>
          <div class="log">{log_rows}</div>
          <p class="notes">Written by the agent itself as it works: every
             tick, contribution, shortfall flag and signature lands here.</p>
        </section>"""

    receipt_html = ""
    if receipts:
        r = receipts[-1]
        supplier_display = (r['delivered_by'] or r['supplier']).replace(
            " (demo supplier)", "")
        verifier_display = (r['attested_by'] or "").split(",")[0].replace(
            " (demo)", "")
        payout_html = ""
        if r.get("payout_tx"):
            payout_html = f"""
          <p>Purchase payout: <strong>{esc(r['payout_amount_near'] or '')}
             NEAR</strong> on NEAR testnet, from
             {esc(r['payout_from'] or '')} to
             {esc(r['payout_to'] or '')}.<br>
             Tx: <a href="https://explorer.testnet.near.org/transactions/{esc(r['payout_tx'])}">{esc(r['payout_tx'])}</a></p>
          <p class="notes">Testnet NEAR has no value. In this demo the
             transfer is the moment the pot is spent, standing in for
             the purchase payment. In production the same trigger
             releases the co-operative's bank transfer in naira, and
             the chain keeps the receipt.</p>"""
        receipt_html = f"""
        <section class="card">
          <h2>Purchase + QC receipt — two signatures</h2>
          <p><strong>{r['bags']} bags of {esc(r['grade'])}</strong> —
             total {r['total_cost']:,} demo units.</p>
          <p>Delivered by: <strong>{esc(supplier_display)}</strong>
             ({esc(r['supplier_account'] or '')})</p>
          <p>Quality attested by: <strong>{esc(verifier_display)}</strong>
             ({esc(r['verifier_account'] or '')})</p>
          <p>QC result: <strong>{'PASSED' if r['qc_passed'] else 'FAILED'}</strong> —
             bag count · sample weights within +/-2% of 50&nbsp;kg · granule
             uniformity / no excessive caking · batch-label grade match.</p>
          {payout_html}
          <p class="notes">The chain proves this record existed and who
             signed it. It cannot prove the fertilizer was good — that
             trust sits with the named verifier, whose name and history
             are on the record.</p>
          <p class="notes">{esc(r['notes'])}</p>
        </section>"""

    chain_html = ""
    if onchain:
        sig_lines = ""
        if onchain.get("delivery_tx"):
            sig_lines += f"""Signature 1 — delivery recorded by the supplier:
             <a href="{esc(onchain['delivery_tx_url'])}">{esc(onchain['delivery_tx'])}</a><br>
             Signature 2 — quality attested by the verifier:
             <a href="{esc(onchain['attestation_tx_url'])}">{esc(onchain['attestation_tx'])}</a>"""
        elif onchain.get("purchase_tx"):
            sig_lines = f"""Purchase + QC receipt recorded:
             <a href="{esc(onchain['purchase_tx_url'])}">{esc(onchain['purchase_tx'])}</a>"""
        chain_html = f"""
        <section class="card">
          <h2>On NEAR testnet</h2>
          <p>Contract: <a href="{esc(onchain['explorer_account_url'])}">
             {esc(onchain['contract_account_id'])}</a> —
             live circle state on-chain: pot {onchain['final_onchain_pot']:,},
             state <strong>{esc(onchain['final_onchain_state'])}</strong>.</p>
          <p>Deploy + init:
             <a href="{esc(onchain['deploy_tx_url'])}">{esc(onchain['deploy_tx'])}</a><br>
             {sig_lines}</p>
        </section>"""

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Farm Ajo — demo</title>
<style>
  body {{ font-family: system-ui, sans-serif; margin: 0; background: #23211a;
         color: #f0ead8; }}
  main {{ max-width: 860px; margin: 0 auto; padding: 24px 16px 48px; }}
  h1 {{ font-size: 28px; margin-bottom: 4px; }}
  .tagline {{ font-size: 18px; color: #cfd8a8; margin-top: 0; }}
  .card {{ background: #2e2b21; border: 1px solid #4a4636; border-radius: 12px;
          padding: 16px 20px; margin: 16px 0; }}
  .bar {{ background: #171510; border-radius: 999px; height: 22px; overflow: hidden; }}
  .bar > div {{ background: #8ba888; height: 100%; }}
  table {{ width: 100%; border-collapse: collapse; }}
  td, th {{ padding: 7px 8px; border-bottom: 1px solid #4a4636; text-align: left; }}
  .chip {{ padding: 2px 9px; border-radius: 999px; font-size: 13px; }}
  .chip.paid {{ background: #37503a; color: #bfe3c2; }}
  .chip.owes {{ background: #54432a; color: #f2d492; }}
  .log {{ font-family: ui-monospace, Menlo, Consolas, monospace;
         font-size: 14.5px; line-height: 1.55; }}
  .logline {{ padding: 5px 0; border-bottom: 1px dashed #4a4636; }}
  .logtime {{ color: #8ba888; margin-right: 10px; }}
  a {{ color: #b9d18b; word-break: break-all; }}
  .notes, .foot {{ color: #bdb69c; font-size: 14px; }}
</style></head><body><main>
  <h1>Farm Ajo</h1>
  <p class="tagline">Farmers save together so they can afford fertilizer
     before planting.</p>

  <section class="card">
    <h2>{esc(view['name'])}</h2>
    <p>Status: <strong>{esc(state_label)}</strong> ·
       {view['members_fully_paid']} of {view['member_count']} members paid in full</p>
    <div class="bar"><div style="width:{pct}%"></div></div>
    <p>Pot: <strong>{view['pot']:,}</strong> of {view['target']:,} demo units
       ({pct}%) · each member's share: {view['contribution_amount']:,}</p>
    <p class="notes">{esc(view['season_note'])} Goal: 20 bags of
       {esc(FERT['grade'])} (50&nbsp;kg each) from {esc(FERT['supplier'])}.</p>
  </section>

  <section class="card">
    <h2>Members</h2>
    <table><tr><th>Farmer</th><th>Crop</th><th>Location</th><th>Paid</th>
    <th>State</th></tr>{farmer_rows}</table>
  </section>
  {log_html}
  {receipt_html}
  {chain_html}
  <p class="foot">Demo on NEAR testnet with simulated contributions and a
     simulated delivery — no real money or goods moved. An Ajo is a rotating
     group savings circle; Farm Ajo's agent treasurer keeps its books.</p>
</main></body></html>"""
