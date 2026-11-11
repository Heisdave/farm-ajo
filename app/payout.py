"""Optional testnet payout for the Farm Ajo agent.

By default the agent sends nothing on-chain: it keeps the books and
prepares the two signature payloads (see agent.py). This module is the
single, opt-in exception.

When the environment enables it (FARMAJO_PAYOUT_ENABLED=1), the tick
that fires the bulk purchase ALSO sends one real NEAR testnet transfer
from the agent treasurer's account to the supplier's account, and the
caller records the transaction hash in the receipt next to the two
signatures. In the demo the transfer stands in for the purchase
payment itself: testnet NEAR has no value and the amount is symbolic.
In production the same trigger releases the co-operative's ordinary
bank transfer in naira instead (see README, "Where does the money
actually move?"). Farmers never touch crypto in either version.

The transfer is executed with near-cli-rs, the same tooling the
testnet deployment used, signing with the legacy keychain that lives
OUTSIDE this repo (~/.near-credentials). No key is read by this code,
and none is ever stored in the repo. Any failure is reported in the
returned dict, never raised: a failed payout must not break the
purchase flow.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

EXPLORER_TX = "https://explorer.testnet.near.org/transactions/{}"
_URL_RE = re.compile(r"transactions/([1-9A-HJ-NP-Za-km-z]{32,44})")
_TXID_RE = re.compile(r"Transaction ID:\s*([1-9A-HJ-NP-Za-km-z]{32,44})")
_TRUTHY = ("1", "true", "yes", "on")


@dataclass
class PayoutConfig:
    from_account: str
    amount_near: str
    cli_path: str
    network: str = "testnet"


def _find_cli() -> str | None:
    candidate = (Path.home() / "near-tools"
                 / "near-cli-rs-x86_64-unknown-linux-gnu" / "near")
    if candidate.exists():
        return str(candidate)
    return shutil.which("near")


def config_from_env() -> PayoutConfig | None:
    """Payout config from the environment, or None when not enabled."""
    if os.environ.get("FARMAJO_PAYOUT_ENABLED", "").strip().lower() \
            not in _TRUTHY:
        return None
    amount = os.environ.get("FARMAJO_PAYOUT_AMOUNT_NEAR", "0.3").strip()
    if amount.upper().endswith("NEAR"):
        amount = amount[:-4].strip()
    return PayoutConfig(
        from_account=os.environ.get("FARMAJO_PAYOUT_FROM",
                                    "farmajo-dev.testnet"),
        amount_near=amount,
        cli_path=os.environ.get("FARMAJO_NEAR_CLI") or _find_cli() or "near",
    )


def fire_payout(cfg: PayoutConfig, to_account: str) -> dict:
    """Send the payout transfer once. NEVER raises.

    Returns {"status": "sent", "tx_hash": ..., "explorer_url": ...,
    "from": ..., "to": ..., "amount_near": ...} on success, or
    {"status": "failed", "error": ..., ...} otherwise.
    """
    base = {"from": cfg.from_account, "to": to_account,
            "amount_near": cfg.amount_near}
    cmd = [cfg.cli_path, "tokens", cfg.from_account, "send-near",
           to_account, f"{cfg.amount_near} NEAR",
           "network-config", cfg.network,
           "sign-with-legacy-keychain", "send"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=90)
    except Exception as exc:  # missing binary, timeout, anything
        return {**base, "status": "failed",
                "error": f"{type(exc).__name__}: {exc}"}
    out = (proc.stdout or "") + (proc.stderr or "")
    match = _URL_RE.search(out) or _TXID_RE.search(out)
    if proc.returncode == 0 and match:
        tx_hash = match.group(1)
        return {**base, "status": "sent", "tx_hash": tx_hash,
                "explorer_url": EXPLORER_TX.format(tx_hash)}
    tail = [line for line in out.strip().splitlines() if line.strip()]
    return {**base, "status": "failed",
            "error": f"near-cli exited {proc.returncode}: "
                     + " | ".join(tail[-3:])}
