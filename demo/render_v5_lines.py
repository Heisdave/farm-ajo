#!/usr/bin/env python3
"""Render Farm Ajo v5 VO lines in Inspiring Gong via /opt/hatch/bin/tts."""
import subprocess, sys
from pathlib import Path

DEMO = Path(__file__).resolve().parent
OUT = DEMO / "vo_v5"
OUT.mkdir(exist_ok=True)
VOICE = "avocado_v2:vg_ng_m23"  # Inspiring Gong — Nigerian, rich/direct

LINES = {
    "line1": ("Farmers save together so they can afford "
              "fertilizer before planting.", 100),
    "line2": ("Eight farmers in Kaduna each save five thousand into "
              "one Ajo circle \u2014 forty thousand for twenty bags of "
              "fertilizer, bought before prices spike.", 100),
    "line3": ("An agent treasurer keeps the books, and flags who "
              "still owes: Halima, two thousand five hundred. "
              "Emeka, five thousand.", 100),
    "line4": ("The last shares land, the pot hits forty thousand "
              "\u2014 and the agent fires the bulk purchase by "
              "itself.", 100),
    "line5": ("The supplier signs what it delivered. Fatima Sule, "
              "the co-operative's QC verifier, signs the quality "
              "checks \u2014 bag count, weights, granules, grade "
              "\u2014 the checks from a blending-plant floor.", 100),
    "line5_fast": ("The supplier signs what it delivered. Fatima Sule, "
                   "the co-operative's QC verifier, signs the quality "
                   "checks \u2014 bag count, weights, granules, grade "
                   "\u2014 the checks from a blending-plant floor.", 115),
    "line6": ("Both signatures live on NEAR testnet, open for anyone "
              "to check. The chain proves the record existed. The "
              "verifier's name is why you trust it.", 100),
    "line7a": ("Ajo, but the pot has a job.", 88),
    "line7b": ("Farm Ajo. Real-World Money, built at the NEAR "
               "Hackathon.", 100),
}


def dur(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True)
    return float(r.stdout.strip())


def main():
    only = sys.argv[1:] or list(LINES)
    for name in only:
        text, speed = LINES[name]
        out = OUT / f"{name}.mp3"
        subprocess.run(["/opt/hatch/bin/tts", "--text", text,
                        "--voice", VOICE, "--speed", str(speed),
                        "--output", str(out)], check=True,
                       capture_output=True)
        print(f"{name}: speed {speed}, {dur(out):.2f}s -> {out.name}")


if __name__ == "__main__":
    main()
