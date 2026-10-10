"""Unit tests for the deterministic layer. Run: python3 -m unittest discover -s scripts/tests"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, SCRIPTS)

from theory_core import (  # noqa: E402
    STYLES, TheoryError, analyze_progression, check_voicing, diatonic_chords, identify, load_notes,
    low_interval_violations, note_to_midi, midi_name, parse_chord, parse_key, parse_progression,
    voice_leading_cost, voice_progression, segment_notes,
)
import midi_io  # noqa: E402

MC = [sys.executable, os.path.join(SCRIPTS, "mc.py")]


def names(sym):
    ch = parse_chord(sym)
    return [str(ch.spell(t)) for t in ch.tones]


class Notes(unittest.TestCase):
    def test_conventions(self):
        self.assertEqual(note_to_midi("C3"), 60)
        self.assertEqual(note_to_midi("C4", "spn"), 60)
        self.assertEqual(note_to_midi("Eb3"), 63)
        self.assertEqual(note_to_midi("B#2"), 60)
        self.assertEqual(note_to_midi("Cb3"), 59)
        self.assertEqual(note_to_midi("64"), 64)
        self.assertEqual(midi_name(60), "C3")
        self.assertEqual(midi_name(60, convention="spn"), "C4")

    def test_out_of_range(self):
        with self.assertRaises(TheoryError):
            note_to_midi("C9")


class Spelling(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(names("Fm9"), ["F", "Ab", "C", "Eb", "G"])
        self.assertEqual(names("Cmaj7"), ["C", "E", "G", "B"])
        self.assertEqual(names("Bbmaj9"), ["Bb", "D", "F", "A", "C"])
        self.assertEqual(names("F#m7b5"), ["F#", "A", "C", "E"])

    def test_enharmonic_correctness(self):
        self.assertEqual(names("C°7"), ["C", "Eb", "Gb", "Bbb"])
        self.assertIn("F##", names("E7#9"))
        self.assertIn("E#", names("C#maj7"))

    def test_aliases(self):
        for a, b in [("C-7", "Cm7"), ("Cmin7", "Cm7"), ("CM7", "Cmaj7"), ("CΔ7", "Cmaj7"), ("Cø", "Cm7b5"),
                     ("C7+5", "C7#5"), ("C7-9", "C7b9"), ("C6/9", "C69"), ("Cm(maj7)", "CmMaj7"),
                     ("Csus", "Csus4"), ("C7(b9,#11)", "C7b9#11")]:
            self.assertEqual(parse_chord(a).pcs(), parse_chord(b).pcs(), (a, b))

    def test_identity_rules(self):
        c13 = {t.label: t.role for t in parse_chord("C13").tones}
        self.assertNotIn("11", c13)          # natural 11 omitted over a major 3rd
        self.assertEqual(c13["13"], "required")
        self.assertEqual(c13["9"], "optional")
        m11 = {t.label: t.role for t in parse_chord("Cm11").tones}
        self.assertEqual(m11["11"], "required")
        alt = parse_chord("G7alt")
        self.assertNotIn("5", [t.label for t in alt.tones])
        self.assertEqual(parse_chord("Dm9/G").bass_pc, 7)

    def test_families(self):
        for sym, fam in [("C7", "dominant"), ("Cm7b5", "half-diminished"), ("Cdim7", "diminished"),
                         ("C7sus4", "dominant-sus"), ("Cmaj9", "major"), ("Cm9", "minor"), ("C5", "power")]:
            self.assertEqual(parse_chord(sym).family, fam, sym)

    def test_rejects_garbage(self):
        for bad in ["H7", "Cfoo", "C7q", ""]:
            with self.assertRaises(TheoryError):
                parse_chord(bad)


class Identify(unittest.TestCase):
    def top(self, notes, bass=None):
        return [d["name"] for d in identify([note_to_midi(n) for n in notes], bass)]

    def test_simple(self):
        self.assertEqual(self.top(["F2", "A2", "C3", "E3"])[0], "Fmaj7")
        self.assertEqual(self.top(["C2", "E2", "G2", "Bb2", "D3"])[0], "C9")
        self.assertEqual(self.top(["F1", "Ab2", "C3", "Eb3", "G3"])[0], "Fm9")

    def test_ambiguity_is_reported(self):
        r = self.top(["C2", "E2", "G2", "A2"])
        self.assertEqual(r[0], "C6")
        self.assertIn("Am7/C", r)
        r = self.top(["F2", "A2", "C3", "E3"])
        self.assertIn("Dm9", r)  # rootless reading offered

    def test_rootless_flag(self):
        d = identify([note_to_midi(n) for n in ["Ab2", "C3", "Eb3", "G3"]], bass=note_to_midi("F0"))
        self.assertEqual(d[0]["name"], "Fm9")

    def test_inversion(self):
        r = identify([note_to_midi(n) for n in ["E2", "G2", "C3"]])
        self.assertEqual(r[0]["name"], "C/E")


class Voicing(unittest.TestCase):
    PROGS = ["Fm9 Bbm9 Eb13 Abmaj9", "Dm9 G13 Cmaj9 A7b9", "Cm9 Dm7b5 G7alt Cm9", "Ebmaj7#11 Dm7 Gm9 C9sus4",
             "Am7 D9 Gmaj7 Cmaj7 F#m7b5 B7alt Em9", "C G Am F", "Bbm9 Gbmaj7 Db6/9 Ab7sus4", "F#m11 Bm9 E13 Amaj9"]

    def test_every_voicing_is_correct_and_playable(self):
        for prog in self.PROGS:
            chords = [c for c, _ in parse_progression(prog)]
            for style in STYLES:
                vs = voice_progression(chords, style)
                for ch, v in zip(chords, vs):
                    r = check_voicing(ch, list(v))
                    self.assertEqual(r["extra_notes"], [], (prog, style, ch.name(), v))
                    self.assertEqual(r["missing_required"], [], (prog, style, ch.name(), v))
                    self.assertFalse(low_interval_violations(list(v)), (prog, style, v))
                    self.assertLessEqual(v[-1] - v[0], STYLES[style]["span"] + 5)

    def test_voice_leading_beats_root_position_blocks(self):
        for prog in self.PROGS:
            chords = [c for c, _ in parse_progression(prog)]
            vs = voice_progression(chords, "rhodes")
            blocks = [tuple(48 + ch.root.pc + t.semis for t in ch.tones if t.role != "optional") for ch in chords]
            smooth = sum(voice_leading_cost(a, b) for a, b in zip(vs, vs[1:]))
            naive = sum(voice_leading_cost(a, b) for a, b in zip(blocks, blocks[1:]))
            self.assertLess(smooth, naive, prog)

    def test_identity_preserved(self):
        # The voicer never adds tones that aren't in the symbol (no sneaky 9ths on a maj7).
        ch = parse_chord("Cmaj7")
        v = voice_progression([ch], "rhodes")[0]
        self.assertTrue({m % 12 for m in v} <= ch.pcs())

    def test_top_line(self):
        chords = [c for c, _ in parse_progression("Fm9 Bbm9 Eb13 Abmaj9")]
        top = [note_to_midi(x) for x in ["C4", "Db4", "Bb3", "C4"]]
        vs = voice_progression(chords, "rhodes", top_line=top)
        self.assertEqual([v[-1] for v in vs], top)

    def test_low_interval_check(self):
        self.assertTrue(low_interval_violations([40, 43]))   # minor 3rd at E1 (Ableton): mud
        self.assertFalse(low_interval_violations([40, 47]))  # 5th is fine


class Analysis(unittest.TestCase):
    def rows(self, prog, key=None):
        chords = [c for c, _ in parse_progression(prog)]
        return analyze_progression(chords, parse_key(key) if key else None)

    def test_secondary_and_tritone_sub(self):
        r = self.rows("Cmaj7 A7 Dm7 G7 Ebmaj7 Abmaj7 Db7 Cmaj7", "C major")
        by = {row["chord"]: row for row in r["chords"]}
        self.assertIn("V7/ii", by["A7"]["explanation"][0])
        self.assertIn("borrowed", by["Abmaj7"]["explanation"][0])
        self.assertEqual(by["Abmaj7"]["numeral"], "bVImaj7")
        self.assertIn("tritone", by["Db7"]["explanation"][0])

    def test_minor_numerals(self):
        r = self.rows("Fm9 Bbm9 Eb13 Abmaj9", "F minor")
        self.assertEqual([x["numeral"] for x in r["chords"]], ["i9", "iv9", "bVII13", "bIIImaj9"])

    def test_key_guess(self):
        self.assertEqual(self.rows("Dm7 G7 Cmaj7")["key"], "C major")
        self.assertEqual(self.rows("Cm9 Fm9 Abmaj7 G7alt")["key"], "C minor")

    def test_diatonic(self):
        names_ = [d["chord"] for d in diatonic_chords(*parse_key("C major"))]
        self.assertEqual(names_, ["Cmaj7", "Dm7", "Em7", "Fmaj7", "G7", "Am7", "Bm7b5"])


class Files(unittest.TestCase):
    def test_midi_roundtrip(self):
        clip = {"bpm": 172, "tracks": [{"name": "Keys", "notes": [
            {"pitch": 56, "start_time": 0, "duration": 4, "velocity": 80},
            {"pitch": 60, "start_time": 0, "duration": 4, "velocity": 80},
            {"pitch": 61, "start_time": 4.5, "duration": 0.25, "velocity": 100}]}]}
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "x.mid")
            midi_io.write_midi(clip, p)
            back = midi_io.read_midi(p)
        self.assertEqual(back["bpm"], 172)
        got = [(n["pitch"], n["start_time"], n["duration"], n["velocity"]) for n in back["tracks"][0]["notes"]]
        self.assertEqual(got, [(56, 0, 4, 80), (60, 0, 4, 80), (61, 4.5, 0.25, 100)])

    def test_mcp_shapes(self):
        raw = {"result": json.dumps({"notes": [{"pitch": 60, "start_time": 0, "duration": 1, "velocity": 90,
                                                "mute": False}, {"pitch": 64, "start_time": 0, "duration": 1,
                                                                 "velocity": 90, "mute": True}]})}
        self.assertEqual([n["pitch"] for n in load_notes(raw)], [60])
        self.assertEqual(load_notes([{"pitch": 50, "start": 1, "duration": 2}])[0]["start_time"], 1.0)

    def test_segments(self):
        notes = load_notes([{"pitch": p, "start_time": 0, "duration": 4} for p in (56, 60, 63, 67)] +
                           [{"pitch": p, "start_time": 4.01, "duration": 4} for p in (56, 60, 61, 65)])
        segs = segment_notes(notes)
        self.assertEqual(len(segs), 2)
        self.assertAlmostEqual(segs[1]["start"], 4.01)


class CLI(unittest.TestCase):
    def run_mc(self, *args):
        return subprocess.run(MC + list(args), capture_output=True, text=True)

    def test_check_exit_codes(self):
        self.assertEqual(self.run_mc("check", "Cm9", "51", "55", "58", "62").returncode, 0)
        self.assertEqual(self.run_mc("check", "Cm9", "51", "52", "58", "62").returncode, 1)

    def test_voice_then_validate(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "c.json")
            r = self.run_mc("voice", "Fm9 Bbm9 Eb13 Abmaj9", "--style", "rhodes", "--out", out,
                            "--mid", os.path.join(d, "c.mid"))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue(os.path.exists(os.path.join(d, "c-bass.mid")))
            ok = self.run_mc("validate", out, "--track", "0", "--chords", "Fm9 Bbm9 Eb13 Abmaj9")
            self.assertEqual(ok.returncode, 0, ok.stdout)
            bad = self.run_mc("validate", out, "--track", "0", "--chords", "Fm7 Bbm7 Eb7 Abmaj7")
            self.assertEqual(bad.returncode, 1)

    def test_json_mode_and_errors(self):
        r = self.run_mc("--json", "identify", "F2", "A2", "C3", "E3")
        self.assertEqual(json.loads(r.stdout)["candidates"][0]["name"], "Fmaj7")
        self.assertEqual(self.run_mc("spell", "Hmaj7").returncode, 2)


class Regressions(unittest.TestCase):
    """Issues found in independent review."""

    def run_mc(self, *args):
        return subprocess.run(MC + list(args), capture_output=True, text=True)

    def write(self, d, name, obj):
        p = os.path.join(d, name)
        with open(p, "w") as f:
            json.dump(obj, f)
        return p

    def test_pushed_chord_and_held_notes(self):
        with tempfile.TemporaryDirectory() as d:
            fm9 = [56, 60, 63, 67]
            bbm9 = [56, 60, 61, 65]
            pushed = [{"pitch": p, "start_time": 0, "duration": 3.5} for p in fm9] + \
                     [{"pitch": p, "start_time": 3.5, "duration": 4.5} for p in bbm9]
            r = self.run_mc("validate", self.write(d, "p.json", pushed), "--chords", "Fm9 Bbm9")
            self.assertEqual(r.returncode, 0, r.stdout)
            self.assertIn("pushed", r.stdout)
            held = [{"pitch": p, "start_time": 0, "duration": 4} for p in fm9[:3]] + \
                   [{"pitch": 67, "start_time": 0, "duration": 8}] + \
                   [{"pitch": p, "start_time": 4, "duration": 4} for p in (56, 60, 61)]
            r = self.run_mc("validate", self.write(d, "h.json", held), "--chords", "Fm9 E7")
            self.assertEqual(r.returncode, 1, r.stdout)

    def test_mcp_wrappers(self):
        notes = [{"pitch": 60, "start_time": 0, "duration": 1}]
        for wrapped in [{"result": {"notes": notes}}, {"status": "success", "result": {"notes": notes}},
                        {"content": [{"type": "text", "text": json.dumps({"notes": notes})}]},
                        {"result": json.dumps({"clip": {"notes": notes}})}]:
            self.assertEqual(load_notes(wrapped)[0]["pitch"], 60, wrapped)
        with self.assertRaises(TheoryError):
            load_notes({"notes": []})

    def test_eleven_chords_drop_the_third(self):
        for sym in ("C11", "F11"):
            ch = parse_chord(sym)
            v = voice_progression([ch], "rhodes")[0]
            self.assertNotIn((ch.root.pc + 4) % 12, {m % 12 for m in v}, sym)

    def test_sharp9_above_third(self):
        ch = parse_chord("G7#9")
        v = voice_progression([ch], "rhodes")[0]
        labels = [ch.tone_for_pc(m % 12).label for m in v]
        self.assertLess(labels.index("3"), labels.index("#9"), v)

    def test_explicit_bass_excludes_rootless(self):
        names_ = [d["name"] for d in identify([56, 60, 63, 67], bass=29)]
        self.assertEqual(names_[0], "Fm9")
        self.assertFalse(any(n.startswith(("Bb13", "Db")) for n in names_), names_)

    def test_pitch_classes_and_groups(self):
        r = self.run_mc("--json", "identify", "Ab", "C", "Eb", "G")
        self.assertEqual(json.loads(r.stdout)["candidates"][0]["name"], "Abmaj7")
        r = self.run_mc("--json", "identify", "41 56 60 63 67 | 46 56 60 61 65")
        self.assertEqual([g["candidates"][0]["name"] for g in json.loads(r.stdout)["groups"]], ["Fm9", "Bbm9"])

    def test_movement_is_semitones(self):
        from theory_core import movement_report
        self.assertEqual(movement_report((56, 60, 63, 67), (56, 60, 61, 65))["semitones"], 4)

    def test_hits_repeat_per_bar(self):
        r = self.run_mc("--json", "voice", "Am9:8", "--style", "stab", "--hits", "0", "--hit-len", "0.5")
        starts = sorted({n["start_time"] for n in json.loads(r.stdout)["clip"]["tracks"][0]["notes"]})
        self.assertEqual(starts, [0, 4])

    def test_bad_pitch_rejected_on_write(self):
        with tempfile.TemporaryDirectory() as d:
            p = self.write(d, "bad.json", {"tracks": [{"name": "x", "notes": [{"pitch": 130, "start_time": 0,
                                                                                 "duration": 1}]}]})
            self.assertEqual(self.run_mc("midi-write", p, os.path.join(d, "o.mid")).returncode, 2)

    def test_unicode_increment(self):
        self.assertEqual(parse_chord("C∆7").pcs(), parse_chord("Cmaj7").pcs())

    def test_user_bassline(self):
        with tempfile.TemporaryDirectory() as d:
            bass = [{"pitch": 41, "start_time": 0, "duration": 3}, {"pitch": 45, "start_time": 3, "duration": 1},
                    {"pitch": 46, "start_time": 4, "duration": 4}]
            r = self.run_mc("--json", "voice", "Fm9 Bbm9", "--bass-file", self.write(d, "b.json", bass))
            out = json.loads(r.stdout)
            self.assertEqual([v["bass_midi"] for v in out["voicings"]], [41, 46])
            self.assertEqual(len(out["clip"]["tracks"]), 1)  # the user's bass isn't duplicated
            self.assertTrue(all(v["midi"][0] - v["bass_midi"] >= 12 for v in out["voicings"]))


if __name__ == "__main__":
    unittest.main()
