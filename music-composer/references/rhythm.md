# Rhythm, syncopation and chord rhythm

Times are in beats (quarter notes): 1 bar of 4/4 = 4.0; an 8th = 0.5; a 16th = 0.25. These are the units of clip JSON, the MCP and `mc.py voice --hits`.

## Harmonic rhythm (how often chords change)

| Context | Typical change rate |
|---|---|
| DnB (170–176 BPM) | every 1, 2 or 4 bars — chords feel half-time against the drums |
| Liquid / atmospheric DnB | 2–4 bars per chord, or a 2-chord vamp over 8 bars |
| House (120–128) | every bar or two; stab loops of 1–2 bars |
| Downtempo (80–110) | every bar or two; jazzier sections twice a bar |
| Acid jazz (95–120) | every bar or half bar; vamps on one chord for whole sections |

Slower harmonic rhythm = more atmospheric; faster = more "song", more jazz.

## Anticipation ("the push")

Moving a chord change an 8th or 16th *early* (e.g. the bar-2 chord starts at beat 3.5 of bar 1) gives funk, soul and house their forward lean. Shorten the previous chord accordingly. In note data: start_time 3.5 (or 3.75) instead of 4.0.

## Stab and comping patterns (positions within one bar, for `--hits`; the pattern repeats every bar of a chord)

| Feel | `--hits` | `--hit-len` |
|---|---|---|
| House offbeat 8ths | `0.5,1.5,2.5,3.5` | 0.25 |
| Deep house push | `0,0.75,1.5,2.5` | 0.25–0.5 |
| Charleston (jazz comp) | `0,1.5` | 0.5 |
| Soul/Rhodes comp | `0,1.5,2.75` | 0.5–1 |
| DnB one hit per bar | `0` | 1–2 |
| DnB two-step stab (with the kick) | `0,2.5` | 0.25–0.5 |
| Garage/2-step skip | `0,0.75,2.25,3` | 0.25 |

For longer patterns or per-chord variation, write the notes directly as clip JSON and `validate` them.

## Swing and groove

- 16th-note swing around 54–62% is the house/hip-hop/acid-jazz pocket; downtempo can go heavier. Apply swing in the DAW (Ableton groove pool) rather than baking it into note positions, so it stays adjustable.
- Humanise velocities (±5–12), not timing, for keys parts that need to sit on the grid; push the snare-adjacent notes slightly late for laid-back downtempo.
- Ghost notes: very short (≤ 0.125 beats), low velocity (30–50), between main hits — bass and Rhodes comping both use them.

## Syncopation guidelines

- Keep one anchor: if the chords syncopate, keep the bass on downbeats (or vice versa).
- Don't syncopate every layer the same way — complementary rhythms (call/response between bass and stabs) sound tighter than everyone pushing together.
- In DnB, leave the snare (beats 2 and 4) clear of stabs and bass hits; place movement around it.

## Polyrhythm

Dotted 8ths (every 0.75 beats) against 4/4 make a 3-against-4 cycle that resolves every 3 beats → a classic pad/pluck/delay feel in downtempo and liquid DnB.
