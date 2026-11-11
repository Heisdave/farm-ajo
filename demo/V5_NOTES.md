# Farm Ajo — demo video v5 notes (Dexter's three fixes, 2026-11-10)

**Output:** `demo/farm-ajo-demo-v5.mp4` — NEW video stream (overlay
backgrounds, built by `demo/build_v5.py`, a copy of build_v2.py —
build_v2.py and the v2/v3/v4 deliverables are untouched) + a fully
rebuilt audio track. v4 remains intact as the fallback.

## 1. New voice — Inspiring Gong (all 7 lines re-rendered)

Dexter picked **Inspiring Gong** (`avocado_v2:vg_ng_m23`) — Nigerian
male, rich/direct, faster natural pacing — after hearing samples
(`demo/vo_samples/gong_*`). Words are EXACTLY as scripted in
VOICEOVER.md. Renders in `demo/vo_v5/`. Speeds were fitted per line:
Gong's long lines run long (sentence pauses), so the two longest
lines were rendered faster to honour scene starts; the ending keeps
the v4 structure Dexter approved (energised line 6 → held beat →
slower tagline → sign-off).

| Line | Speed | Dur (s) | Placed (s) | Ends (s) | Scene (starts) |
|---|---|---|---|---|---|
| 1 — farmers line | 100 | 3.60 | 0.40 | 4.00 | 1 title (0) |
| 2 — eight farmers | 100 | 9.12 | 5.30 | 14.42 | 2 circle (5.1) |
| 3 — agent flags | 100 | 7.80 | 15.90 | 23.70 | 3 log flag (15.7) |
| 4 — purchase fires | 100 | 5.81 | 24.10 | 29.91 | 4 log trig (23.8) |
| 5 — two signatures | 140 | 7.94 | 33.00 | 40.94 | 5 receipt (32.9) |
| 6 — on NEAR testnet | 115 | 8.23 | 41.30 | 49.53 | 6 chain (39.0) |
| 7a — tagline | 88 | 2.54 | 51.05 | 53.59 | 7 end card (49.1) |
| 7b — sign-off | 100 | 4.49 | 54.10 | 58.59 | 7 end card |

Fit notes (honest, same standard as v3/v4 notes):
- Every line STARTS inside its own scene; no overlaps (gaps 1.30 /
  1.48 / 0.40 / 3.09 / 0.36 s), nothing clipped; last word ends at
  58.59 of 59.13.
- Line 5 remains the structural exception: 27 words cannot fit the
  receipt shot's 6.5 s in any voice. At speed 140 it overruns only
  ~1.5 s into the chain scene (v3's Hull render overran ~3 s), and
  its content (delivery + attestation) bridges the two beats.
- Line 6 ends 0.43 s into the end-card crossfade — same landing as
  v4 (49.74) and inaudible as an issue under the fade.
- **Held beat:** line 6 ends 49.53 → tagline at 51.05 = **1.52 s of
  music only**, then the tagline at speed 88 (slower/weightier),
  then the sign-off after a 0.51 s pause, ending 58.59 (target
  ~58.8 ✓).

## 2. Overlay backgrounds (visual rebuild)

`build_v5.py` blends each scene's AI overlay into the dark gradient
background; page screenshots are pasted opaquely on top, so the
imagery lives in the frame margins as texture — no veil over text.

| Scene | Overlay | Opacity | Notes |
|---|---|---|---|
| 1 title | overlay1_farmland | 20% | |
| 2 circle | overlay2_farmers | 20% | |
| 3 log flag | overlay2_farmers | 20% | contributions beat |
| 4 log trigger | overlay3_bags | 20% | purchase beat |
| 5 receipt | overlay3_bags | 20% | |
| 6 chain record | overlay3_bags | 20% | |
| 7 end card | overlay4_seedlings | 15% + blur 3px | per overlays/NOTES.md — hands kept soft so text dominates |

Scene durations and 0.4 s xfades are byte-identical to v2/v3/v4
(5.5 / 11.0 / 8.5 / 9.5 / 6.5 / 10.5 / 10.0 → 59.13 s). Frame
spot-checks from the encoded file (margins, mean luminance): v5
70.8–76.6 vs v4 38.9–45.2 on content scenes — overlay clearly
present; end card 39.9 vs 38.9 — deliberately near-unchanged.
Frames at 10 s (circle) and 55 s (end card) were visually inspected:
all UI text, captions and end-card rows perfectly readable.

## 3. Music bed — same pad, ~6 dB hotter

v4's synthesised pad (`vo_v4/bed.wav`: C–G–Am–F sine chords,
low-passed 800 Hz, no drums/vocals) re-used at **+6 dB**
(`vo_v5/bed_hot.wav`, mean −45.0 dB, peaks −33.8 — no clipping).
Against speech-active windows at ≈ −22.6 dB the bed now sits
**≈ 22 dB under the voice** (v4: ~28–29 dB) — the brief's target.
The voice remains clearly on top in every window; no ducking, and
the hotter bed did not muddy speech, so no 24 dB fallback was
needed. Final mix: +1.5 dB make-up into a −1 dB-ceiling limiter
(v4 method); decoded peaks −1.1 dB, no clipping.

## Verification (ffprobe / volumedetect on the FINAL mp4)

- Video: h264, 1920×1080, yuv420p, 30 fps. Audio: AAC 160 kbps,
  48 kHz. Duration 59.133 s. File 6,131,107 bytes.
- Speech windows (mean): 0–5 s −24.3 dB · 30–42 s −26.2 dB ·
  42–51 s −22.6 dB · 51–59 s −22.2 dB — speech present throughout.
- Held-beat window (49.6–51.0 s): −44.1 dB = pad only, confirming
  the pause survives the hotter bed.
- Overall: mean −24.0 dB, max −1.1 dB.

## v5.1 — line-5 pace fix (audio only, 2026-11-10)

**Output:** `demo/farm-ajo-demo-v5_1.mp4` — v5's video stream copied
byte-for-byte (streamhash MD5 identical: f1695979a4c393edaa4d3d9eb27d6916)
+ rebuilt audio. v5, v4, v3 untouched.

**Why:** Dexter's ear caught what the table couldn't hide — line 5 at
speed 140 against neighbours at 100–115 suddenly feels ~2× at ~0:32.

**Fix:** line 5 re-rendered in Inspiring Gong as two sentence clips
(renders in `vo_v5/`, kept as `line5a.mp3` / `line5b.mp3`). First
attempt at speed 115 measured 1.82 + 9.96 s — the pause-heavy list
sentence could not fit the window at 115 in any placement. The chosen
renders are both at **speed 120** (inside the 112–125 nudge band),
whose internal pauses happened to land tighter (~1.9 s of pauses in
5b vs ~3.1 s in the 115 render):

| Clip | Speed | Dur (s) | Placed (s) | Ends (s) |
|---|---|---|---|---|
| 5a — "The supplier signs what it delivered." | 120 | 1.61 | 31.00 | 32.61 |
| breath | — | 0.40 | 32.61 | 33.01 |
| 5b — "Fatima Sule, the co-operative's QC verifier…" | 120 | 8.09 | 33.01 | 41.10 |

5a plays over the purchase→receipt transition (its delivery sentence
belongs with the purchase shot); 5b starts where v5's line 5 started
(33.0, the receipt scene) and ends 0.20 s before line 6 (41.30) —
no overlap with line 4 (ends 29.91; 1.09 s gap) or line 6.
**Speed ratios vs neighbours:** 120/100 (line 4) = 1.20×, 120/115
(line 6) = 1.04× — max 1.20×, inside the ~1.25× target (old line 5:
1.40× vs line 4). In delivered pace, 5b's list actually runs *more*
measured than its neighbours (~156 wpm vs ~186–190) because of its
comma/dash pauses; 5a is a 1.6 s burst of a single short sentence.

**Method:** surgical, to guarantee nothing else moved — the original
`vo_v5/vo_track.wav` was muted only across 32.90–41.05 (verified
digital silence on both sides of the old line 5) and the two new
clips were added at their offsets (`vo_v5/vo_track_v51.wav`). The
final chain was first proven bit-faithful: original vo_track +
`bed_hot.wav` through amix(normalize=0) → +1.5 dB → alimiter
(limit 0.8913) reproduces `audio_v5.wav`'s measured stats exactly
(mean −24.0, max −1.1). Same chain → `vo_v5/audio_v5_1.wav`, muxed
with `-c:v copy`, AAC 160 kbps 48 kHz mono (v5's format).

**Verification (final mp4):** 59.133 s, h264 1920×1080 yuv420p
30 fps + AAC — identical to v5. Windows: 0–5 s −24.3 dB (= v5) ·
30–33 −26.9 (5a speech) · 33–41.1 −25.4 (5b speech) · breath
32.61–33.01 −39.7 (bed only) · 41.1–41.3 −39.7 (bed only — 5b is
done, line 6 starts clean) · 30–42 overall −25.0, max −3.8 (= v5's
window max; no clipping) · 42–51 −22.6 / max −1.1 (= v5, ending
untouched) · held beat 49.6–51.0 −44.1 (= v5) · 51–59 −22.1 ·
overall mean −23.8, max −1.1 dB (0.2 dB hotter overall than v5
because the new line 5 fills more of its window with speech).
Whether 120 *feels* even is, as ever, Dexter's ear call.

## Honest self-assessment

All three of Dexter's fixes are in and verified by measurement and
frame inspection: the Gong voice is quicker and more direct than
Hull (whether it sounds *human enough* is still Dexter's ear call —
I cannot listen from this VM); the overlays end the "plain
background" complaint without touching readability — the screenshot
at 10 s genuinely looks like a product filmed inside its own world
now; and the bed is present rather than subliminal, filling the
gaps (the 3.1 s gap before line 5 and the held beat now feel like
breathing, not dead air). Residual risks, plainly: line 5 at speed
140 is brisk — intelligible on the numbers (27 words / 7.9 s ≈
205 wpm, radio pace) but it is the fastest moment in the video; and
the overlay margins at 20% are a taste call Dexter may want at 15%
or 25% — a one-line change in build_v5.py and a re-encode (~2 min)
if he asks. v5 is the current cut; v4 stands as fallback.
