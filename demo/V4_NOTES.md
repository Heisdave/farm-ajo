# Farm Ajo — demo video v4 notes ("less lifeless" pass, 2026-11-10)

**Output:** `demo/farm-ajo-demo-v4.mp4` — v3's video stream copied
untouched (h264 1920×1080 yuv420p 30 fps, 59.13 s) + a rebuilt audio
track. v3 remains intact as the fallback.

## What changed (audio only)

### 1. Ending VO lift — lines 6 and 7 re-rendered
Same voice as v3 ("Pensive Hull", `avocado_v2:vd2_r8_rep5k_3443_v068_28k_g5k`,
Nigerian, deep/composed). The tts tool exposes speed only — no
pitch/emphasis controls — so the lift is done with pace + structure.
Words are exactly as scripted in VOICEOVER.md. New files in
`demo/vo_v4/`:

- **Line 6** (`line6_v4.mp3`) re-rendered at speed **138** (v3: 125) —
  brisker, more forward. 7.44 s (was 8.88 s), still placed at 42.3 s,
  so it now ends at 49.74 s instead of spilling ~2 s into the end
  card — sync with its own scene is *better* than v3.
- **Line 7 split in two** to manufacture the held beat:
  - `line7a_v4.mp3` — "Ajo, but the pot has a job." at speed **112**
    (slower, weightier). Placed at **51.30 s**: after line 6 ends
    (49.74 s) there is a **~1.6 s beat** where only the music pad
    breathes before the tagline lands (v3's gap was 0.42 s).
  - `line7b_v4.mp3` — "Farm Ajo. Real-World Money, built at the NEAR
    Hackathon." at speed 125, placed at 54.32 s (0.55 s pause after
    the tagline), ending at 58.76 s (v3 ended 58.68 s — same landing).
- Lines 1–5 are the unchanged v3 renders at the unchanged v3 offsets
  (0.4 / 5.3 / 15.9 / 24.1 / 30.6 s).

### 2. Music bed — synthesised pad, kept
- **Source:** generated with ffmpeg, no external/licensed material —
  a I–V–vi–IV loop (C–G–Am–F, ×2) of sine-tone chords, 2.5 s
  slow-attack/release crossfades per chord, low-passed at 800 Hz,
  gentle fade-in (3 s) and fade-out (last 5 s). No drums, no vocals.
  Intermediates kept in `demo/vo_v4/` (`bed.wav`, `bed_raw.wav`,
  `vo_mix_v4.wav`).
- **Level:** bed mean −51 dB against speech-active windows at
  ~−23 dB → the pad sits **~28 dB under the voice**, static (no
  ducking). It reads as warmth/motion in the gaps, never as a tune.
- Final mix passed through −2 dB headroom + limiter; decoded peaks
  −1.0 dB, no clipping (a first mux hit −0.0 dB after AAC overshoot
  and was redone).

### 3. Ken Burns motion — SKIPPED, deliberately
The composited scene frames (`demo/work_v2/`) no longer exist on
disk; regenerating them means re-running build_v2.py (which would
overwrite the v2 deliverable), and a supersampled zoompan re-encode
of all 1,774 frames on this VM risks both encode time and xfade
timing drift for a cosmetic gain. Per the brief's guardrail — do not
jeopardise the cut — the video stream is v3's, byte-for-byte.

## Verification (ffprobe / volumedetect on the final file)
- Video: h264, 1920×1080, yuv420p, 30 fps — stream-copied from v3.
- Audio: AAC, 48 kHz, present throughout; total duration 59.133 s.
- Speech windows: line 6 (42.3–49.7 s) mean −22.8 dB; line 7
  (51.3–58.8 s) mean −23.6 dB (pre-headroom pass) — ~29 dB above the
  bed. Held-beat window (49.8–51.3 s) mean −53.0 dB = pad only,
  confirming the pause is real and the bed alone fills it.
- Ending window (42.3–58.7 s) overall loudness matches v3 (−23.6 vs
  −23.7 dB): the lift is pacing and pause, not volume.

## Honest self-assessment
The ending lands better than v3, measurably in structure if not in
loudness: line 6 arrives with more energy and stops crowding the end
card, there's a genuine held beat before the tagline, and the tagline
itself is delivered slower and heavier, with the credits line given
its own breath after it. The pad removes the "voice in a vacuum"
flatness Dexter flagged — the two planned silence gaps in v3 are now
the two quietest-but-alive moments instead of dead air. Limits, said
plainly: I still cannot literally listen from this VM, so "more
energy" rests on the faster render + timing analysis, not on hearing
the performance; and without the Ken Burns pass the *picture* is as
static as v3 — v4 fixes the sound of lifeless, not the look of it.
If Dexter still finds the visuals plain after hearing v4, the motion
pass is a separate, schedulable job — not a reason to hold v4.
