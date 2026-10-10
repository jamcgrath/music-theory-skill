"""Deterministic music-theory helpers for the music-composer skill.

Standard library only. Everything here is checkable arithmetic: note and chord
spelling, chord identification, voicing generation/validation, scale and key
lookups. Musical *judgement* (which chord, which colour, which variation) is
left to the model using the skill; this module makes sure the notes it writes
are the notes it says they are.

Octave conventions
------------------
MIDI note numbers are the ground truth. Names are rendered in one of two
conventions:

* ``ableton`` (default): C3 = MIDI 60, matching Ableton Live's piano roll.
* ``spn``: scientific pitch notation, C4 = MIDI 60.
"""
from __future__ import annotations

import itertools
import re
from dataclasses import dataclass, field

# --------------------------------------------------------------------------
# Notes and spelling
# --------------------------------------------------------------------------

LETTERS = "CDEFGAB"
NAT = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
ACC_STR = {-2: "bb", -1: "b", 0: "", 1: "#", 2: "##"}
ACC_PARSE = {"": 0, "b": -1, "♭": -1, "bb": -2, "𝄫": -2, "#": 1, "♯": 1, "##": 2, "x": 2, "𝄪": 2}
CONVENTIONS = {"ableton": 2, "spn": 1}  # midi = (octave + k) * 12 + pc

FLAT_NAMES = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]
SHARP_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


class TheoryError(ValueError):
    """Raised for input the module cannot interpret."""


@dataclass(frozen=True)
class Spelled:
    letter: str
    acc: int = 0

    @property
    def pc(self) -> int:
        return (NAT[self.letter] + self.acc) % 12

    def __str__(self) -> str:
        return self.letter + ACC_STR[self.acc]


NOTE_RE = re.compile(r"^([A-Ga-g])(##|bb|#|b|x|♯|♭|𝄪|𝄫)?(-?\d+)?$")


def parse_note(text: str) -> tuple[Spelled, int | None]:
    m = NOTE_RE.match(text.strip())
    if not m:
        raise TheoryError(f"Not a note name: {text!r}")
    letter, acc, octave = m.groups()
    return Spelled(letter.upper(), ACC_PARSE[acc or ""]), (int(octave) if octave is not None else None)


def note_to_midi(text: str | int, convention: str = "ableton") -> int:
    """'Eb3' -> 63 (Ableton) / 51 (SPN). Plain integers pass through."""
    if isinstance(text, int):
        midi = text
    elif re.fullmatch(r"\s*\d{1,3}\s*", str(text)):
        midi = int(text)
    else:
        sp, octave = parse_note(str(text))
        if octave is None:
            raise TheoryError(f"Note {text!r} needs an octave (e.g. {text}3) or a MIDI number")
        midi = (octave + CONVENTIONS[convention]) * 12 + NAT[sp.letter] + sp.acc
    if not 0 <= midi <= 127:
        raise TheoryError(f"MIDI note out of range 0-127: {text!r} -> {midi}")
    return midi


def default_spelling(pc: int, prefer_flats: bool = True) -> Spelled:
    name = (FLAT_NAMES if prefer_flats else SHARP_NAMES)[pc % 12]
    return Spelled(name[0], ACC_PARSE[name[1:]])


def midi_octave(midi: int, sp: Spelled, convention: str = "ableton") -> int:
    return (midi - NAT[sp.letter] - sp.acc) // 12 - CONVENTIONS[convention]


def midi_name(midi: int, sp: Spelled | None = None, convention: str = "ableton", prefer_flats: bool = True) -> str:
    if sp is None or sp.pc != midi % 12:
        sp = default_spelling(midi % 12, prefer_flats)
    return f"{sp}{midi_octave(midi, sp, convention)}"


def spell_degree(root: Spelled, degree: int, semis: int) -> Spelled:
    """Spell the note `semis` above `root` as scale degree `degree` (1-13)."""
    letter = LETTERS[(LETTERS.index(root.letter) + degree - 1) % 7]
    target = (root.pc + semis) % 12
    acc = (target - NAT[letter]) % 12
    if acc > 6:
        acc -= 12
    if abs(acc) > 2:
        return default_spelling(target)
    return Spelled(letter, acc)


INTERVAL_SHORT = ["P1", "m2", "M2", "m3", "M3", "P4", "TT", "P5", "m6", "M6", "m7", "M7"]
INTERVAL_LONG = ["unison", "minor 2nd", "major 2nd", "minor 3rd", "major 3rd", "perfect 4th",
                 "tritone", "perfect 5th", "minor 6th", "major 6th", "minor 7th", "major 7th"]
COMPOUND = {12: "octave", 13: "minor 9th", 14: "major 9th", 15: "minor 10th", 16: "major 10th",
            17: "perfect 11th", 18: "augmented 11th", 19: "perfect 12th", 20: "minor 13th",
            21: "major 13th", 22: "minor 14th", 23: "major 14th", 24: "two octaves"}


def interval_name(semis: int) -> str:
    semis = abs(semis)
    if semis < 12:
        return INTERVAL_LONG[semis]
    if semis in COMPOUND:
        return COMPOUND[semis]
    return f"{INTERVAL_LONG[semis % 12]} + {semis // 12} octaves"


# --------------------------------------------------------------------------
# Chords
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Tone:
    label: str      # "1", "b3", "3", "5", "b7", "9", "#11", "13", ...
    degree: int     # scale-degree number used for spelling
    semis: int      # semitones above the root (may exceed 12)
    role: str       # "root" | "required" | "optional" | "alt"


@dataclass
class Chord:
    symbol: str
    root: Spelled
    suffix: str
    tones: list[Tone]
    family: str
    bass: Spelled | None = None
    notes: list[str] = field(default_factory=list)

    @property
    def root_pc(self) -> int:
        return self.root.pc

    @property
    def bass_pc(self) -> int:
        return self.bass.pc if self.bass else self.root.pc

    def pcs(self) -> set[int]:
        return {(self.root.pc + t.semis) % 12 for t in self.tones}

    def tone_for_pc(self, pc: int) -> Tone | None:
        for t in self.tones:
            if (self.root.pc + t.semis) % 12 == pc % 12:
                return t
        return None

    def spell(self, tone: Tone) -> Spelled:
        return spell_degree(self.root, tone.degree, tone.semis)

    def has_seventh(self) -> bool:
        return any(t.degree in (6, 7) for t in self.tones)

    def name(self) -> str:
        base = f"{self.root}{self.suffix}"
        if self.bass and self.bass.pc != self.root.pc:
            base += f"/{self.bass}"
        return base


CHORD_RE = re.compile(r"^\s*([A-Ga-g])(##|bb|#|b|♯|♭)?(.*?)\s*$")
TOKEN_RE = re.compile(r"mmaj|maj|m|dim|aug|sus2|sus4|sus|alt|add[b#]?\d+|no\d+|omit\d+|[b#]\d+|\d+")


def normalise_suffix(q: str) -> str:
    q = q.replace("♭", "b").replace("♯", "#").replace("−", "-").replace("–", "-")
    q = q.replace("6/9", "69").replace("6add9", "69")
    q = q.replace("(", " ").replace(")", " ").replace(",", " ")
    q = q.replace("Δ", "maj").replace("∆", "maj").replace("^", "maj")
    q = q.replace("ø7", "m7b5").replace("ø", "m7b5")
    q = q.replace("°7", "dim7").replace("°", "dim")
    q = re.sub(r"^o7", "dim7", q)
    q = re.sub(r"^o(?=$|\s)", "dim", q)
    q = re.sub(r"^(?:MAJ|Maj|Ma|M)(?!in|i)", "maj", q)
    q = re.sub(r"M(?=7|9|11|13)", "maj", q)
    q = q.lower()
    q = q.replace("major", "maj").replace("minor", "m")
    q = re.sub(r"^(?:min|mi)(?!n)", "m", q)
    q = re.sub(r"^ma(?=\d|$)", "maj", q)
    q = re.sub(r"^-", "m", q)
    q = re.sub(r"^\+", "aug", q)
    q = re.sub(r"\+(\d)", r"#\1", q)
    q = re.sub(r"(?<=\d)-(\d)", r"b\1", q)
    q = re.sub(r"(?<=7)\+$", "#5", q)
    q = q.replace(" ", "")
    return q


def _parse_bass(rest: str) -> tuple[str, Spelled | None]:
    # A trailing '/X' where X is a note name is a slash bass. '6/9' was normalised earlier.
    m = re.match(r"^(.*)/([A-Ga-g](?:##|bb|#|b|♯|♭)?)\s*$", rest)
    if m and not re.fullmatch(r".*\d", m.group(2)):
        sp, _ = parse_note(m.group(2))
        return m.group(1), sp
    return rest, None


def parse_chord(symbol: str) -> Chord:
    m = CHORD_RE.match(symbol)
    if not m:
        raise TheoryError(f"Not a chord symbol: {symbol!r}")
    letter, acc, rest = m.groups()
    root = Spelled(letter.upper(), ACC_PARSE[acc or ""])
    rest = rest.replace("6/9", "69")
    rest, bass = _parse_bass(rest)
    q = normalise_suffix(rest)
    tokens = TOKEN_RE.findall(q)
    if "".join(tokens) != q:
        raise TheoryError(f"Unrecognised chord suffix {rest!r} in {symbol!r}")

    third: int | None = 4
    fifth = 7
    maj7 = False
    dim = aug = alt = power = False
    sus: int | None = None
    sixth = False
    six_nine = False
    ext: int | None = None
    alts: dict[str, int] = {}
    adds: list[str] = []
    omit: set[int] = set()

    for i, tok in enumerate(tokens):
        if tok == "m":
            third = 3
        elif tok == "mmaj":
            third, maj7 = 3, True
        elif tok == "maj":
            maj7 = True
        elif tok == "dim":
            third, fifth, dim = 3, 6, True
        elif tok == "aug":
            fifth, aug = 8, True
        elif tok.startswith("sus"):
            sus = 2 if tok == "sus2" else 4
        elif tok == "alt":
            alt = True
        elif tok.startswith("add"):
            adds.append(tok[3:])
        elif tok.startswith("no") or tok.startswith("omit"):
            omit.add(int(re.sub(r"\D", "", tok)))
        elif tok[0] in "b#":
            num = int(tok[1:])
            mapping = {("b", 6): "b13", ("#", 4): "#11"}
            label = mapping.get((tok[0], num), tok)
            if label not in ("b5", "#5", "b9", "#9", "#11", "b13", "13", "b6"):
                raise TheoryError(f"Unsupported alteration {tok!r} in {symbol!r}")
            alts[label] = 1
        else:
            num = int(tok)
            if num == 5 and len(tokens) == 1:
                power = True
            elif num == 6:
                sixth = True
            elif num == 69:
                sixth = six_nine = True
            elif num in (7, 9, 11, 13) and ext is None:
                ext = num
            else:
                raise TheoryError(f"Unexpected number {tok!r} in {symbol!r}")

    tones: list[Tone] = [Tone("1", 1, 0, "root")]
    if power:
        tones.append(Tone("5", 5, 7, "required"))
        return Chord(symbol, root, rest, tones, "power", bass)

    if (alts.keys() & {"b9", "#9", "#11", "b13"}) and ext is None and not sixth:
        ext = 7
    if alt and ext is None:
        ext = 7

    # Third / suspension
    if sus == 2:
        tones.append(Tone("2", 2, 2, "required"))
    elif sus == 4:
        tones.append(Tone("4", 4, 5, "required"))
    elif third is not None and 3 not in omit:
        role = "required"
        if ext == 11 and third == 4:
            role = "optional"  # dominant/major 11: the 3rd clashes with the 11 and is usually dropped
        tones.append(Tone("b3" if third == 3 else "3", 3, third, role))

    # Fifth
    if "b5" in alts or dim:
        tones.append(Tone("b5", 5, 6, "required"))
    elif "#5" in alts or aug:
        tones.append(Tone("#5", 5, 8, "required"))
    elif 5 not in omit and not alt:
        tones.append(Tone("5", 5, 7, "optional"))

    if sixth:
        tones.append(Tone("6", 6, 9, "required"))
    if six_nine:
        tones.append(Tone("9", 9, 14, "required"))

    if ext is not None:
        if dim and ext == 7 and not maj7:
            tones.append(Tone("bb7", 7, 9, "required"))
        elif maj7:
            tones.append(Tone("7", 7, 11, "required"))
        else:
            tones.append(Tone("b7", 7, 10, "required"))
        if alt:
            tones += [Tone("b9", 9, 13, "alt"), Tone("#9", 9, 15, "alt"),
                      Tone("#11", 11, 18, "alt"), Tone("b13", 13, 20, "alt")]
        else:
            if ext >= 9 and not ({"b9", "#9"} & alts.keys()):
                tones.append(Tone("9", 9, 14, "required" if ext == 9 else "optional"))
            if ext >= 11 and "#11" not in alts:
                if ext == 11:
                    tones.append(Tone("11", 11, 17, "required"))
                elif third == 3 or sus:
                    tones.append(Tone("11", 11, 17, "optional"))
                # major-3rd 13 chords: natural 11 omitted (it clashes a minor 9th above the 3rd)
            if ext == 13 and "b13" not in alts:
                tones.append(Tone("13", 13, 21, "required"))

    for label, semis, degree in (("b9", 13, 9), ("#9", 15, 9), ("#11", 18, 11), ("b13", 20, 13)):
        if label in alts and not alt:
            tones.append(Tone(label, degree, semis, "required"))

    for a in adds:
        acc = a[0] if a[0] in "b#" else ""
        num = int(a.lstrip("b#"))
        base = {2: 2, 4: 5, 6: 9, 9: 14, 11: 17, 13: 21}.get(num)
        if base is None:
            raise TheoryError(f"Unsupported add tone 'add{a}' in {symbol!r}")
        semis = base + (-1 if acc == "b" else 1 if acc == "#" else 0)
        tones.append(Tone(f"{acc}{num}", num, semis, "required"))

    # A b13 makes a natural 5 a semitone clash in most voicings; keep it optional only.
    if "b13" in alts or alt:
        tones = [t for t in tones if t.label != "5"]

    # Deduplicate by pitch class, keeping the most important role.
    rank = {"required": 0, "alt": 1, "root": 2, "optional": 3}
    seen: dict[int, Tone] = {}
    for t in tones:
        pc = t.semis % 12
        if pc not in seen or rank[t.role] < rank[seen[pc].role]:
            seen[pc] = t
    tones = sorted(seen.values(), key=lambda t: t.semis)

    labels = {t.label for t in tones}
    if sus is not None:
        family = "dominant-sus" if "b7" in labels else "sus"
    elif third == 3 and "b5" in labels and "bb7" in labels:
        family = "diminished"
    elif third == 3 and "b5" in labels and "b7" in labels:
        family = "half-diminished"
    elif third == 3 and "b5" in labels:
        family = "diminished"
    elif third == 3:
        family = "minor-major" if "7" in labels else "minor"
    elif "b7" in labels:
        family = "dominant"
    elif aug:
        family = "augmented"
    else:
        family = "major"
    return Chord(symbol, root, rest, tones, family, bass)


def chord_from_pc(root_pc: int, suffix: str, bass_pc: int | None = None) -> Chord:
    """Build a chord on a pitch class, choosing the root spelling with the fewest accidentals."""
    best = None
    for prefer_flats in (True, False):
        sp = default_spelling(root_pc, prefer_flats)
        ch = parse_chord(f"{sp}{suffix}")
        cost = sum(abs(ch.spell(t).acc) + (2 if abs(ch.spell(t).acc) == 2 else 0) for t in ch.tones)
        if best is None or cost < best[0]:
            best = (cost, ch)
    ch = best[1]
    if bass_pc is not None and bass_pc != root_pc:
        tone = ch.tone_for_pc(bass_pc)
        ch.bass = ch.spell(tone) if tone else default_spelling(bass_pc, ch.root.acc <= 0)
    return ch


def describe_chord(ch: Chord) -> dict:
    out = []
    for t in ch.tones:
        out.append({"label": t.label, "note": str(ch.spell(t)), "pc": (ch.root.pc + t.semis) % 12,
                    "role": t.role, "interval": interval_name(t.semis)})
    d = {"symbol": ch.symbol, "name": ch.name(), "root": str(ch.root), "family": ch.family, "tones": out}
    if ch.bass and ch.bass.pc != ch.root.pc:
        bt = ch.tone_for_pc(ch.bass.pc)
        d["bass"] = {"note": str(ch.bass),
                     "relation": f"chord tone ({bt.label})" if bt else
                     f"non-chord bass, {interval_name((ch.bass.pc - ch.root.pc) % 12)} above the root"}
        if not bt:
            whole = identify([60 + (ch.root.pc + t.semis) % 12 for t in ch.tones], bass=36 + ch.bass.pc, limit=1)
            if whole and whole[0]["root_pc"] != ch.root.pc:
                d["bass"]["sounds_as"] = whole[0]["name"]
    return d


# --------------------------------------------------------------------------
# Identification
# --------------------------------------------------------------------------

TEMPLATE_SUFFIXES = [
    "", "m", "dim", "aug", "sus2", "sus4", "5", "6", "m6", "69", "m69",
    "7", "maj7", "m7", "m7b5", "dim7", "mmaj7", "7sus4", "9sus4", "13sus4", "aug7", "maj7#5",
    "7b5", "7#5", "add9", "madd9", "9", "maj9", "m9", "mmaj9", "11", "m11", "13", "maj13", "m13",
    "7b9", "7#9", "7#11", "7b13", "9#11", "13#11", "13b9", "7b9b13", "7#9b13", "7#9#5", "7b9#11",
    "maj7#11", "maj9#11", "maj13#11", "m7add11", "m9b5", "6sus4"
]
_TEMPLATES: list[tuple[str, frozenset, frozenset, frozenset, float]] | None = None


def _templates():
    global _TEMPLATES
    if _TEMPLATES is None:
        out = []
        for suf in TEMPLATE_SUFFIXES:
            try:
                ch = parse_chord("C" + suf)
            except TheoryError:
                continue
            full = frozenset(t.semis % 12 for t in ch.tones)
            req = frozenset(t.semis % 12 for t in ch.tones if t.role == "required")
            opt = frozenset(t.semis % 12 for t in ch.tones if t.role == "optional")
            complexity = 0.05 * len(full) + 0.3 * len(re.findall(r"[b#]\d", suf))
            out.append((suf, full, req, opt, complexity))
        _TEMPLATES = out
    return _TEMPLATES


def identify(midis: list[int], bass: int | None = None, limit: int = 6) -> list[dict]:
    """Rank chord interpretations of a note set. The lowest note is treated as the bass."""
    allm = sorted(set(midis) | ({bass} if bass is not None else set()))
    if not allm:
        return []
    bass_pc = (bass if bass is not None else allm[0]) % 12
    pcs = {m % 12 for m in allm}
    if len(pcs) < 3:
        return []
    results = []
    for strict in (True, False):
        for r in range(12):
            rel = {(p - r) % 12 for p in pcs}
            for suf, full, req, opt, complexity in _templates():
                extras = rel - full
                if strict and extras:
                    continue
                if not strict and len(extras) != 1:
                    continue
                if req - rel:
                    continue
                score = complexity
                rootless = r not in pcs
                if rootless and bass is not None:
                    continue  # an explicit bass note fixes the bottom; readings needing another root don't apply
                if rootless:
                    if not any(x in full for x in (9, 10, 11)) or len(pcs) < 3:
                        continue
                    score += 2.5
                inversion = (not rootless) and r != bass_pc
                if inversion:
                    score += 1.0
                missing_opt = (opt - rel)
                score += 0.4 * len(missing_opt)
                if not strict:
                    score += 3.0
                if suf in ("5",):
                    continue
                ch = chord_from_pc(r, suf, None if (rootless or not inversion) else bass_pc)
                note = []
                if rootless:
                    note.append(f"rootless — {ch.root} is not present; works if the bass plays {ch.root}")
                if inversion:
                    bt = ch.tone_for_pc(bass_pc)
                    note.append(f"inversion: {bt.label if bt else '?'} in the bass")
                if missing_opt:
                    labels = [ch.tone_for_pc((r + x) % 12).label for x in sorted(missing_opt)]
                    note.append("omits " + ", ".join(labels))
                if extras:
                    note.append("one note outside the chord: " +
                                ", ".join(FLAT_NAMES[(r + x) % 12] for x in extras))
                results.append({"name": ch.name(), "score": round(score, 2), "rootless": rootless,
                                "inversion": inversion, "notes": "; ".join(note), "suffix": suf,
                                "root_pc": r})
        if results:
            break
    results.sort(key=lambda d: (d["score"], d["name"]))
    seen, out = set(), []
    for d in results:
        if d["name"] in seen:
            continue
        seen.add(d["name"])
        out.append(d)
    return out[:limit]


# --------------------------------------------------------------------------
# Voicing checks
# --------------------------------------------------------------------------

# Lowest recommended bottom note (MIDI) for each interval < an octave (classic low-interval limits).
LOW_INTERVAL_LIMIT = {1: 52, 2: 51, 3: 48, 4: 46, 5: 46, 6: 47, 7: 34, 8: 43, 9: 41, 10: 41, 11: 41}


def low_interval_violations(midis: list[int]) -> list[tuple[int, int]]:
    s = sorted(midis)
    bad = []
    for lo, hi in zip(s, s[1:]):
        iv = hi - lo
        if 0 < iv < 12 and lo < LOW_INTERVAL_LIMIT[iv]:
            bad.append((lo, hi))
    return bad


def hand_split(midis: list[int]) -> str:
    s = sorted(midis)
    if not s:
        return ""
    if s[-1] - s[0] <= 12:
        return "one hand"
    best = None
    for i in range(1, len(s)):
        lh, rh = s[:i], s[i:]
        if lh[-1] - lh[0] <= 12 and rh[-1] - rh[0] <= 12:
            score = abs(len(lh) - len(rh)) + max(lh[-1] - lh[0], rh[-1] - rh[0]) / 12
            if best is None or score < best[0]:
                best = (score, len(lh), len(rh))
    if best:
        return f"two hands (LH {best[1]} notes / RH {best[2]} notes)"
    return "wider than two comfortable hand spans — fine to program, hard to play"


def check_voicing(ch: Chord, midis: list[int], bass: int | None = None, convention: str = "ableton") -> dict:
    s = sorted(midis)
    roles, extras = [], []
    present = set()
    for m in s:
        t = ch.tone_for_pc(m % 12)
        if t is None:
            extras.append(m)
            roles.append({"midi": m, "name": midi_name(m, None, convention), "tone": None})
        else:
            present.add(t.label)
            roles.append({"midi": m, "name": midi_name(m, ch.spell(t), convention), "tone": t.label})
    bass_pc = bass % 12 if bass is not None else None
    if bass_pc is not None:
        bt = ch.tone_for_pc(bass_pc)
        if bt:
            present.add(bt.label)
    missing = [t.label for t in ch.tones if t.role == "required" and t.label not in present]
    alt_tones = [t for t in ch.tones if t.role == "alt"]
    if alt_tones and not any(t.label in present for t in alt_tones):
        missing.append("(one altered tension: b9/#9/#11/b13)")
    warnings = []
    if "1" not in present:
        warnings.append(f"rootless: {ch.root} not in the voicing — the bass (or another part) should play it")
    if ch.bass and bass_pc is None and ch.bass.pc != ch.root.pc and s and s[0] % 12 != ch.bass.pc:
        warnings.append(f"slash chord: lowest sounding note should be {ch.bass}")
    if bass is not None and bass_pc != ch.bass_pc:
        bt = ch.tone_for_pc(bass_pc)
        warnings.append(f"bass plays {midi_name(bass, None, convention)} "
                        f"({'chord tone ' + bt.label if bt else 'non-chord tone'}), not {ch.bass or ch.root}")
    lil = low_interval_violations(s + ([bass] if bass is not None else []))
    for lo, hi in lil:
        warnings.append(f"muddy: {interval_name(hi - lo)} between {midi_name(lo, None, convention)} and "
                        f"{midi_name(hi, None, convention)} is below the low-interval limit")
    if s and s[0] < 48:
        warnings.append(f"lowest chord note {midi_name(s[0], None, convention)} (MIDI {s[0]}) is in the "
                        "low-mid/bass register; risks clashing with the bassline")
    if bass is not None and s and s[0] - bass < 12:
        warnings.append("chord sits within an octave of the bass note")
    ok = not extras and not missing
    return {"chord": ch.name(), "ok": ok, "notes": roles, "missing_required": missing,
            "extra_notes": [midi_name(m, None, convention) + f" ({m})" for m in extras],
            "span_semitones": (s[-1] - s[0]) if s else 0, "playability": hand_split(s),
            "warnings": warnings}


# --------------------------------------------------------------------------
# Voicing generation
# --------------------------------------------------------------------------

STYLES = {
    # voices, register window (MIDI), max span, centre, spread, include root, allow doubling, velocity
    "rhodes": dict(voices=4, low=50, high=79, span=12, center=62, spread="close", root=False, double=False, vel=80),
    "piano":  dict(voices=5, low=45, high=84, span=22, center=63, spread="open", root=True, double=True, vel=80),
    "pad":    dict(voices=4, low=48, high=86, span=24, center=66, spread="open", root=False, double=True, vel=70),
    "stab":   dict(voices=3, low=55, high=79, span=12, center=66, spread="close", root=False, double=False, vel=100),
    "organ":  dict(voices=4, low=48, high=79, span=14, center=62, spread="close", root=True, double=True, vel=85),
    "pluck":  dict(voices=3, low=60, high=88, span=12, center=72, spread="close", root=False, double=False, vel=90),
}

ALT_PRIORITY = {"#9": 0.5, "b13": 0.55, "b9": 0.7, "#11": 0.8}


def select_tones(ch: Chord, voices: int, include_root: bool, allow_double: bool,
                 force_pcs: set[int] | None = None) -> list[Tone]:
    triad_like = not ch.has_seventh() and ch.family not in ("dominant-sus",)

    def prio(t: Tone) -> float:
        if t.role == "root":
            return -1 if include_root else (0.5 if triad_like else 3)
        if t.role == "required":
            return 0
        if t.role == "alt":
            return ALT_PRIORITY.get(t.label, 0.9)
        if t.label == "5":
            return 2
        return 1

    labels = {t.label for t in ch.tones}
    # a rootless style never re-adds the root on 7th chords; an optional 3rd is dropped under a natural 11
    pool = [t for t in ch.tones if prio(t) < 3 and not (t.label == "3" and t.role == "optional" and "11" in labels)]
    ranked = sorted(pool, key=lambda t: (prio(t), t.semis))
    required = [t for t in ranked if prio(t) <= 0]
    n = max(voices, len(required))
    chosen = ranked[:n]
    if ch.family == "power":
        chosen = ranked
    for pc in force_pcs or ():
        t = ch.tone_for_pc(pc)
        if t is not None and t not in chosen:
            if len(chosen) >= voices:
                # make room by dropping the least important non-required tone
                for drop in reversed(chosen):
                    if prio(drop) > 0 and (drop.semis % 12) not in (force_pcs or ()):
                        chosen.remove(drop)
                        break
            chosen.append(t)
    if allow_double and len(chosen) < voices:
        root = next(t for t in ch.tones if t.role == "root")
        fifth = next((t for t in ch.tones if t.label == "5"), None)
        # with a major 7th, a doubled root lands a semitone or b9 above it — double the 5th first
        has_maj7 = any(t.label == "7" for t in chosen)
        for extra in ([fifth, root] if has_maj7 and fifth is not None else [root, fifth, root]):
            if extra is not None and len(chosen) < voices:
                chosen.append(extra)
    return chosen


def _shape_cost(ch: Chord, v: tuple[int, ...], style: dict, center: float, bass: int | None = None) -> float:
    gaps = [b - a for a, b in zip(v, v[1:])]
    cost = 0.0
    if bass is not None and v[0] - bass < 12:
        cost += 3.0
    if style["spread"] == "close":
        cost += sum(max(0, g - 7) for g in gaps) * 0.6
    else:
        if gaps:
            cost += max(0, 5 - gaps[0]) * 0.5
        cost += sum(max(0, 3 - g) * 0.3 for g in gaps[: len(gaps) // 2 + 1])
        cost += sum(max(0, g - 12) * 0.5 for g in gaps)
    labels = [ch.tone_for_pc(m % 12).label for m in v]
    allow_b9 = any(lbl in ("b9", "#11", "b13", "#9") for lbl in labels) or ch.family == "diminished"
    for i in range(len(v)):
        for j in range(i + 1, len(v)):
            iv = v[j] - v[i]
            if iv % 12 == 1 and iv > 12 and not allow_b9:
                cost += 2.0
            if iv == 1:
                cost += 1.0 if (j == len(v) - 1 or i == 0) else 0.4
    if "#9" in labels and "3" in labels and labels.index("#9") < labels.index("3"):
        cost += 1.5  # the #9 reads as a wrong note when voiced below the 3rd
    if labels and labels[-1] in ("9", "11", "#11", "13", "5", "6"):
        cost -= 0.3
    if labels and labels[-1] == "1" and style["spread"] == "close":
        cost += 0.2
    cost += abs(sum(v) / len(v) - center) * 0.15
    return cost


def _root_over_maj7(ch: Chord, v: tuple[int, ...]) -> bool:
    sevens = [m for m in v if ch.tone_for_pc(m % 12).label == "7"]
    return any(m - s in (1, 13) for s in sevens for m in v if ch.tone_for_pc(m % 12).label == "1")


def candidate_voicings(ch: Chord, style: dict, voices: int | None = None, include_root: bool | None = None,
                       center: float | None = None, keep: int = 48,
                       force_pcs: set[int] | None = None,
                       bass_bottom: bool = False, bass: int | None = None) -> list[tuple[tuple[int, ...], float]]:
    voices = voices or style["voices"]
    include_root = style["root"] if include_root is None else include_root
    center = style["center"] if center is None else center
    pinned = bool(force_pcs)  # a top-line note the user asked for
    if bass_bottom:
        include_root = True
        force_pcs = set(force_pcs or ()) | {ch.bass_pc}
    tones = select_tones(ch, voices, include_root, style["double"], force_pcs)
    options = []
    for t in tones:
        pc = (ch.root.pc + t.semis) % 12
        options.append([m for m in range(style["low"], style["high"] + 1) if m % 12 == pc])
    cands = []
    for combo in itertools.product(*options):
        if len(set(combo)) != len(combo):
            continue
        v = tuple(sorted(combo))
        if v[-1] - v[0] > style["span"]:
            continue
        if bass_bottom and v[0] % 12 != ch.bass_pc:
            continue
        if low_interval_violations(list(v)):
            continue
        cands.append((v, _shape_cost(ch, v, style, center, bass)))
    cands = sorted(set(cands), key=lambda c: c[1])
    # the root a semitone or b9 above a major 7th rubs against it; keep such voicings only as a last
    # resort, or when a pinned top note asks for it (a melody on the root over Imaj7 is ordinary)
    if pinned:
        return cands[:keep]
    clean = [c for c in cands if not _root_over_maj7(ch, c[0])]
    return (clean or cands)[:keep]


def voice_leading_cost(a: tuple[int, ...], b: tuple[int, ...]) -> float:
    if len(a) == len(b):
        move = sum(abs(x - y) for x, y in zip(a, b))
    else:
        move = (sum(min(abs(x - y) for y in a) for x in b) + sum(min(abs(x - y) for y in b) for x in a)) / 2
    top = abs(a[-1] - b[-1])
    return move + max(0, top - 4) * 0.3


def voice_progression(chords: list[Chord], style_name: str = "rhodes", voices: int | None = None,
                      include_root: bool | None = None, center: float | None = None, loop: bool = True,
                      top_line: list[int | None] | None = None,
                      warnings: list[str] | None = None, bass_bottom: bool = False,
                      basses: list[int | None] | None = None) -> list[tuple[int, ...]]:
    style = STYLES[style_name]
    all_cands = []
    if top_line and len(top_line) > len(chords) and warnings is not None:
        warnings.append(f"--top-line has {len(top_line)} entries for {len(chords)} chords; extra entries ignored")
    for i, ch in enumerate(chords):
        bass = basses[i] if basses and i < len(basses) else None
        cands = candidate_voicings(ch, style, voices, include_root, center, bass_bottom=bass_bottom, bass=bass)
        if not cands:
            # Relax: allow a wider window before giving up.
            wide = dict(style, low=style["low"] - 5, high=style["high"] + 7, span=style["span"] + 5)
            cands = candidate_voicings(ch, wide, voices, include_root, center, bass_bottom=bass_bottom, bass=bass)
        if not cands:
            raise TheoryError(f"No playable voicing found for {ch.name()} in style {style_name}")
        if top_line and i < len(top_line) and top_line[i] is not None:
            target = top_line[i]
            if target % 12 not in ch.pcs():
                if warnings is not None:
                    warnings.append(f"chord {i + 1} ({ch.name()}): requested top note is not a chord tone — "
                                    "left unconstrained (change the chord or treat that note as melody)")
            else:
                exact = [c for c in cands if c[0][-1] == target]
                if not exact:
                    more = candidate_voicings(ch, dict(style, high=max(style["high"], target)),
                                              voices, include_root, center, keep=2000, force_pcs={target % 12},
                                              bass_bottom=bass_bottom, bass=bass)
                    exact = [c for c in more if c[0][-1] == target]
                if exact:
                    cands = exact[:48]
                elif warnings is not None:
                    warnings.append(f"chord {i + 1} ({ch.name()}): no playable voicing with that top note")
        all_cands.append(cands)

    n = len(chords)
    if n == 1:
        return [all_cands[0][0][0]]
    trans = [[[voice_leading_cost(a[0], b[0]) for b in all_cands[i + 1]] for a in all_cands[i]]
             for i in range(n - 1)]
    closing = None
    if loop and n > 2:
        closing = [[voice_leading_cost(a[0], b[0]) for b in all_cands[0]] for a in all_cands[-1]]

    best_total, best_path = float("inf"), None
    starts = range(len(all_cands[0])) if closing else [None]
    for s in starts:
        cost = [(all_cands[0][j][1] if (s is None or j == s) else float("inf")) for j in range(len(all_cands[0]))]
        back = []
        for i in range(n - 1):
            nxt, bp = [], []
            for k, (vb, shape) in enumerate(all_cands[i + 1]):
                bestc, bestj = float("inf"), 0
                for j, c in enumerate(cost):
                    if c == float("inf"):
                        continue
                    t = c + trans[i][j][k]
                    if t < bestc:
                        bestc, bestj = t, j
                nxt.append(bestc + shape)
                bp.append(bestj)
            cost = nxt
            back.append(bp)
        for k, c in enumerate(cost):
            total = c + (closing[k][s] if closing else 0)
            if total < best_total:
                path = [k]
                for bp in reversed(back):
                    path.append(bp[path[-1]])
                best_total, best_path = total, list(reversed(path))
    return [all_cands[i][j][0] for i, j in enumerate(best_path)]


def bass_note(ch: Chord, low: int = 28, high: int = 43) -> int:
    pc = ch.bass_pc
    for m in range(low, high + 1):
        if m % 12 == pc:
            return m
    raise TheoryError("bass range too narrow")


def semitone_movement(a: tuple[int, ...], b: tuple[int, ...]) -> tuple[int, int]:
    """Minimal total semitones moved pairing voices one-to-one; second value = voices added/dropped."""
    small, large = (a, b) if len(a) <= len(b) else (b, a)
    if len(a) == len(b):
        return sum(abs(x - y) for x, y in zip(sorted(a), sorted(b))), 0
    best = min(sum(abs(x - y) for x, y in zip(small, perm)) for perm in itertools.permutations(large, len(small)))
    return best, len(large) - len(small)


def movement_report(a: tuple[int, ...], b: tuple[int, ...]) -> dict:
    held = sorted(set(a) & set(b))
    moved, extra = semitone_movement(a, b)
    return {"held": len(held), "semitones": moved, "voices_added_or_dropped": extra, "top_move": b[-1] - a[-1]}


# --------------------------------------------------------------------------
# Scales, keys, analysis
# --------------------------------------------------------------------------

MODES = {
    "major": [0, 2, 4, 5, 7, 9, 11], "ionian": [0, 2, 4, 5, 7, 9, 11],
    "dorian": [0, 2, 3, 5, 7, 9, 10], "phrygian": [0, 1, 3, 5, 7, 8, 10],
    "lydian": [0, 2, 4, 6, 7, 9, 11], "mixolydian": [0, 2, 4, 5, 7, 9, 10],
    "minor": [0, 2, 3, 5, 7, 8, 10], "aeolian": [0, 2, 3, 5, 7, 8, 10],
    "locrian": [0, 1, 3, 5, 6, 8, 10], "harmonic minor": [0, 2, 3, 5, 7, 8, 11],
    "melodic minor": [0, 2, 3, 5, 7, 9, 11], "phrygian dominant": [0, 1, 4, 5, 7, 8, 10],
    "lydian dominant": [0, 2, 4, 6, 7, 9, 10], "altered": [0, 1, 3, 4, 6, 8, 10],
    "major pentatonic": [0, 2, 4, 7, 9], "minor pentatonic": [0, 3, 5, 7, 10],
    "blues": [0, 3, 5, 6, 7, 10], "whole tone": [0, 2, 4, 6, 8, 10],
    "diminished half-whole": [0, 1, 3, 4, 6, 7, 9, 10], "diminished whole-half": [0, 2, 3, 5, 6, 8, 9, 11],
}
MODE_NOTES = {
    "dorian": "natural minor with a raised 6th — the soulful/jazzy minor (Rhodes vamps, acid jazz, liquid DnB)",
    "phrygian": "natural minor with a flat 2nd — dark, tense, Spanish/techy",
    "lydian": "major with a raised 4th — floating, dreamy, cinematic",
    "mixolydian": "major with a flat 7th — bluesy, funky, unresolved major",
    "minor": "natural minor (aeolian) — sad, serious, the default dark mode",
    "aeolian": "natural minor — sad, serious, the default dark mode",
    "major": "major (ionian) — bright and resolved",
    "ionian": "major — bright and resolved",
    "locrian": "flat 2nd and flat 5th — unstable; rarely a home key",
    "harmonic minor": "minor with a raised 7th — gives minor keys a strong V7; exotic/dramatic",
    "melodic minor": "minor with raised 6th and 7th — modern jazz minor, minor-major colour",
    "phrygian dominant": "5th mode of harmonic minor — Middle-Eastern/flamenco dominant",
    "lydian dominant": "major with #4 and b7 — the sound of 7#11 chords",
    "altered": "every tension altered — the sound of 7alt dominants",
    "major pentatonic": "five notes, no semitones — safe, open melody",
    "minor pentatonic": "five notes, no semitones — the basis of most riffs and basslines",
    "blues": "minor pentatonic plus the b5 'blue note'",
    "whole tone": "all whole steps — dreamy, ambiguous, augmented",
    "diminished half-whole": "symmetrical — fits 7b9/13b9 dominants",
    "diminished whole-half": "symmetrical — fits diminished 7th chords",
}
DEGREE_NAMES = {0: "1", 1: "b2", 2: "2", 3: "b3", 4: "3", 5: "4", 6: "#4/b5", 7: "5", 8: "b6", 9: "6", 10: "b7", 11: "7"}


def parse_key(text: str) -> tuple[Spelled, str]:
    text = text.strip()
    m = re.match(r"^([A-Ga-g](?:##|bb|#|b)?)\s*(.*)$", text)
    if not m:
        raise TheoryError(f"Not a key: {text!r}")
    root, _ = parse_note(m.group(1))
    mode = m.group(2).strip().lower() or "major"
    mode = {"m": "minor", "min": "minor", "maj": "major", "natural minor": "minor"}.get(mode, mode)
    if mode not in MODES:
        raise TheoryError(f"Unknown mode {mode!r}. Known: {', '.join(MODES)}")
    return root, mode


def scale_notes(root: Spelled, mode: str) -> list[Spelled]:
    steps = MODES[mode]
    if len(steps) == 7:
        return [spell_degree(root, i + 1, s) for i, s in enumerate(steps)]
    return [default_spelling((root.pc + s) % 12, prefer_flats=root.acc <= 0 and root.letter != "B")
            for s in steps]


ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII"]
MAJOR_STEPS = [0, 2, 4, 5, 7, 9, 11]


def roman_numeral(ch: Chord, tonic_pc: int) -> str:
    s = (ch.root.pc - tonic_pc) % 12
    if s in MAJOR_STEPS:
        base = ROMAN[MAJOR_STEPS.index(s)]
    else:
        base = {1: "bII", 3: "bIII", 6: "#IV", 8: "bVI", 10: "bVII"}[s]
    lower = ch.family in ("minor", "minor-major", "diminished", "half-diminished")
    if lower:
        base = base.replace("I", "i").replace("V", "v")
    suf = normalise_suffix(ch.suffix)
    if ch.family == "half-diminished":
        rest = suf.replace("m7b5", "").replace("m9b5", "9")
        suf = "ø7" + rest if "9" not in rest else "ø" + rest
    elif ch.family == "diminished":
        suf = suf.replace("dim7", "°7").replace("dim", "°")
    elif lower and suf.startswith("m"):
        suf = suf[1:]
    elif ch.family == "augmented":
        suf = suf.replace("aug", "+")
    return base + suf


FUNCTIONS_MAJOR = {0: "tonic (home)", 2: "pre-dominant", 4: "tonic substitute", 5: "pre-dominant",
                   7: "dominant (wants to resolve to I)", 9: "tonic substitute (relative minor)",
                   11: "dominant (leading-tone chord)"}
FUNCTIONS_MINOR = {0: "tonic (home)", 2: "pre-dominant", 3: "relative major (tonic colour)",
                   5: "pre-dominant", 7: "dominant", 8: "pre-dominant / tonic substitute",
                   10: "subtonic (modal dominant)"}

MOTION = {0: "same root", 1: "up a semitone", 2: "up a whole step", 3: "up a minor 3rd",
          4: "up a major 3rd", 5: "up a 4th / down a 5th — the strongest resolving motion",
          6: "tritone", 7: "up a 5th / down a 4th", 8: "down a major 3rd", 9: "down a minor 3rd",
          10: "down a whole step", 11: "down a semitone (chromatic slide)"}


def _target_numeral(target: int, tonic_pc: int, scale: set[int]) -> str:
    s = (target - tonic_pc) % 12
    base = ROMAN[MAJOR_STEPS.index(s)] if s in MAJOR_STEPS else {1: "bII", 3: "bIII", 6: "#IV", 8: "bVI", 10: "bVII"}[s]
    minor = (target + 3) % 12 in scale and (target + 4) % 12 not in scale
    return base.lower() if minor else base


def core_pcs(ch: Chord) -> set[int]:
    return {(ch.root.pc + t.semis) % 12 for t in ch.tones if t.degree in (1, 2, 3, 4, 5, 6, 7)}


def guess_keys(chords: list[Chord], limit: int = 3) -> list[dict]:
    """Score keys by how diatonic the chords' core tones are, plus light tonal-centre heuristics.

    Heuristics (deliberately small; ties are reported as ambiguity, not hidden):
    first chord on the tonic +0.08; last chord on the tonic (unless it is a dominant
    turnaround) +0.04; a V7 of the key present +0.03, or +0.08 when it resolves to the
    tonic (loop wrap included); dorian/mixolydian -0.06 so they only win when the
    evidence for that centre is strong.
    """
    n = len(chords)
    out = []
    for tonic in range(12):
        for mode in ("major", "minor", "dorian", "mixolydian"):
            scale = {(tonic + s) % 12 for s in MODES[mode]}
            fit = sum(len(core_pcs(c) & scale) / len(core_pcs(c)) for c in chords) / len(chords)
            want_minor = mode in ("minor", "dorian")
            bonus = 0.0
            first, last = chords[0], chords[-1]
            if first.root.pc == tonic and want_minor == (first.family in ("minor", "minor-major")):
                bonus += 0.08
            if (len(chords) > 1 and last.root.pc == tonic and last.family not in ("dominant", "dominant-sus")
                    and want_minor == (last.family in ("minor", "minor-major"))):
                bonus += 0.04
            if mode in ("major", "minor") and any(c.family == "dominant" and c.root.pc == (tonic + 7) % 12
                                                  for c in chords):
                bonus += 0.03
                if n > 1 and any(chords[i].family == "dominant" and chords[i].root.pc == (tonic + 7) % 12
                                 and chords[(i + 1) % n].root.pc == tonic for i in range(n)):
                    bonus += 0.05
            if mode in ("dorian", "mixolydian"):
                bonus -= 0.06
            out.append({"key": f"{default_spelling(tonic, True)} {mode}", "fit": round(fit + bonus, 3),
                        "tonic_pc": tonic, "mode": mode})
    out.sort(key=lambda d: -d["fit"])
    return out[:limit]


def analyze_progression(chords: list[Chord], key: tuple[Spelled, str] | None = None) -> dict:
    guesses = guess_keys(chords)
    if key is None:
        tonic_pc, mode = guesses[0]["tonic_pc"], guesses[0]["mode"]
        tonic_sp = default_spelling(tonic_pc, True)
    else:
        tonic_sp, mode = key
        tonic_pc = tonic_sp.pc
    scale = {(tonic_pc + s) % 12 for s in MODES[mode]}
    is_minor_key = mode in ("minor", "aeolian", "dorian", "phrygian", "harmonic minor", "melodic minor")
    parallels = (["major", "dorian", "harmonic minor", "melodic minor", "phrygian", "mixolydian"] if is_minor_key
                 else ["minor", "dorian", "mixolydian", "phrygian", "lydian", "harmonic minor", "melodic minor"])
    rows = []
    for i, ch in enumerate(chords):
        nxt = chords[(i + 1) % len(chords)] if len(chords) > 1 else None
        core = core_pcs(ch)
        allp = ch.pcs()
        row = {"chord": ch.name(), "numeral": roman_numeral(ch, tonic_pc), "family": ch.family}
        s = (ch.root.pc - tonic_pc) % 12
        if core <= scale:
            row["status"] = "diatonic"
            fn = (FUNCTIONS_MINOR if is_minor_key else FUNCTIONS_MAJOR).get(s)
            if fn:
                row["function"] = fn
            outside = allp - scale
            if outside:
                row["colour"] = "colour tones outside the key: " + ", ".join(
                    str(ch.spell(ch.tone_for_pc(p))) for p in sorted(outside))
        else:
            explanations = []
            if ch.family in ("dominant", "dominant-sus") or (ch.family == "major" and "b7" in {t.label for t in ch.tones}):
                target = (ch.root.pc + 5) % 12
                if target in scale:
                    resolves = nxt is not None and nxt.root.pc == target
                    tail = " — and it resolves there" if resolves else " (its resolution is avoided)"
                    if target == tonic_pc:
                        explanations.append("dominant of the home key with a raised leading tone "
                                            "(borrowed from harmonic minor)" + tail)
                    else:
                        explanations.append(f"secondary dominant: V7/{_target_numeral(target, tonic_pc, scale)}"
                                            + tail)
                target_sub = (ch.root.pc - 1) % 12
                if target_sub in scale and nxt is not None and nxt.root.pc == target_sub:
                    explanations.append("tritone substitution: dominant a semitone above its target, sliding down")
            borrowed = []
            for pm in ([] if explanations else parallels):
                pscale = {(tonic_pc + x) % 12 for x in MODES[pm]}
                if core <= pscale:
                    borrowed.append(pm)
            if borrowed:
                changed = sorted(core - scale)
                names = ", ".join(f"{ch.spell(ch.tone_for_pc(p))} (degree {DEGREE_NAMES[(p - tonic_pc) % 12]})"
                                  for p in changed)
                explanations.append(f"borrowed (modal interchange) from {tonic_sp} {borrowed[0]}: uses {names}")
            if not explanations:
                if nxt is not None and abs(((nxt.root.pc - ch.root.pc + 6) % 12) - 6) == 1:
                    explanations.append("chromatic passing/approach chord into the next chord")
                else:
                    explanations.append("chromatic chord (outside the key and its parallel modes)")
            row["status"] = "non-diatonic"
            row["explanation"] = explanations
        if nxt is not None and i < len(chords) - 1:
            row["root_motion_to_next"] = MOTION[(nxt.root.pc - ch.root.pc) % 12]
        rows.append(row)
    return {"key": f"{tonic_sp} {mode}", "key_candidates": guesses, "chords": rows}


def diatonic_chords(root: Spelled, mode: str, size: int = 4) -> list[dict]:
    steps = MODES[mode]
    if len(steps) != 7:
        raise TheoryError("diatonic chords need a 7-note mode")
    notes = scale_notes(root, mode)
    out = []
    for i in range(7):
        best, idx = None, []
        for sz in range(size, 2, -1):
            idx = [i, i + 2, i + 4, i + 6, i + 8][:sz]
            semis = [(steps[j % 7] + 12 * (j // 7)) - steps[i] for j in idx]
            rel = frozenset(x % 12 for x in semis)
            for suf, full, req, opt, comp in _templates():
                if rel == full or (rel <= full and req <= rel and (full - rel) <= opt):
                    if best is None or comp < best[1]:
                        best = (suf, comp)
            if best:
                break
        suf = best[0]
        ch = parse_chord(f"{notes[i]}{suf}")
        out.append({"degree": i + 1, "chord": ch.name(), "numeral": roman_numeral(ch, root.pc),
                    "notes": [str(notes[j % 7]) for j in idx]})
    return out


def fit_scales(pcs: set[int], limit: int = 12) -> list[dict]:
    pref = ["minor", "major", "dorian", "mixolydian", "phrygian", "lydian", "harmonic minor", "melodic minor",
            "minor pentatonic", "major pentatonic", "blues", "phrygian dominant", "lydian dominant"]
    out = []
    for mode in pref:
        for tonic in range(12):
            scale = {(tonic + s) % 12 for s in MODES[mode]}
            if pcs <= scale:
                out.append({"scale": f"{default_spelling(tonic)} {mode}", "unused": len(scale - pcs),
                            "rank": pref.index(mode)})
    out.sort(key=lambda d: (d["unused"], d["rank"]))
    return out[:limit]


def chords_containing(pc: int, root: Spelled, mode: str, size: int = 4) -> list[dict]:
    out = []
    for d in diatonic_chords(root, mode, size):
        ch = parse_chord(d["chord"])
        t = ch.tone_for_pc(pc)
        if t:
            role = {"1": "root — strongest, plain", "3": "3rd — first inversion, smooth",
                    "b3": "3rd — first inversion, smooth", "5": "5th — second inversion, floating",
                    "b5": "b5 — unstable"}.get(t.label, f"{t.label} in the bass — colourful/suspended")
            out.append({"chord": ch.name(), "numeral": d["numeral"], "bass_is": t.label, "effect": role})
    order = {"1": 0, "3": 1, "b3": 1, "5": 2}
    out.sort(key=lambda d: order.get(d["bass_is"], 3))
    return out


# Krumhansl-Kessler key profiles
KK_MAJOR = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
KK_MINOR = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]


def _corr(x: list[float], y: list[float]) -> float:
    mx, my = sum(x) / len(x), sum(y) / len(y)
    num = sum((a - mx) * (b - my) for a, b in zip(x, y))
    den = (sum((a - mx) ** 2 for a in x) * sum((b - my) ** 2 for b in y)) ** 0.5
    return num / den if den else 0.0


def detect_key(notes: list[dict], limit: int = 3) -> list[dict]:
    hist = [0.0] * 12
    for n in notes:
        hist[n["pitch"] % 12] += float(n.get("duration", 1.0))
    out = []
    for tonic in range(12):
        rot = hist[tonic:] + hist[:tonic]
        out.append({"key": f"{default_spelling(tonic)} major", "r": round(_corr(rot, KK_MAJOR), 3)})
        out.append({"key": f"{default_spelling(tonic)} minor", "r": round(_corr(rot, KK_MINOR), 3)})
    out.sort(key=lambda d: -d["r"])
    return out[:limit]


# --------------------------------------------------------------------------
# Progression strings and note-list utilities
# --------------------------------------------------------------------------

def parse_progression(text: str, default_beats: float = 4.0) -> list[tuple[Chord, float]]:
    """'Fm9 Bbm9:2 Eb13:2 | Abmaj9 %' -> [(chord, beats), ...]. '%' repeats the previous chord."""
    tokens = [t for t in re.split(r"(?:\s|\||,(?![^()]*\)))+", text.strip()) if t and t != "-"]
    out: list[tuple[Chord, float]] = []
    for tok in tokens:
        beats = default_beats
        if ":" in tok:
            tok, b = tok.rsplit(":", 1)
            try:
                beats = float(b)
            except ValueError:
                raise TheoryError(f"Bad duration {b!r} in {tok}:{b} (use Chord:beats, e.g. Fm9:2)")
        if tok == "%":
            if not out:
                raise TheoryError("'%' with no previous chord")
            out.append((out[-1][0], beats))
            continue
        out.append((parse_chord(tok), beats))
    if not out:
        raise TheoryError("Empty progression")
    return out


def _find_notes(obj, depth: int = 0):
    import json
    if depth > 8:
        return None
    if isinstance(obj, str):
        try:
            return _find_notes(json.loads(obj), depth + 1)
        except ValueError:
            return None
    if isinstance(obj, list):
        if obj and all(isinstance(n, dict) and "pitch" in n for n in obj):
            return obj
        if not obj:
            return []
        found = []
        for item in obj:  # e.g. MCP content blocks [{"type": "text", "text": "..."}], or lists of clips
            sub = _find_notes(item, depth + 1)
            if sub:
                found.extend(sub)
        return found or None
    if isinstance(obj, dict):
        if "pitch" in obj:
            return [obj]
        if "tracks" in obj and isinstance(obj["tracks"], list):
            out = []
            for t in obj["tracks"]:
                out.extend(_find_notes(t, depth + 1) or [])
            return out
        for key in ("notes", "result", "clip", "clips", "content", "text", "data"):
            if key in obj:
                sub = _find_notes(obj[key], depth + 1)
                if sub is not None:
                    return sub
    return None


def load_notes(obj) -> list[dict]:
    """Normalise MCP replies / clip JSON / raw note lists to [{pitch,start_time,duration,velocity,mute}].

    Accepts plain lists, {"notes": [...]}, clip JSON {"tracks": [...]}, MCP wrappers such as
    {"result": "<json string>"} or {"result": {...}}, and MCP content blocks
    {"content": [{"type": "text", "text": "<json>"}]}. Raises TheoryError if no notes are found.
    """
    raw = _find_notes(obj)
    if not raw:
        raise TheoryError("no MIDI notes found in the input (expected a list of {pitch, start_time, duration})")
    out = []
    for n in raw:
        out.append({"pitch": int(n["pitch"]),
                    "start_time": float(n.get("start_time", n.get("start", n.get("time", 0.0)))),
                    "duration": float(n.get("duration", n.get("length", 1.0))),
                    "velocity": int(n.get("velocity", 100)),
                    "mute": bool(n.get("mute", False))})
        if not 0 <= out[-1]["pitch"] <= 127:
            raise TheoryError(f"pitch out of MIDI range 0-127: {out[-1]['pitch']}")
    out = [n for n in out if not n["mute"]]
    if not out:
        raise TheoryError("all notes are muted")
    return out


def segment_notes(notes: list[dict], window: float | None = None, tol: float = 0.06) -> list[dict]:
    """Split a note list into harmonic segments: by onset (default) or fixed beat windows."""
    if not notes:
        return []
    segs = []
    if window:
        end = max(n["start_time"] + n["duration"] for n in notes)
        t = 0.0
        while t < end - 1e-9:
            w = {}
            for n in notes:
                ov = min(n["start_time"] + n["duration"], t + window) - max(n["start_time"], t)
                if ov > 1e-6:
                    w[n["pitch"]] = w.get(n["pitch"], 0) + ov
            if w:
                segs.append({"start": t, "end": t + window, "pitches": sorted(w), "weights": w})
            t += window
        return segs
    onsets = []
    for t in sorted({n["start_time"] for n in notes}):
        if not onsets or t - onsets[-1] > tol:
            onsets.append(t)
    prev = None
    for i, t in enumerate(onsets):
        sounding = sorted({n["pitch"] for n in notes
                           if n["start_time"] - tol / 2 <= t < n["start_time"] + n["duration"] - tol / 2})
        if sounding and sounding != prev:
            segs.append({"start": round(t, 3), "pitches": sounding})
            prev = sounding
    for i, s in enumerate(segs):
        s["end"] = segs[i + 1]["start"] if i + 1 < len(segs) else max(n["start_time"] + n["duration"] for n in notes)
    return segs
