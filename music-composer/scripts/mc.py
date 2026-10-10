#!/usr/bin/env python3
"""music-composer CLI: deterministic theory, voicing and MIDI helpers.

Run `python3 mc.py <command> -h` for options. Global flags go before the command:
  --spn   name octaves in scientific pitch (C4 = MIDI 60) instead of Ableton (C3 = MIDI 60)
  --json  machine-readable output

Commands
  spell       chord symbols -> notes, degrees, required/optional tones, MIDI
  identify    notes (names or MIDI numbers) -> ranked chord interpretations
  check       does a voicing (MIDI notes) really spell a chord? register/playability warnings
  voice       progression -> voice-led, instrument-aware voicings (+ bass), clip JSON / .mid
  analyze     progression -> key candidates, roman numerals, borrowed/secondary chords, root motion
  scale       notes of a scale/mode with degrees and character
  diatonic    the chords that live in a key
  fit         which scales/keys contain a set of notes
  bass-options which chords in a key contain a given bass note, and what that does
  notes       analyse an existing clip (MCP JSON, clip JSON or .mid): chords over time + key
  validate    check a written part against a chord progression (roles: chords, bass, melody)
  midi-read   .mid -> clip JSON
  midi-write  clip JSON -> .mid (optionally one file per track)
  interval    name the interval between two notes
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from theory_core import (  # noqa: E402
    MODE_NOTES, MODES, STYLES, DEGREE_NAMES, TheoryError, Chord, analyze_progression, bass_note,
    check_voicing, chords_containing, default_spelling, describe_chord, detect_key, diatonic_chords,
    fit_scales, identify, interval_name, load_notes, midi_name, midi_octave, movement_report, note_to_midi,
    parse_chord, parse_key, parse_progression, scale_notes, segment_notes, voice_progression, Spelled,
    CONVENTIONS,
)
import midi_io  # noqa: E402

CONV = "ableton"
AS_JSON = False


# ---------------------------------------------------------------- helpers

ODD = {("C", -1), ("F", -1), ("E", 1), ("B", 1)}


def odd(sp: Spelled) -> bool:
    return abs(sp.acc) == 2 or (sp.letter, sp.acc) in ODD


def disp(sp: Spelled) -> str:
    s = str(sp)
    if odd(sp):
        s += f" [={default_spelling(sp.pc)}]"
    return s


def note_str(midi: int, ch: Chord | None = None) -> str:
    sp = None
    if ch is not None:
        t = ch.tone_for_pc(midi % 12)
        if t is not None:
            sp = ch.spell(t)
        elif ch.bass and ch.bass.pc == midi % 12:
            sp = ch.bass
    if sp is None:
        sp = default_spelling(midi % 12, prefer_flats=True if ch is None else ch.root.acc <= 0)
    name = f"{sp}{midi_octave(midi, sp, CONV)}"
    if odd(sp):
        alt = default_spelling(sp.pc)
        name += f"[={alt}{midi_octave(midi, alt, CONV)}]"
    return f"{name}({midi})"


def conv_banner() -> str:
    return "Octaves: Ableton naming, C3 = MIDI 60" if CONV == "ableton" else "Octaves: scientific pitch, C4 = MIDI 60"


def emit(obj, text: str) -> None:
    if AS_JSON:
        print(json.dumps(obj, indent=2, default=str))
    else:
        print(text)


def parse_notes(tokens: list[str]) -> list[int]:
    """Names with octaves, MIDI numbers, or bare pitch classes (placed ascending from octave 3)."""
    from theory_core import parse_note
    out: list[int] = []
    for tok in tokens:
        for t in tok.replace(",", " ").split():
            if t == "|":
                continue
            if re.fullmatch(r"[A-Ga-g](?:##|bb|#|b|x|♯|♭)?", t):
                sp, _ = parse_note(t)
                m = (3 + CONVENTIONS[CONV]) * 12 + sp.pc
                while out and m <= out[-1]:
                    m += 12
                out.append(m)
            else:
                out.append(note_to_midi(t, CONV))
    return out


def note_groups(tokens: list[str]) -> list[list[str]]:
    groups, cur = [], []
    for tok in " ".join(tokens).replace("|", " | ").split():
        if tok == "|":
            if cur:
                groups.append(cur)
            cur = []
        else:
            cur.append(tok)
    if cur:
        groups.append(cur)
    return groups


def read_any(path: str) -> dict:
    if path.lower().endswith((".mid", ".midi")):
        return midi_io.read_midi(path)
    with open(path) as f:
        return json.load(f)


def pick_track(obj, track: str | None):
    if isinstance(obj, dict) and "tracks" in obj and track is not None:
        trs = obj["tracks"]
        if track.isdigit():
            return trs[int(track)]["notes"]
        for t in trs:
            if t.get("name", "").lower() == track.lower():
                return t["notes"]
        raise TheoryError(f"No track {track!r}; tracks: {[t.get('name') for t in trs]}")
    return obj


def timeline(prog: list[tuple[Chord, float]], length: float) -> list[tuple[Chord, float, float]]:
    out, t, total = [], 0.0, sum(b for _, b in prog)
    while t < max(length, total) - 1e-9:
        for ch, b in prog:
            out.append((ch, t, t + b))
            t += b
            if t >= max(length, total) - 1e-9:
                break
    return out


# ---------------------------------------------------------------- commands

def cmd_spell(a):
    res, lines = [], [conv_banner()]
    errors = 0
    for sym in a.chords:
        try:
            ch = parse_chord(sym)
        except TheoryError as e:
            lines.append(f"\n{sym}: error — {e}")
            res.append({"symbol": sym, "error": str(e)})
            errors += 1
            continue
        d = describe_chord(ch)
        base = (int(a.octave) + CONVENTIONS[CONV]) * 12 + ch.root.pc
        stack = [base + t.semis for t in ch.tones]
        d["root_position_midi"] = stack
        res.append(d)
        req = [t["label"] for t in d["tones"] if t["role"] == "required"]
        opt = [t["label"] for t in d["tones"] if t["role"] == "optional"]
        alt = [t["label"] for t in d["tones"] if t["role"] == "alt"]
        lines.append(f"\n{ch.name()}  ({ch.family})")
        lines.append("  notes:    " + "  ".join(f"{disp(ch.spell(t))}={t.label}" for t in ch.tones))
        lines.append("  must have: " + (", ".join(req) or "-") + ("   (root: usually the bass)" ))
        if opt:
            lines.append("  optional:  " + ", ".join(opt))
        if alt:
            lines.append("  altered tensions (use 1-2): " + ", ".join(alt))
        if "bass" in d:
            lines.append(f"  bass: {d['bass']['note']} — {d['bass']['relation']}"
                         + (f"; the whole sound is {d['bass']['sounds_as']}" if d['bass'].get('sounds_as') else ""))
        lines.append("  stacked root position: " + " ".join(note_str(m, ch) for m in stack)
                     + "  (reference only — not a recommended voicing)")
    emit(res, "\n".join(lines))
    if errors:
        sys.exit(2)


def cmd_identify(a):
    groups = note_groups(a.notes)
    bass = note_to_midi(a.bass, CONV) if a.bass else None
    out, lines = [], [conv_banner()]
    for gi, g in enumerate(groups):
        midis = parse_notes(g)
        res = identify(midis, bass, limit=a.limit)
        if len(groups) > 1:
            lines.append(f"\n[{gi + 1}]")
        lines.append("notes: " + " ".join(note_str(m) for m in sorted(midis))
                     + (f"  bass: {note_str(bass)}" if bass is not None else ""))
        pcs = {m % 12 for m in midis} | ({bass % 12} if bass is not None else set())
        if len(pcs) < 3:
            s_ = sorted(set(midis) | ({bass} if bass is not None else set()))
            lines.append("Fewer than 3 distinct pitch classes — not enough to name a chord.")
            if len(s_) == 2:
                lines.append(f"Interval: {interval_name(s_[1] - s_[0])}")
            out.append({"candidates": [], "pitch_classes": sorted(pcs)})
            continue
        if not res:
            lines.append("No standard chord matches these notes (likely a cluster or contains passing tones).")
        for i, d in enumerate(res, 1):
            lines.append(f"{i}. {d['name']}" + (f"  — {d['notes']}" if d["notes"] else ""))
        if len(res) > 1 and res[1]["score"] - res[0]["score"] < 1.05:
            lines.append("Ambiguous: the top readings are close. The bassline/context decides which one you hear.")
        out.append({"candidates": res})
    if all(not any(c.isdigit() for c in t) for g in groups for t in g):
        lines.append("(no octaves given: notes were stacked upward from octave 3 — the lowest note counts as the bass)")
    emit(out[0] if len(out) == 1 else {"groups": out}, "\n".join(lines))


def cmd_check(a):
    ch = parse_chord(a.chord)
    midis = parse_notes(a.notes)
    bass = note_to_midi(a.bass, CONV) if a.bass else None
    r = check_voicing(ch, midis, bass, CONV)
    lines = [conv_banner(), f"{r['chord']}: {'OK' if r['ok'] else 'MISMATCH'}"]
    lines.append("  " + "  ".join(f"{n['name']}({n['midi']})={n['tone'] or 'NOT IN CHORD'}" for n in r["notes"]))
    if r["missing_required"]:
        lines.append("  missing: " + ", ".join(r["missing_required"]))
    if r["extra_notes"]:
        lines.append("  not in the chord: " + ", ".join(r["extra_notes"]))
    lines.append(f"  span {r['span_semitones']} semitones — {r['playability']}")
    for w in r["warnings"]:
        lines.append("  ! " + w)
    emit(r, "\n".join(lines))
    if not r["ok"]:
        sys.exit(1)


def user_bass_per_chord(path: str, prog: list[tuple[Chord, float]], track: str | None) -> list[int | None]:
    notes = load_notes(pick_track(read_any(path), track))
    out, t = [], 0.0
    for _, beats in prog:
        sounding = [n["pitch"] for n in notes if n["start_time"] - 1e-6 <= t < n["start_time"] + n["duration"] - 1e-6]
        starting = [n for n in notes if t - 1e-6 <= n["start_time"] < t + beats - 1e-6]
        if sounding:
            out.append(min(sounding))
        elif starting:
            out.append(min(starting, key=lambda n: (n["start_time"], n["pitch"]))["pitch"])
        else:
            out.append(None)
        t += beats
    return out


def cmd_voice(a):
    prog = parse_progression(a.progression, a.beats)
    chords = [c for c, _ in prog]
    include_root = True if (a.no_bass or a.with_root) else None
    top = None
    if a.top_line:
        top = [None if t in ("-", "_", "x") else note_to_midi(t, CONV) for t in a.top_line.replace(",", " ").split()]
    center = note_to_midi(a.center, CONV) if a.center else None
    lo, hi = (note_to_midi(x, CONV) for x in a.bass_range.split("-")) if a.bass_range else (28, 43)
    if a.bass_file:
        basses = user_bass_per_chord(a.bass_file, prog, a.bass_track)
    elif a.no_bass:
        basses = [None] * len(chords)
    else:
        basses = [bass_note(ch, lo, hi) for ch in chords]
    vwarn: list[str] = []
    vs = voice_progression(chords, a.style, a.voices, include_root, center, loop=not a.no_loop, top_line=top,
                           warnings=vwarn, bass_bottom=a.no_bass, basses=basses)
    vel = a.velocity or STYLES[a.style]["vel"]
    hits = [float(x) for x in a.hits.split(",")] if a.hits else None

    rows, chord_notes, bass_notes, t = [], [], [], 0.0
    bass_label = " + your bassline" if a.bass_file else ("" if a.no_bass else " + bass")
    lines = [conv_banner(), f"style: {a.style}{bass_label}" + ("  (loop-aware voice leading)" if not a.no_loop else "")]
    for i, ((ch, beats), v, b) in enumerate(zip(prog, vs, basses)):
        chk = check_voicing(ch, list(v), b, CONV)
        if not chk["ok"]:
            raise TheoryError(f"internal check failed for {ch.name()}: {chk}")
        labels = [ch.tone_for_pc(m % 12).label for m in v]
        warns = [w for w in chk["warnings"] if not w.startswith("rootless")]
        if b is not None and b >= v[0]:
            warns.append("the bass note is at or above the chord's lowest note — lower the bass or raise the chords")
        row = {"chord": ch.name(), "start": t, "beats": beats, "midi": list(v),
               "names": [note_str(m, ch) for m in v], "degrees": labels,
               "bass_midi": b, "playability": chk["playability"], "warnings": warns}
        if i:
            row["voice_leading"] = movement_report(vs[i - 1], v)
        rows.append(row)
        if hits is None:
            for m in v:
                chord_notes.append({"pitch": m, "start_time": round(t, 4), "duration": round(beats, 4),
                                    "velocity": vel, "mute": False})
        else:
            bar = 0.0
            while bar < beats - 1e-9:  # the hit pattern repeats every 4-beat bar of the chord
                for h in hits:
                    if bar + h < beats - 1e-9:
                        dur = min(a.hit_len, beats - bar - h)
                        for m in v:
                            chord_notes.append({"pitch": m, "start_time": round(t + bar + h, 4),
                                                "duration": round(dur, 4), "velocity": vel, "mute": False})
                bar += 4.0
        if b is not None and not a.bass_file:
            bass_notes.append({"pitch": b, "start_time": t, "duration": beats, "velocity": 100, "mute": False})
        lines.append(f"\n{i + 1}. {ch.name():<12} beats {t:g}-{t + beats:g}")
        lines.append(f"   {a.style:<7} " + " ".join(row["names"]) + "   degrees: " + " ".join(labels))
        if b is not None:
            lines.append(f"   bass    {note_str(b, ch)}" + ("  (from your bassline)" if a.bass_file else ""))
        lines.append(f"   playing: {chk['playability']}")
        if i:
            vl = row["voice_leading"]
            extra = f", {vl['voices_added_or_dropped']} voice(s) added/dropped" if vl["voices_added_or_dropped"] else ""
            lines.append(f"   from previous: {vl['held']} note(s) held, voices move {vl['semitones']} semitones "
                         f"in total{extra}, top voice {vl['top_move']:+d}")
        for w in warns:
            lines.append("   ! " + w)
        t += beats
    if not a.no_loop and len(vs) > 2:
        vl = movement_report(vs[-1], vs[0])
        lines.append(f"\nloop back to bar 1: {vl['held']} held, voices move {vl['semitones']} semitones")
    for w in vwarn:
        lines.append("! " + w)
    lines.append("\nAll voicings verified: every note belongs to its chord and every required tone is present.")

    clip = {"bpm": a.bpm, "time_signature": [4, 4], "length_beats": t,
            "tracks": [{"name": f"{a.style.title()} chords", "notes": chord_notes}]}
    if bass_notes:
        clip["tracks"].append({"name": "Bass", "notes": bass_notes})
    if a.out:
        with open(a.out, "w") as f:
            json.dump(clip, f, indent=1)
        lines.append(f"clip JSON -> {a.out}")
    if a.mid:
        written = write_mid(clip, a.mid, split=True)
        lines.append("MIDI -> " + ", ".join(written))
    emit({"voicings": rows, "clip": clip, "warnings": vwarn}, "\n".join(lines))


def write_mid(clip: dict, path: str, split: bool) -> list[str]:
    if not split or len(clip["tracks"]) == 1:
        midi_io.write_midi(clip, path)
        return [path]
    stem = path[:-4] if path.lower().endswith(".mid") else path
    out = []
    for i, tr in enumerate(clip["tracks"]):
        safe = "".join(c if c.isalnum() else "-" for c in tr["name"].lower()).strip("-")
        p = f"{stem}-{safe}.mid"
        midi_io.write_midi(clip, p, track_filter=i)
        out.append(p)
    return out


def cmd_analyze(a):
    prog = parse_progression(a.progression)
    key = parse_key(a.key) if a.key else None
    r = analyze_progression([c for c, _ in prog], key)
    lines = [f"key: {r['key']}" + ("" if a.key else "  (guessed)")]
    if not a.key:
        c = r["key_candidates"]
        if len(c) > 1 and c[0]["fit"] - c[1]["fit"] < 0.05:
            lines.append(f"  ambiguous: {c[0]['key']} and {c[1]['key']} fit equally — "
                         "the bassline and which chord feels like home decide it")
    for row in r["chords"]:
        lines.append(f"\n{row['chord']:<12} {row['numeral']:<12} {row['status']}")
        if "function" in row:
            lines.append(f"   function: {row['function']}")
        if "colour" in row:
            lines.append(f"   {row['colour']}")
        for e in row.get("explanation", []):
            lines.append(f"   {e}")
        if "root_motion_to_next" in row:
            lines.append(f"   -> next: root moves {row['root_motion_to_next']}")
    emit(r, "\n".join(lines))


def cmd_scale(a):
    root, _ = (parse_key(f"{a.root} {a.mode}"))
    mode = parse_key(f"{a.root} {a.mode}")[1]
    notes = scale_notes(root, mode)
    steps = MODES[mode]
    base = (int(a.octave) + CONVENTIONS[CONV]) * 12 + root.pc
    midi = [base + s for s in steps]
    r = {"scale": f"{root} {mode}", "notes": [str(n) for n in notes],
         "degrees": [DEGREE_NAMES[s] for s in steps], "midi": midi, "character": MODE_NOTES.get(mode, "")}
    lines = [conv_banner(), f"{root} {mode}: " + " ".join(disp(n) for n in notes),
             "degrees: " + " ".join(r["degrees"]), "MIDI: " + " ".join(note_str(m) for m in midi)]
    if r["character"]:
        lines.append("character: " + r["character"])
    emit(r, "\n".join(lines))


def cmd_diatonic(a):
    root, mode = parse_key(a.key)
    rows = diatonic_chords(root, mode, a.size)
    lines = [f"{root} {mode} — diatonic chords"] + [f"  {r['numeral']:<10} {r['chord']:<10} {' '.join(r['notes'])}"
                                                     for r in rows]
    emit(rows, "\n".join(lines))


def cmd_fit(a):
    midis = parse_notes(a.notes) if all(any(c.isdigit() for c in n) for n in a.notes) else None
    if midis is None:
        from theory_core import parse_note
        pcs = {parse_note(n)[0].pc for tok in a.notes for n in tok.replace(",", " ").split()}
    else:
        pcs = {m % 12 for m in midis}
    rows = fit_scales(pcs, a.limit)
    lines = ["pitch classes: " + " ".join(default_spelling(p).__str__() for p in sorted(pcs))]
    lines += [f"  {r['scale']:<22} ({r['unused']} scale notes unused)" for r in rows] or ["  no common scale contains all of these"]
    emit(rows, "\n".join(lines))


def cmd_bass_options(a):
    from theory_core import parse_note
    sp, _ = parse_note(a.note)
    root, mode = parse_key(a.key)
    rows = chords_containing(sp.pc, root, mode, a.size)
    lines = [f"{sp} in the bass, key of {root} {mode}:"] + [
        f"  {r['chord']:<10} {r['numeral']:<10} bass is the {r['bass_is']} — {r['effect']}" for r in rows]
    lines.append("  (chromatic options — secondary dominants, borrowed chords, slash chords — are a musical "
                 "choice; ask the model, then verify with `check`)")
    emit(rows, "\n".join(lines))


def cmd_notes(a):
    obj = read_any(a.file)
    notes = load_notes(pick_track(obj, a.track))
    if not notes:
        raise TheoryError("no notes found")
    segs = segment_notes(notes, a.window)
    keys = detect_key(notes)
    rows = []
    lines = [conv_banner(), f"{len(notes)} notes, {min(n['pitch'] for n in notes)}-{max(n['pitch'] for n in notes)} "
             f"({note_str(min(n['pitch'] for n in notes))} to {note_str(max(n['pitch'] for n in notes))})",
             "key estimate: " + ", ".join(f"{k['key']} (r={k['r']})" for k in keys)]
    if keys[0]["r"] - keys[1]["r"] < 0.05:
        lines.append("  key is ambiguous between the top candidates")
    mono = max(len(s["pitches"]) for s in segs) < 3
    if mono and not a.window:
        lines.append("Mostly single notes — looks like a bass or melody. Use --window 4 (beats) to read "
                     "the implied harmony per bar, or `fit` to find scales.")
    for s in segs:
        pitches = s["pitches"]
        if a.window:
            w = s["weights"]
            thresh = 0.4 * max(w.values())  # ignore short approach/passing notes
            pitches = [p for p in pitches if w[p] >= thresh]
        cands = identify(pitches, limit=3) if len({p % 12 for p in pitches}) >= 3 else []
        row = {"start": s["start"], "end": s["end"], "pitches": pitches,
               "chords": [c["name"] for c in cands], "detail": cands[:1]}
        rows.append(row)
        label = " / ".join(row["chords"]) or ("(interval: " + interval_name(pitches[-1] - pitches[0]) + ")"
                                             if len(pitches) == 2 else "(single note)" if len(pitches) == 1 else "-")
        lines.append(f"  {s['start']:>6g}-{s['end']:<6g} " + " ".join(note_str(p) for p in pitches) + f"  -> {label}")
    named = [parse_chord(r["chords"][0]) for r in rows if r["chords"]]
    harmonic = []
    if len(named) >= 2:
        from theory_core import guess_keys
        harmonic = guess_keys(named)
        lines.append("key from the identified chords: " + ", ".join(f"{k['key']} ({k['fit']})" for k in harmonic)
                     + "   <- usually more reliable than the note-count estimate for chord clips")
    emit({"key_candidates": keys, "harmonic_key_candidates": harmonic, "segments": rows}, "\n".join(lines))


AVAILABLE = {  # tensions (semitones above root) that are normally safe over each chord family
    "major": {2: "9", 6: "#11", 9: "13"}, "dominant": {1: "b9", 2: "9", 3: "#9", 6: "#11", 8: "b13", 9: "13"},
    "minor": {2: "9", 5: "11", 9: "13 (dorian)", 8: "b13 (aeolian)"}, "minor-major": {2: "9", 5: "11", 9: "13"},
    "half-diminished": {2: "9", 5: "11", 8: "b13"}, "diminished": {2: "9", 5: "11", 8: "b13", 11: "7"},
    "sus": {2: "9", 9: "13", 10: "b7"}, "dominant-sus": {2: "9", 9: "13", 1: "b9", 3: "#9"},
    "augmented": {2: "9", 6: "#11"}, "power": {}}
AVOID = {"major": {5: "11 (clashes with the 3rd)"}, "dominant": {5: "11 (clashes with the 3rd)"},
         "minor": {1: "b9"}, "minor-major": {1: "b9"}}


def classify(pitch: int, ch: Chord, role: str = "melody") -> tuple[str, str]:
    t = ch.tone_for_pc(pitch % 12)
    if t is not None and (role == "bass" or t.label in ("1", "3", "b3", "5", "b5", "#5", "b7", "7", "bb7", "6", "2", "4")):
        return "chord", t.label
    if t is not None:
        return "tension", t.label
    rel = (pitch - ch.root.pc) % 12
    if rel in AVAILABLE.get(ch.family, {}):
        return "tension", AVAILABLE[ch.family][rel]
    if rel in AVOID.get(ch.family, {}):
        return "avoid", AVOID[ch.family][rel]
    return "outside", DEGREE_NAMES[rel]


ANTICIPATION = 0.5  # a chord change up to an 8th early counts as a push into the next chord


def cmd_validate(a):
    obj = read_any(a.file)
    notes = sorted(load_notes(pick_track(obj, a.track)), key=lambda n: (n["start_time"], n["pitch"]))
    prog = parse_progression(a.chords, a.beats)
    length = max(n["start_time"] + n["duration"] for n in notes)
    tl = timeline(prog, length)
    loop_len = sum(b for _, b in prog)

    def chord_at(t, allow_push=True):
        for idx, (ch, s, e) in enumerate(tl):
            if s - 1e-6 <= t < e - 1e-6:
                if allow_push and idx + 1 < len(tl) and e - t <= ANTICIPATION + 1e-6 and t > s + 1e-6:
                    return tl[idx + 1]
                return ch, s, e
        return tl[-1]

    lines, report, problems = [conv_banner(), f"role: {a.role}"], [], 0
    if a.role == "chords":
        # Check at every onset and every chord change: all notes sounding there (held notes included).
        points = sorted({round(n["start_time"], 4) for n in notes} | {round(s, 4) for _, s, _ in tl if s < length})
        prev_key = None
        for o in points:
            sounding = sorted({n["pitch"] for n in notes if n["start_time"] - 1e-6 <= o < n["start_time"] + n["duration"] - 1e-6})
            if not sounding:
                continue
            starts_here = any(abs(n["start_time"] - o) < 1e-6 for n in notes)
            ch, cs, _ = chord_at(o, allow_push=starts_here)
            key = (ch.name(), cs, tuple(sounding))
            if key == prev_key:
                continue
            prev_key = key
            r = check_voicing(ch, sounding, None, CONV)
            pushed = o < cs - 1e-6
            report.append({"beat": o, "chord": ch.name(), "pushed": pushed, **r})
            if not r["ok"]:
                problems += 1
            status = "ok" if r["ok"] else "MISMATCH"
            extra = ""
            if r["missing_required"]:
                extra += " missing " + ",".join(r["missing_required"])
            if r["extra_notes"]:
                held = [n for n in r["extra_notes"]]
                extra += " not in chord " + ",".join(held)
            lines.append(f"  beat {o:>6g} {ch.name():<12}{' (pushed)' if pushed else ''} {status}{extra}  "
                         + " ".join(f"{x['name']}={x['tone'] or '?'}" for x in r["notes"]))
            for w in r["warnings"]:
                if not w.startswith("rootless"):
                    lines.append("     ! " + w)
    else:
        strong_ct = strong_total = 0
        n_notes = len(notes)
        loops = abs(length - round(length / loop_len) * loop_len) < 0.51 if loop_len else False
        for i, n in enumerate(notes):
            ch, s, e = chord_at(n["start_time"])
            kind, label = classify(n["pitch"], ch, a.role)
            if i + 1 < n_notes:
                nxt, nxt_t = notes[i + 1], notes[i + 1]["start_time"]
            elif loops and n_notes > 1:
                nxt, nxt_t = notes[0], 0.0  # the part loops: the last note leads back to the first
            else:
                nxt, nxt_t = None, None
            prv = notes[i - 1] if i > 0 else (notes[-1] if loops and n_notes > 1 else None)
            movable = ("outside", "avoid", "tension") if a.role == "bass" else ("outside", "avoid")
            if kind in movable and nxt is not None:
                step_next = abs(nxt["pitch"] - n["pitch"]) in (1, 2)
                step_prev = prv is not None and abs(n["pitch"] - prv["pitch"]) in (1, 2)
                nk, _ = classify(nxt["pitch"], chord_at(nxt_t)[0], a.role)
                if step_next and nk in ("chord", "tension"):
                    kind = "passing" if step_prev else "approach"
            downbeat = abs(n["start_time"] - s) < 1e-3
            strong = abs(n["start_time"] / 2 - round(n["start_time"] / 2)) < 1e-3  # beats 1 and 3
            flag = ""
            if a.role == "bass":
                if downbeat:
                    tone = ch.tone_for_pc(n["pitch"] % 12)
                    if kind != "chord":
                        flag = "downbeat is not a chord tone"
                    elif tone and tone.label != "1" and not (ch.bass and ch.bass.pc == n["pitch"] % 12):
                        flag = f"inversion: {label} on the downbeat (fine if intended)"
                if n["pitch"] < 24:
                    flag += " | below MIDI 24 (~33 Hz): inaudible on most systems"
                if n["pitch"] > 55:
                    flag += " | high for a bass part"
            else:
                if strong:
                    strong_total += 1
                    if kind in ("chord", "tension"):
                        strong_ct += 1
                if strong and n["duration"] >= 0.5 and kind in ("outside", "avoid"):
                    flag = "held non-chord note on a strong beat — check by ear"
            flag = flag.strip(" |")
            if flag and "fine if intended" not in flag:
                problems += 1
            report.append({"beat": n["start_time"], "pitch": n["pitch"], "chord": ch.name(), "class": kind,
                           "label": label, "flag": flag})
            lines.append(f"  beat {n['start_time']:>6g} {note_str(n['pitch'], ch):<12} over {ch.name():<10} "
                         f"{kind:<8} {label:<14} {flag}")
        if a.role == "melody":
            ps = [n["pitch"] for n in notes]
            ivs = [b - a_ for a_, b in zip(ps, ps[1:])]
            durs = [round(n["duration"], 3) for n in notes]
            leaps = sum(1 for x in ivs if abs(x) > 7)
            steps = sum(1 for x in ivs if 0 < abs(x) <= 2)
            cells: dict = {}
            for k in range(len(ivs) - 1):
                cell = (tuple(ivs[k:k + 2]), tuple(durs[k:k + 3]))  # 3-note shape + rhythm, any transposition
                cells[cell] = cells.get(cell, 0) + 1
            rhythm_cells: dict = {}
            for k in range(len(durs) - 2):
                rc = tuple(durs[k:k + 3])
                rhythm_cells[rc] = rhythm_cells.get(rc, 0) + 1
            repeats = sum(c - 1 for c in cells.values() if c > 1)
            rrepeats = sum(c - 1 for c in rhythm_cells.values() if c > 1)
            stats = {"range": [min(ps), max(ps)], "range_semitones": max(ps) - min(ps),
                     "stepwise_pct": round(100 * steps / max(1, len(ivs))), "leaps_over_5th": leaps,
                     "strong_beat_chord_or_tension_pct": round(100 * strong_ct / max(1, strong_total)),
                     "repeated_motif_cells": repeats, "repeated_rhythm_cells": rrepeats}
            report.append({"stats": stats})
            lines.append(f"\n  range {note_str(min(ps))}-{note_str(max(ps))} ({stats['range_semitones']} st), "
                         f"{stats['stepwise_pct']}% stepwise, {leaps} leap(s) > a 5th, "
                         f"{stats['strong_beat_chord_or_tension_pct']}% of beat-1/3 notes are chord tones/tensions, "
                         f"motif reuse: {repeats} repeated 3-note shape(s) (pitch+rhythm, any transposition), "
                         f"{rrepeats} repeated rhythm cell(s)")
    lines.append(f"\n{problems} item(s) to check." if problems else "\nNo problems found.")
    lines.append("This checks pitch/role correctness only — whether it sounds good needs your ears.")
    emit({"problems": problems, "report": report}, "\n".join(lines))
    if problems and (a.role == "chords" or a.strict):
        sys.exit(1)


def cmd_midi_read(a):
    clip = midi_io.read_midi(a.file)
    if a.out:
        with open(a.out, "w") as f:
            json.dump(clip, f, indent=1)
    lines = [f"bpm {clip['bpm']}, time signature {clip['time_signature'][0]}/{clip['time_signature'][1]}"]
    for i, t in enumerate(clip["tracks"]):
        lines.append(f"  [{i}] {t['name']}: {len(t['notes'])} notes")
    if a.out:
        lines.append(f"clip JSON -> {a.out}")
    emit(clip if not a.out else {"written": a.out, "tracks": len(clip["tracks"])}, "\n".join(lines))


def cmd_midi_write(a):
    with open(a.clip) as f:
        clip = json.load(f)
    if "tracks" not in clip:
        clip = {"bpm": a.bpm, "tracks": [{"name": "Clip", "notes": load_notes(clip)}]}
    written = write_mid(clip, a.out, a.split)
    emit({"written": written}, "MIDI -> " + ", ".join(written))


def cmd_interval(a):
    x, y = parse_notes([a.a])[0], parse_notes([a.b])[0]
    d = y - x
    r = {"semitones": d, "name": interval_name(d), "direction": "up" if d > 0 else "down" if d < 0 else "same"}
    emit(r, f"{note_str(x)} -> {note_str(y)}: {r['name']} {r['direction']} ({abs(d)} semitones)")


# ---------------------------------------------------------------- main

def main(argv=None):
    global CONV, AS_JSON
    p = argparse.ArgumentParser(prog="mc.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--spn", action="store_true", help="scientific pitch octave names (C4 = 60)")
    p.add_argument("--json", action="store_true", help="JSON output")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("spell"); s.add_argument("chords", nargs="+"); s.add_argument("--octave", default="3")
    s.set_defaults(fn=cmd_spell)

    s = sub.add_parser("identify"); s.add_argument("notes", nargs="+"); s.add_argument("--bass")
    s.add_argument("--limit", type=int, default=5); s.set_defaults(fn=cmd_identify)

    s = sub.add_parser("check"); s.add_argument("chord"); s.add_argument("notes", nargs="+"); s.add_argument("--bass")
    s.set_defaults(fn=cmd_check)

    s = sub.add_parser("voice")
    s.add_argument("progression", help='e.g. "Fm9 Bbm9 Eb13 Abmaj9" or "Cm9:2 F13:2 | Bbmaj9" ("%%" repeats)')
    s.add_argument("--style", choices=sorted(STYLES), default="rhodes")
    s.add_argument("--beats", type=float, default=4.0, help="beats per chord unless given as Chord:beats")
    s.add_argument("--voices", type=int)
    s.add_argument("--center", help="register centre note, e.g. C4 or 64")
    s.add_argument("--top-line", help="target top note per chord, '-' to leave free, e.g. 'G4 F4 - Eb4'")
    s.add_argument("--with-root", action="store_true", help="keep the root in the voicing")
    s.add_argument("--no-bass", action="store_true", help="no bass part (root then stays in the voicing)")
    s.add_argument("--bass-range", help="bass register, e.g. E0-G1 or 28-43 (default 28-43)")
    s.add_argument("--bass-file", help="use the user's existing bassline (clip JSON/MCP JSON/.mid) instead of "
                                       "generating one; voicings are checked and spaced against it")
    s.add_argument("--bass-track", help="track index or name inside --bass-file")
    s.add_argument("--no-loop", action="store_true", help="don't optimise the last->first chord transition")
    s.add_argument("--hits", help="rhythm: hit positions in beats within each bar (repeats every bar of a "
                                  "chord), e.g. '0,1.5,3'")
    s.add_argument("--hit-len", type=float, default=0.5)
    s.add_argument("--velocity", type=int)
    s.add_argument("--bpm", type=float, default=120)
    s.add_argument("--out", help="write clip JSON")
    s.add_argument("--mid", help="write .mid (one file per part)")
    s.set_defaults(fn=cmd_voice)

    s = sub.add_parser("analyze"); s.add_argument("progression"); s.add_argument("--key")
    s.set_defaults(fn=cmd_analyze)

    s = sub.add_parser("scale"); s.add_argument("root"); s.add_argument("mode", nargs="?", default="major")
    s.add_argument("--octave", default="3"); s.set_defaults(fn=cmd_scale)

    s = sub.add_parser("diatonic"); s.add_argument("key"); s.add_argument("--size", type=int, default=4, choices=[3, 4, 5])
    s.set_defaults(fn=cmd_diatonic)

    s = sub.add_parser("fit"); s.add_argument("notes", nargs="+"); s.add_argument("--limit", type=int, default=10)
    s.set_defaults(fn=cmd_fit)

    s = sub.add_parser("bass-options"); s.add_argument("note"); s.add_argument("--key", required=True)
    s.add_argument("--size", type=int, default=4, choices=[3, 4, 5]); s.set_defaults(fn=cmd_bass_options)

    s = sub.add_parser("notes"); s.add_argument("file"); s.add_argument("--track"); s.add_argument("--window", type=float)
    s.set_defaults(fn=cmd_notes)

    s = sub.add_parser("validate"); s.add_argument("file"); s.add_argument("--chords", required=True)
    s.add_argument("--role", choices=["chords", "bass", "melody"], default="chords")
    s.add_argument("--track"); s.add_argument("--beats", type=float, default=4.0)
    s.add_argument("--strict", action="store_true", help="exit 1 if a bass/melody check flags anything")
    s.set_defaults(fn=cmd_validate)

    s = sub.add_parser("midi-read"); s.add_argument("file"); s.add_argument("--out"); s.set_defaults(fn=cmd_midi_read)

    s = sub.add_parser("midi-write"); s.add_argument("clip"); s.add_argument("out")
    s.add_argument("--split", action="store_true"); s.add_argument("--bpm", type=float, default=120)
    s.set_defaults(fn=cmd_midi_write)

    s = sub.add_parser("interval"); s.add_argument("a"); s.add_argument("b"); s.set_defaults(fn=cmd_interval)

    a = p.parse_args(argv)
    CONV = "spn" if a.spn else "ableton"
    AS_JSON = a.json
    try:
        a.fn(a)
    except (TheoryError, ValueError, KeyError, FileNotFoundError) as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
