#!/usr/bin/env python3
"""Executable checks for the deterministic path behind each eval scenario.

These prove the *toolchain* produces correct, MIDI-ready, verifiable material for each
scenario. They do not prove musical quality — that needs listening (see evals.json,
assertions typed "subjective-listening").

Run: python3 evals/check_toolchain.py
"""
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from theory_core import (check_voicing, identify, parse_progression, voice_progression,  # noqa: E402
                         voice_leading_cost, analyze_progression, parse_key, chords_containing, note_to_midi)
import midi_io  # noqa: E402

MC = [sys.executable, os.path.join(ROOT, "scripts", "mc.py")]
results = []


def check(n, name, cond, detail=""):
    results.append((n, name, bool(cond), detail))


def mc(*args, stdin=None):
    return subprocess.run(MC + list(args), capture_output=True, text=True, input=stdin)


def mcj(*args):
    r = mc("--json", *args)
    return json.loads(r.stdout), r.returncode


tmp = tempfile.mkdtemp()

# 1. Four-bar jazzy DnB progression -> verified voicings + sub bass
d, rc = mcj("voice", "Fm9 Bbm9 Eb13 Abmaj9", "--style", "rhodes", "--bpm", "174")
v = d["voicings"]
check(1, "4 chords voiced", len(v) == 4)
check(1, "keys >= MIDI 48", all(min(r["midi"]) >= 48 for r in v))
check(1, "bass in sub range 24-43", all(24 <= r["bass_midi"] <= 43 for r in v))
check(1, "clip is 16 beats", d["clip"]["length_beats"] == 16)

# 2. Rhodes voicings: rootless, one hand, smooth
chords = [c for c, _ in parse_progression("Dm9 G13 Cmaj9 A7b13")]
vs = voice_progression(chords, "rhodes")
check(2, "all validate", all(check_voicing(c, list(x))["ok"] for c, x in zip(chords, vs)))
check(2, "rootless", all(c.root.pc not in {m % 12 for m in x} for c, x in zip(chords, vs)))
check(2, "3-5 notes, span <= 12", all(3 <= len(x) <= 5 and x[-1] - x[0] <= 12 for x in vs))
check(2, "lowest >= 50", all(x[0] >= 50 for x in vs))
move = [voice_leading_cost(a, b) for a, b in zip(vs, vs[1:])]
check(2, "each change moves <= 8 semitones total", all(m <= 8 for m in move), str(move))

# 3. Harmonise a bassline with approach notes
bass = {"notes": [{"pitch": 41, "start_time": 0, "duration": 3}, {"pitch": 45, "start_time": 3, "duration": 1},
                  {"pitch": 46, "start_time": 4, "duration": 3}, {"pitch": 40, "start_time": 7, "duration": 1},
                  {"pitch": 39, "start_time": 8, "duration": 4}, {"pitch": 44, "start_time": 12, "duration": 4}]}
bp = os.path.join(tmp, "bass.json")
json.dump(bass, open(bp, "w"))
seg, _ = mcj("notes", bp, "--window", "4")
check(3, "window analysis returns 4 bars", len(seg["segments"]) == 4)
for prog in ["Fm9 Bbm9 Eb13 Abmaj9", "Fm11 Bb13 Ebmaj9 Abmaj7#11", "Fm9 Bbm7 Eb9sus4 Abmaj9"]:
    r, rc = mcj("validate", bp, "--role", "bass", "--chords", prog)
    approach = [x for x in r["report"] if x.get("pitch") in (45, 40)]
    check(3, f"bass validates over {prog}", r["problems"] == 0)
    check(3, f"A1/E1 classed as approach over {prog}", all(x["class"] in ("approach", "passing", "chord") for x in approach))
opts = [o["chord"] for o in chords_containing(5, *parse_key("F minor"))]
check(3, "bass-options F in F minor includes Fm7 and Dbmaj7", "Fm7" in opts and "Dbmaj7" in opts, str(opts))

# 4. Identify chords from MIDI
bars = [[41, 56, 60, 63, 67], [46, 56, 60, 61, 65], [39, 55, 60, 61, 65], [44, 58, 60, 63, 67]]
want = ["Fm9", "Bbm9", "Eb13", "Abmaj9"]
got = [identify(b)[0]["name"] for b in bars]
check(4, "identifies Fm9 Bbm9 Eb13 Abmaj9", got == want, str(got))
an = analyze_progression([c for c, _ in parse_progression(" ".join(got))])
check(4, "key candidates include F minor and Ab major",
      {"F minor", "Ab major"} <= {k["key"] for k in an["key_candidates"]})

# 5. Three reharmonisations keeping melody G C F F
mel = {"notes": [{"pitch": p, "start_time": i * 4, "duration": 4} for i, p in enumerate([67, 72, 65, 65])]}
mp = os.path.join(tmp, "mel.json")
json.dump(mel, open(mp, "w"))
for prog in ["Cmaj9 Am9 Dm9 G9sus4", "Cmaj7 A7#9b13 Dm9 Db7", "Cmaj7 Abmaj7 Fm9 Bb13"]:
    r, _ = mcj("validate", mp, "--role", "melody", "--chords", prog)
    check(5, f"melody fits {prog}", r["problems"] == 0 and all(x.get("class") in ("chord", "tension", None)
                                                               for x in r["report"]))
    top = [note_to_midi(x) for x in ["G3", "C4", "F3", "F3"]]
    cs = [c for c, _ in parse_progression(prog)]
    vv = voice_progression(cs, "rhodes", top_line=top)
    check(5, f"melody is top voice for {prog}", [x[-1] for x in vv] == top, str(vv))

# 6. Explain Cmaj7 Fm7 Cmaj7: borrowed chord, changed note named
an = analyze_progression([c for c, _ in parse_progression("Cmaj7 Fm7 Cmaj7")], parse_key("C major"))
row = an["chords"][1]
check(6, "Fm7 flagged as borrowed with Ab named", row["status"] == "non-diatonic" and "Ab" in row["explanation"][0],
      str(row))

# 7. Melody over harmony: validator stats
mel7 = {"notes": [{"pitch": 72, "start_time": 0, "duration": 1.5}, {"pitch": 70, "start_time": 1.5, "duration": 0.5},
                  {"pitch": 68, "start_time": 2, "duration": 2}, {"pitch": 72, "start_time": 4, "duration": 1.5},
                  {"pitch": 70, "start_time": 5.5, "duration": 0.5}, {"pitch": 68, "start_time": 6, "duration": 2},
                  {"pitch": 67, "start_time": 8, "duration": 1.5}, {"pitch": 65, "start_time": 9.5, "duration": 0.5},
                  {"pitch": 63, "start_time": 10, "duration": 2}, {"pitch": 67, "start_time": 12, "duration": 4}]}
p7 = os.path.join(tmp, "mel7.json")
json.dump(mel7, open(p7, "w"))
r, _ = mcj("validate", p7, "--role", "melody", "--chords", "Fm9 Bbm9 Eb13 Abmaj9")
stats = r["report"][-1]["stats"]
check(7, "strong-beat chord/tension >= 70%", stats["strong_beat_chord_or_tension_pct"] >= 70, str(stats))
check(7, "motif reuse detected", stats["repeated_motif_cells"] >= 1, str(stats))
check(7, "range <= 19 semitones", stats["range_semitones"] <= 19)

# 8. MIDI-compatible output round-trips
cj = os.path.join(tmp, "pads.json")
mid = os.path.join(tmp, "pads.mid")
r = mc("voice", "Cm9:8 Fm9:8 Abmaj7:8 G7alt:8", "--style", "pad", "--out", cj, "--mid", mid)
clip = json.load(open(cj))
notes = clip["tracks"][0]["notes"]
check(8, "pitches 0-127, durations > 0", all(0 <= n["pitch"] <= 127 and n["duration"] > 0 for n in notes))
check(8, "chords start at 0, 8, 16, 24", sorted({n["start_time"] for n in notes}) == [0, 8, 16, 24])
back = midi_io.read_midi(mid.replace(".mid", "-pad-chords.mid"))
check(8, "MIDI file round-trips exactly",
      sorted((n["pitch"], n["start_time"], n["duration"]) for n in back["tracks"][0]["notes"]) ==
      sorted((n["pitch"], n["start_time"], n["duration"]) for n in notes))
r = mc("validate", cj, "--track", "0", "--beats", "8", "--chords", "Cm9 Fm9 Abmaj7 G7alt")
check(8, "pad clip validates against symbols", r.returncode == 0, r.stdout[-300:])

# 9. Ambiguity reported
names = [d_["name"] for d_ in identify([56, 60, 63, 67])]
check(9, "Abmaj7 and Fm9 both offered", "Abmaj7" in names and "Fm9" in names, str(names))
r = mc("identify", "Ab2", "C3", "Eb3", "G3")
check(9, "CLI flags ambiguity", "Ambiguous" in r.stdout or "rootless" in r.stdout)

# 10. Works with no MCP: offline .mid delivery
r = mc("voice", "Am9 Dm9 Em9 Am9", "--style", "stab", "--hits", "0.5,1.5,2.5,3.5", "--hit-len", "0.25",
       "--bpm", "124", "--mid", os.path.join(tmp, "stab.mid"))
files = [os.path.join(tmp, f) for f in ("stab-stab-chords.mid", "stab-bass.mid")]
check(10, "per-part .mid files written", all(os.path.exists(f) for f in files), r.stderr)
check(10, "valid SMF header", all(open(f, "rb").read(4) == b"MThd" for f in files if os.path.exists(f)))
check(10, "short-note rhythm", all(n["duration"] <= 0.25 for n in midi_io.read_midi(files[0])["tracks"][0]["notes"]))

failed = [r_ for r_ in results if not r_[2]]
for n, name, ok, detail in results:
    print(f"[{'PASS' if ok else 'FAIL'}] scenario {n}: {name}" + (f"  -- {detail}" if not ok and detail else ""))
print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
sys.exit(1 if failed else 0)
