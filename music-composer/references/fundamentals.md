# Fundamentals

Reference for the basics you'll explain most often. Pair with `teaching.md` for *how* to explain.

## MIDI and octave numbering

- One semitone = 1 MIDI number; one octave = 12. MIDI 60 is "middle C".
- **Ableton names MIDI 60 "C3"**; scientific pitch notation (most theory books, many other DAWs) calls it "C4". Always give MIDI numbers alongside names so there's no ambiguity.
- Useful landmarks (Ableton names): E0 = 28 (~41 Hz, lowest bass guitar string), C1 = 36 (~65 Hz), C2 = 48, C3 = 60, C4 = 72, C5 = 84.
- Sub-bass fundamentals typically live around MIDI 24–43 (C0–G1 in Ableton terms, ~32–98 Hz).

## Intervals

| Semitones | Name | Plain description | From C3 (60) |
|---|---|---|---|
| 1 | minor 2nd | crunchy, tense rub | Db3 (61) |
| 2 | major 2nd | gentle step, open rub | D3 (62) |
| 3 | minor 3rd | the "sad/minor" sound | Eb3 (63) |
| 4 | major 3rd | the "happy/major" sound | E3 (64) |
| 5 | perfect 4th | open, hollow, unresolved | F3 (65) |
| 6 | tritone | unstable, wants to move | F#3/Gb3 (66) |
| 7 | perfect 5th | strong, neutral, "power chord" | G3 (67) |
| 8 | minor 6th | dark, cinematic | Ab3 (68) |
| 9 | major 6th | warm, sweet | A3 (69) |
| 10 | minor 7th | bluesy, soulful | Bb3 (70) |
| 11 | major 7th | dreamy, slightly aching | B3 (71) |
| 12 | octave | same note, higher | C4 (72) |

Compound intervals: 9th = 2nd + octave (14), 11th = 4th + octave (17), 13th = 6th + octave (21). They're named this way because they're the notes you get by continuing to stack thirds past the 7th.

## Scales and modes

A mode is a scale with a different "home" note. Explain each by what's different from plain major or minor — that one note is the mode's flavour.

| Mode | Compared to… | Characteristic note | Feel and use |
|---|---|---|---|
| Ionian (major) | — | — | bright, resolved; house piano, soulful house |
| Dorian | natural minor | raised 6th | soulful minor; liquid DnB, acid jazz, deep house vamps |
| Phrygian | natural minor | flat 2nd | dark, tense; neurofunk, techy DnB, trip-hop |
| Lydian | major | raised 4th | floating, dreamy; atmospheric DnB, ambient, cinematic |
| Mixolydian | major | flat 7th | funky, bluesy major; acid jazz, funk vamps |
| Aeolian (natural minor) | — | — | sad, serious; default dark key |
| Locrian | natural minor | flat 2nd and flat 5th | unstable; almost never home |
| Harmonic minor | natural minor | raised 7th | dramatic; gives minor keys a real V7 |
| Melodic minor (jazz) | natural minor | raised 6th and 7th | modern jazz minor; minor-major chords |

`mc.py scale D dorian` prints notes, degrees and MIDI numbers for any of these.

## Keys, relative major/minor

Every major key shares its notes with a minor key three semitones below (C major / A minor, Ab major / F minor). A loop using only those notes can feel like either — which one you hear as "home" depends on the bass and which chord the loop rests on. This is the most common source of harmonic ambiguity; say so rather than guessing.

## Chords from a scale

Stack every other scale note: 1-3-5 (triad), 1-3-5-7 (seventh chord), 1-3-5-7-9 (ninth). In a major key the seventh chords are:

`Imaj7  ii7  iii7  IVmaj7  V7  vi7  viiø7` — e.g. C major: Cmaj7 Dm7 Em7 Fmaj7 G7 Am7 Bm7b5.

`mc.py diatonic "F minor" --size 5` lists the chords for any key/mode.

## Roman numerals (this skill's convention)

Numerals are measured from the key's tonic using major-scale steps, with flats/sharps for anything else, so they read the same in major and minor: in F minor, Ab is `bIII`, Db is `bVI`, Eb is `bVII`. Upper case = major-third chord, lower case = minor; `ø` half-diminished, `°` diminished; extensions follow (`i9`, `bVII13`, `IVmaj7`). Use numerals only when they help ("this is the iv chord borrowed from minor"); otherwise use chord names.

## Chord symbols

Root + quality + extensions/alterations (+ `/bass`). `m` minor, `maj7` major seventh, `7` dominant seventh, `ø`/`m7b5` half-diminished, `°7` diminished, `sus4`/`sus2` third replaced, `add9` colour without the 7th, `alt` altered dominant, `/G` bass note. `mc.py spell <chord>` shows the notes, which are essential (3rd, 7th, named extensions) and which are optional (usually the 5th; lower extensions implied by a 13th).
