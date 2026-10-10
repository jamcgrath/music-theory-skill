# Basslines

The bass decides what chord the listener hears. The same upper voicing over a different bass note is a different chord (Abmaj7 over F = Fm9; over C = Abmaj7/C).

## Bass note choices and their effect

| Bass plays | Effect |
|---|---|
| Root | solid, clear; default for downbeats |
| 3rd | first inversion: smoother, lighter; great for stepwise bass lines |
| 5th | second inversion: floating, unresolved; pedal-like |
| 7th | tension, "falling" feel (Cmaj7/B); passing |
| a non-chord tone | creates a new composite chord (Bb under Abmaj7 → Bb13sus4-ish); check with `mc.py identify` |

## Movement vocabulary

- **Approach notes**: a semitone below or above the next chord's root on the last 8th/16th before the change (E → F; Gb → F). Chromatic approaches are the single most effective "jazz" move in a bassline.
- **Dominant approach**: the 5th of the next chord before it (C → F).
- **Passing tones**: fill a 3rd with the step between (F–G–Ab).
- **Octave jumps**: rhythm without new harmony; the funk/disco/house staple.
- **Root–5th–octave** patterns: sturdy and genre-neutral.
- **Pedal**: hold one note under changing chords (see `harmony.md` §4).

## Styles

**Root-note bass** — one note per chord, rhythm carries it. DnB subs, house, minimal downtempo.

**Melodic bass** — stepwise or arpeggiated lines with inversions; the bass becomes a counter-melody. Jazzy downtempo, liquid DnB intros.

**Jazz / walking** — quarter notes: beat 1 chord root, beats 2–3 chord tones or scale steps, beat 4 a chromatic or 5th approach into the next root. `Dm7 | G7`: D F A Ab | G … (Ab is the semitone-above approach into G)

**Funk / acid jazz** — 16th-note syncopation, ghost notes (very short, low velocity), root and octave, b7 and 5th, a slide or hammer into the 1. Leave beat 1 strong, play around the snare.

**Sub-bass (DnB/downtempo)** — single sustained notes, mostly roots, long durations (whole bars or half-bars), occasional slide/glide (portamento) into the next note. Keep it mono and simple: busy sub lines below ~60 Hz smear. Fundamentals: E0–G1 (MIDI 28–43). A mid-bass/reese layer can carry movement while the sub holds roots.

**DnB rhythmic bass** — follows the two-step kick: notes on 1 and the "and" of 3 (positions 0 and 2.5 in beats), leaving space around the snare on 2 and 4. Liquid often follows the chord roots with long notes; rollers repeat a 1-bar figure.

**House bass** — offbeat 8ths (between the kicks), root–octave, or a syncopated 1–2 bar riff; leaves the kick's space on each beat.

## Bass and chords together

- Bass owns the bottom: keep chord voicings at least an octave above the bass note (≥ C2, MIDI 48, when the bass is in the sub).
- Don't double the bass's moving notes in the keys' bottom voice.
- When the bass moves by step through inversions, keep the upper voicing still — the harmony "changes" for free.

## Harmonising an existing bassline (procedure)

1. Get the notes: from the user, a `.mid` (`mc.py midi-read`), or Ableton via MCP (save to JSON).
2. Read the implied harmony per bar: `mc.py notes bass.json --window 4` (short approach notes are ignored), then `mc.py fit <downbeat/long notes only>` for candidate keys — approach and passing notes are often chromatic and would rule out every scale.
3. For each bar's main (downbeat/longest) note, list options: `mc.py bass-options <note> --key "<key>"` (bass as root, 3rd, 5th, 7th or colour).
4. Choose chords with a goal (smooth, soulful, dark…) and offer 2–3 options with different intents. Treat approach/passing notes as non-harmonic — harmonise the downbeats.
5. Voice them over the user's actual bassline: `mc.py voice "<progression>" --bass-file bass.json` (keeps their bass, spaces the chords an octave or more above it), then verify: `mc.py validate bass.json --role bass --chords "<progression>"`.
