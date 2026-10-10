# Melody

A melody is a motif that develops, not a walk through scale notes. Write the rhythm and shape first, then choose pitches against the chords.

## Building blocks

- **Motif**: 2–5 notes with a recognisable rhythm and contour (e.g. short-short-long, rising a 4th then stepping down). Everything else is made from it.
- **Phrase**: usually 2 or 4 bars. Pair phrases as **question → answer** (antecedent/consequent): same opening, different ending — the question ends on an unstable note (2, 4, 6, 7 or a tension), the answer on a stable one (1, 3, 5 of the chord).
- **Contour**: one clear high point per phrase (often in its second half); come down after it. Avoid hovering in one place without purpose.
- **Space**: rests are part of the melody. In DnB and house the gaps let the drums and bass speak.

## Development techniques (vary one thing at a time)

| Technique | What changes | Example from motif C–Eb–F (8th, 8th, quarter) |
|---|---|---|
| Repeat | nothing (move the chord under it instead) | same notes over a new chord: new colour for free |
| Sequence | pitch level | D–F–G, then Eb–G–Ab |
| Rhythmic displacement | where it starts | same notes, starting on the "and" of 1 |
| Augmentation / diminution | note lengths ×2 or ÷2 | quarters–quarters–half |
| Inversion | interval direction | C–A–G (down instead of up) |
| Truncation / extension | length | C–Eb, or C–Eb–F–G–F |
| Ornament | add passing/neighbour notes | C–D–Eb–F |

Common shape for a 4-bar phrase: motif, motif varied, motif developed further, cadence (an answer that lands).

## Pitch choices against chords

- **Strong beats** (beats 1 and 3, or the downbeat of each chord): chord tones or the chord's colour tensions (9, 11 on minor, 13, #11 on maj7). These define the harmony.
- **Weak beats / short notes**: passing tones (stepwise between chord tones), neighbour tones (step away and back), chromatic approach notes (a semitone into a chord tone).
- **Avoid notes** held on strong beats: natural 11 over major or dominant chords, b9 over minor chords. Fine as quick passing notes.
- **Guide-tone melodies**: a melody made of 3rds and 7ths moving by step across the changes is the most "inside" and soulful line; decorate it with rhythm.
- **Common-tone melodies**: a note that is a chord tone in one chord and a tension in the next (e.g. C over Fm9 = 5, over Bbm9 = 9, over Eb13 = 13, over Abmaj9 = 3) — holding it while the chords move is a classic atmospheric trick.

## Call and response

- Between instruments: Rhodes phrase (call) answered by a pad swell, vocal chop or horn line.
- Within one line: bars 1–2 ask, bars 3–4 answer.
- Against the chords: leave the melody silent on chord changes and enter just after — the harmony "calls", the melody "responds".

## Register and instrument

Melody should sit above the chord voicing's top note or be clearly separated in timbre. Typical: C3–C5 (60–84) for leads and keys melodies; higher for bells and plucks.

## Genre notes

- **Liquid/jazzy DnB**: sparse, long notes over the fast drums; phrases often span 2 or 4 bars at 170+, so think at half-time. Pentatonic/dorian with 9ths.
- **Downtempo / trip-hop**: lazy, behind-the-beat phrasing; blue notes; repeated short hooks.
- **Acid jazz**: blues-inflected, pentatonic with chromatic approach notes, horn-section style phrases, syncopation.
- **House**: short repeated hooks (1–2 bars), vocal-like; repetition with small variations every 4 or 8 bars.

## Workflow

1. Write the motif and phrase plan (in words or rhythm) before pitches.
2. Choose pitches; write the notes as clip JSON (`pitch`, `start_time`, `duration`, `velocity` in beats).
3. Run `mc.py validate melody.json --role melody --chords "<progression>"`. It labels each note (chord tone / tension / passing / approach / avoid / outside) and reports range, stepwise percentage, leaps and repeated interval cells (motif reuse). Flags are prompts to listen, not errors.
4. Present the melody as a note table (bar.beat, note, MIDI, length) plus a one-line description of its shape.
