#!/usr/bin/env python3
"""Build demo/farm-ajo-demo-v2.mp4 from real /demo screenshots.

Fix-round rebuild after the external review:
- every beat is cropped from ONE full-page screenshot of ONE state
  (v1 mixed element screenshots from different states — that is how a
  frame ended up with a 32,500 header over a 37,500 table);
- the agent treasurer log gets two beats (shortfall flag, then the
  purchase trigger);
- the receipt beat is short and shows both named signatures;
- the explorer beat falls back to the on-chain card with big hashes
  (headless Chromium in this VM cannot tunnel through the egress
  proxy to either testnet explorer — see BUILD_NOTES fix round);
- captions carry the VOICEOVER.md lines: edge-tts is unreachable from
  this VM (websocket stream blocked by the egress proxy), so v2 ships
  captioned; the script is ready to render the moment a route opens.

Specs (same as v1): 1920x1080, h264, yuv420p, 30 fps, crf 18,
dark olive/brown, no orange, watermark "@heisdave01 / DEXTER WEB3".
Run: python3 demo/build_v2.py   (needs Pillow + ffmpeg)
"""
import subprocess, sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

DEMO = Path(__file__).resolve().parent
SHOTS = DEMO / "shots_v2"
WORK = DEMO / "work_v2"
WORK.mkdir(exist_ok=True)

W, H = 1920, 1080
CREAM = (240, 234, 216)
GREEN = (169, 199, 165)
FAINT = (196, 188, 164)
WATERMARK = "@heisdave01 / DEXTER WEB3"

FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FM = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"


def font(path, size):
    return ImageFont.truetype(path, size)


def background():
    img = Image.new("RGB", (W, H))
    top, bottom = (46, 43, 30), (23, 22, 17)
    px = img.load()
    for y in range(H):
        t = y / H
        c = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        for x in range(0, W, 8):
            for dx in range(8):
                px[x + dx, y] = c
    return img


def wrap(draw, text, fnt, max_w):
    words, lines, cur = text.split(), [], ""
    for w_ in words:
        trial = f"{cur} {w_}".strip()
        if draw.textlength(trial, font=fnt) <= max_w:
            cur = trial
        else:
            lines.append(cur)
            cur = w_
    if cur:
        lines.append(cur)
    return lines


def base_frame():
    img = background()
    d = ImageDraw.Draw(img)
    wf = font(FR, 30)
    tw = d.textlength(WATERMARK, font=wf)
    d.text((W - 70 - tw, H - 62), WATERMARK, font=wf, fill=(168, 160, 138))
    return img, d


def caption(img, text):
    d = ImageDraw.Draw(img)
    f = font(FB, 44)
    lines = wrap(d, text, f, 1500)
    y = H - 88 - 56 * len(lines)
    for ln in lines:
        d.text((90, y), ln, font=f, fill=CREAM)
        y += 56
    return img


def paste_shot(img, shot, max_w=1600, max_h=800, center_y=None):
    s = Image.open(SHOTS / shot).convert("RGB")
    scale = min(max_w / s.width, max_h / s.height)
    s = s.resize((int(s.width * scale), int(s.height * scale)),
                 Image.LANCZOS)
    x = (W - s.width) // 2
    y = ((center_y if center_y is not None else 470) - s.height // 2)
    img.paste(s, (x, max(24, y)))
    return img


def title_card():
    img, d = base_frame()
    d.text((140, 300), "FARM AJO", font=font(FB, 170), fill=CREAM)
    d.rectangle([146, 520, 760, 528], fill=GREEN)
    d.text((140, 580), "Ajo, but the pot has a job.",
           font=font(FB, 72), fill=GREEN)
    d.text((140, 700),
           "Farmers save together so they can afford fertilizer "
           "before planting.", font=font(FR, 38), fill=FAINT)
    d.text((140, 800), "NEAR HACKATHON · BUILD BEYOND BOUNDARIES",
           font=font(FB, 30), fill=FAINT)
    return img


def end_card():
    img, d = base_frame()
    d.text((140, 180), "Ajo, but the pot has a job.",
           font=font(FB, 84), fill=CREAM)
    d.rectangle([146, 310, 760, 318], fill=GREEN)
    rows = [
        ("Track: Real-World Money", FB, 46, CREAM, 400),
        ("Live on NEAR testnet:  circle2.farmajo-dev.testnet",
         FB, 42, GREEN, 500),
        ("explorer.testnet.near.org/accounts/circle2.farmajo-dev.testnet",
         FM, 33, FAINT, 575),
        ("Submission repo:  github.com/Heisdave/farm-ajo",
         FB, 42, CREAM, 680),
        ("Built at the NEAR Hackathon — Build Beyond Boundaries",
         FR, 34, FAINT, 770),
    ]
    for text, fp, size, color, y in rows:
        d.text((140, y), text, font=font(fp, size), fill=color)
    return img


def chain_frame():
    img, d = base_frame()
    d.text((160, 90), "Attestation transaction — live on NEAR testnet",
           font=font(FB, 40), fill=GREEN)
    paste_shot(img, "crop_chain.png", max_w=1600, max_h=560, center_y=480)
    d.text((160, 830),
           "explorer.testnet.near.org/transactions/"
           "9dv6SwC2mBJrWezFLbrTwUHNmbkuepj7ozbwuTB9p57",
           font=font(FM, 30), fill=FAINT)
    return img


SCENES = [
    # (frame builder, duration s, caption or None)
    (lambda: title_card(), 5.5, None),
    (lambda: caption(paste_shot(base_frame()[0], "crop_circle.png"),
                     "Eight farmers. One savings circle. "
                     "A planting-season deadline."), 11.0, None),
    (lambda: caption(paste_shot(base_frame()[0], "crop_logflag.png",
                                max_h=760),
                     "The agent treasurer flags who still owes."),
     8.5, None),
    (lambda: caption(paste_shot(base_frame()[0], "crop_logtrig.png",
                                max_h=760),
                     "Pot reached 40,000 — the purchase fires itself."),
     9.5, None),
    (lambda: caption(paste_shot(base_frame()[0], "crop_receipt.png",
                                max_h=760),
                     "Two signatures. Neither can do the other's job."),
     6.5, None),
    (lambda: caption(chain_frame(),
                     "Open the record. Check the signatures yourself."),
     10.5, None),
    (lambda: end_card(), 10.0, None),
]


def main():
    frames = []
    for i, (build, _dur, _cap) in enumerate(SCENES, 1):
        path = WORK / f"frame{i}.png"
        build().save(path)
        frames.append(path)
        print("frame", path)
    durations = [d for _b, d, _c in SCENES]
    fade = 0.4
    inputs, filters, prev, offset = [], [], None, 0.0
    for i, (path, dur) in enumerate(zip(frames, durations)):
        inputs += ["-loop", "1", "-t", f"{dur}", "-i", str(path)]
    for i in range(len(frames)):
        if i == 0:
            prev = "[0:v]"
            offset = durations[0]
            continue
        offset -= fade
        out = f"[x{i}]"
        filters.append(
            f"{prev}[{i}:v]xfade=transition=fade:duration={fade}"
            f":offset={offset:.2f}{out}")
        prev = out
        offset += durations[i]
    total = offset
    cmd = (["ffmpeg", "-y"] + inputs +
           ["-filter_complex", ";".join(filters),
            "-map", prev, "-r", "30", "-c:v", "libx264", "-crf", "18",
            "-pix_fmt", "yuv420p", str(DEMO / "farm-ajo-demo-v2.mp4")])
    print("total ~", round(total, 1), "s")
    subprocess.run(cmd, check=True, capture_output=True)
    print("wrote", DEMO / "farm-ajo-demo-v2.mp4")


if __name__ == "__main__":
    sys.exit(main())
