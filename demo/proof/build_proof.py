#!/usr/bin/env python3
"""Build the Farm Ajo LIVE-RUN proof clip (terminal style).

Every value on screen is copied from a real captured run
(demo/proof/capture/step*.txt, produced by capture_run.sh against a
fresh copy started with ./run.sh). Long JSON is trimmed for the
frame; no value is altered. 1280x720, 30fps, silent AAC.
"""
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
DEMO = HERE.parent
WORK = HERE / "work"
WORK.mkdir(exist_ok=True)

W, H = 1280, 720
BG = (10, 12, 10)
TEXT = (203, 213, 196)
GREEN = (169, 199, 165)
CREAM = (240, 234, 216)
FAINT = (150, 148, 128)
WATERMARK = "@heisdave01 / DEXTER WEB3"

FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FM = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"


def font(path, size):
    return ImageFont.truetype(path, size)


def frame(lines, caption=None):
    """lines: list of (text, color, size, bold) tuples."""
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text((48, 30), "FARM AJO: LIVE RUN", font=font(FB, 25), fill=GREEN)
    d.text((48, 66), "one command · full circle · real output",
           font=font(FR, 19), fill=FAINT)
    d.line([48, 108, W - 48, 108], fill=(52, 58, 48), width=2)
    y = 138
    for text, color, size in lines:
        d.text((48, y), text, font=font(FM, size), fill=color)
        y += int(size * 1.62)
    if caption:
        cf = font(FB, 30)
        d.text((48, H - 108), caption, font=cf, fill=CREAM)
    wf = font(FR, 17)
    tw = d.textlength(WATERMARK, font=wf)
    d.text((W - 40 - tw, H - 42), WATERMARK, font=wf, fill=(120, 116, 98))
    return img


CMD = GREEN
OUT = TEXT
KEY = CREAM

FRAMES = [
    # (lines, caption, seconds)
    ([
        ("$ ./run.sh", CMD, 30),
        ("", OUT, 24),
        ("FARM AJO: LIVE RUN", KEY, 34),
        ("", OUT, 24),
        ("One command starts the demo.", OUT, 24),
        ("A full savings circle runs end to end.", OUT, 24),
        ("Real output from the real app. Nothing staged.", OUT, 24),
    ], None, 4.0),
    ([
        ("$ curl localhost:8792/circle", CMD, 23),
        ("{", OUT, 23),
        ('  "name": "Planting Season Circle - Kaduna (demo)",', OUT, 23),
        ('  "target": 40000,', OUT, 23),
        ('  "pot": 32500,', KEY, 23),
        ('  "remaining_to_target": 7500,', OUT, 23),
        ('  "state": "open",', OUT, 23),
        ('  "member_count": 8,', OUT, 23),
        ('  "members_fully_paid": 6,', OUT, 23),
        ('  "total_shortfall": 7500', OUT, 23),
        ("}", OUT, 23),
    ], "The circle, part-way funded: 32,500 of 40,000.", 7.0),
    ([
        ("$ curl -X POST localhost:8792/agent/tick", CMD, 23),
        ('"funded": false,', OUT, 23),
        ('"actions": [', OUT, 23),
        ('  "reminder: Halima Usman still owes 2500', OUT, 23),
        ('   of their 5000 share",', OUT, 23),
        ('  "reminder: Emeka Nwosu still owes 5000', OUT, 23),
        ('   of their 5000 share",', OUT, 23),
        ('  "hold: pot is 32500 of 40000;', KEY, 23),
        ('   no purchase below target"', KEY, 23),
        ("],", OUT, 23),
        ('"circle_state": "open"', OUT, 23),
    ], "Below target, the agent refuses to buy.", 8.0),
    ([
        ("$ curl -X POST localhost:8792/contributions \\", CMD, 21),
        ("    -d '{\"farmer_id\": \"farmer-emeka-nwosu\",", CMD, 21),
        ("         \"amount\": 5000}'", CMD, 21),
        ('  "recorded": true,   "pot": 37500,', KEY, 23),
        ('  "members_fully_paid": 7', OUT, 23),
        ("", OUT, 23),
        ("$ curl -X POST localhost:8792/contributions \\", CMD, 21),
        ("    -d '{\"farmer_id\": \"farmer-halima-usman\",", CMD, 21),
        ("         \"amount\": 2500}'", CMD, 21),
        ('  "recorded": true,   "pot": 40000,', KEY, 23),
        ('  "members_fully_paid": 8', OUT, 23),
    ], "The two missing shares land. Pot full.", 8.0),
    ([
        ("$ curl -X POST localhost:8792/agent/tick", CMD, 23),
        ('"funded": true,', KEY, 23),
        ('"actions": [', OUT, 23),
        ('  "target reached: pot 40000 >= target 40000",', OUT, 23),
        ('  "bulk purchase fired: 20 bags of NPK 15-15-15', OUT, 23),
        ('   from Kaduna Agro Inputs Ltd for 40000",', OUT, 23),
        ('  "signature 1 of 2: delivery record ready for', OUT, 23),
        ('   the supplier account supplier.farmajo-dev.testnet",', OUT, 23),
        ('  "signature 2 of 2: QC attestation ready for', OUT, 23),
        ('   the verifier account verifier.farmajo-dev.testnet"', OUT, 23),
        ("],", OUT, 23),
        ('"circle_state": "verified"', KEY, 23),
    ], "At target, the purchase fires itself.", 9.0),
    ([
        ("$ curl localhost:8792/receipts", CMD, 23),
        ('"delivered_by": "Kaduna Agro Inputs Ltd",', OUT, 23),
        ('"supplier_account": "supplier.farmajo-dev.testnet",', OUT, 23),
        ('"attested_by": "Fatima Sule — QC Verifier,', OUT, 23),
        ('   Kaduna Farmers\' Co-operative",', OUT, 23),
        ('"verifier_account": "verifier.farmajo-dev.testnet",', OUT, 23),
        ('"bags": 20,  "grade": "NPK 15-15-15",', OUT, 23),
        ('"qc_passed": true,', KEY, 23),
        ('"checks": ["bag count matches the purchase order",', OUT, 23),
        ('  "sample bags weigh within +/-2% of 50 kg",', OUT, 23),
        ('  "granules uniform; no excessive caking", ...]', OUT, 23),
    ], "Two signatures. Neither can do the other's job.", 9.0),
]


def main():
    paths = []
    for i, (lines, cap, _dur) in enumerate(FRAMES, 1):
        p = WORK / f"pf{i}.png"
        frame(lines, cap).save(p)
        paths.append(p)
        print("frame", p)
    endcard = DEMO / "friend_cut" / "endcard.png"
    segs = []
    for p, (_l, _c, dur) in zip(paths, FRAMES):
        segs += ["-loop", "1", "-t", str(dur), "-i", str(p)]
    segs += ["-loop", "1", "-t", "5", "-i", str(endcard)]
    n = len(FRAMES) + 1
    filt = "".join(f"[{i}:v]" for i in range(n)) + f"concat=n={n}:v=1:a=0[v]"
    out = HERE / "farm-ajo-live-run.mp4"
    cmd = (["ffmpeg", "-y", "-v", "error"] + segs +
           ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
            "-filter_complex", filt, "-map", "[v]", "-map", f"{n}:a",
            "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p",
            "-r", "30", "-c:a", "aac", "-b:a", "128k", "-shortest",
            "-movflags", "+faststart", str(out)])
    subprocess.run(cmd, check=True)
    print("wrote", out)


if __name__ == "__main__":
    main()
