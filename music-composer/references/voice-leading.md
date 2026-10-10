# Voice leading and register

Voice leading = how each note of one chord moves to the next. Good voice leading is why a progression sounds like one instrument playing rather than blocks being pasted in, and it's what makes chords *playable* for someone with limited keyboard technique.

## Principles (in priority order for this music)

1. **Hold common tones.** If two chords share a note, keep it in the same voice/octave. `Fm9 → Bbm9` shares Ab and C — keep them, move the rest.
2. **Move the others by the smallest step.** Semitones and whole tones. Big jumps belong in the bass and melody, not inner voices.
3. **Guide-tone lines.** In ii–V–I and circle-of-fifths motion, the 7th of one chord falls a step to the 3rd of the next (Dm7's C → G7's B; G7's F → Cmaj7's E). Keeping those lines intact is most of jazz voice leading.
4. **Treat the top voice as a melody.** Listeners hear the top note most. Aim for a top line that moves by step or holds; the script's `--top-line` pins it.
5. **Bass and top in contrary motion** when possible — the progression feels wider and more intentional.
6. **Loops wrap.** In a 4-bar loop, chord 4 → chord 1 is a transition too. `mc.py voice` optimises it by default (`--no-loop` to turn off).

Classical "no parallel 5ths/octaves" rules don't apply to electronic textures. Parallel movement of a whole shape (planing) is a deliberate, idiomatic sound — use it when the colour is the point, use smooth voice leading when the line is the point. Say which one you're doing.

## Register

Low notes need wider spacing; close intervals low down turn to mud. Classic low-interval limits (lowest comfortable bottom note for each interval):

| Interval | Lowest bottom note (Ableton name, MIDI) |
|---|---|
| minor 2nd | E2 (52) |
| major 2nd | Eb2 (51) |
| minor 3rd | C2 (48) |
| major 3rd / perfect 4th | Bb1 (46) |
| tritone | B1 (47) |
| perfect 5th | Bb0 (34) |
| minor 6th | G1 (43) |
| major 6th / 7ths | F1 (41) |

`mc.py check` and `voice` enforce these. Practical zones (Ableton names):

- **Sub / bass**: E0–G1 (28–43). One note at a time.
- **Low-mid danger zone**: G1–C2 (43–48). Keep chords out when there's a bassline; at most a 5th or octave.
- **Keys/pads body**: C2–C4 (48–72). Most chord voicings live here.
- **Air/top**: above C4 (72). Colour notes, bells, pad tops, melodies.

With a bass part, keep the chord's lowest note at least an octave above the bass note, ideally above C2 (48).

## Fixing a jumpy progression

1. Drop the root from the keys (the bass has it) — fewer notes to move.
2. Choose inversions so common tones stay put: run `voice` rather than stacking each chord from its root.
3. Pin the top voice (`--top-line`) to a stepwise line if the top is jumping.
4. If one chord still jumps, ask whether its function needs that chord; a substitution with more common tones (see `reharmonization.md`) may serve better.
5. Report movement in plain terms: the script prints notes held and total semitones moved per change.

## Rootless "A" and "B" forms (piano/Rhodes shorthand)

For 4-voice rootless voicings over a bass, jazz pianists alternate two shapes so ii–V–I moves by step:
- **A form**: 3 – 5 – 7 – 9 (Dm9: F A C E)
- **B form**: 7 – 9 – 3 – 5 (Dm9: C E F A)
On a dominant, swap the 5 for the 13 (G13: B E F A / F A B E). ii (A) → V (B) → I (A) is a classic smooth chain. The script finds these automatically; mention the names only if the user is learning to play them.
