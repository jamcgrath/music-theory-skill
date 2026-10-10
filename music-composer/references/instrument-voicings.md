# Instrument-aware voicings

Same chord, different instrument, different voicing. Each section: register, density, spacing, length, and what to include. Note names use Ableton octaves (C3 = 60); every example was generated or checked with `mc.py`. Script style names in brackets.

## Rhodes / electric piano [`rhodes`]
- **Register**: bottom note ~D2–C3 (50–60), top ~G3–C4 (67–72). Above C4 the tines get bell-like — lovely for a top voice, thin for the body.
- **Density**: 3–4 notes, rootless when the bass has the root. Two-hand version: LH shell (root+7 or 3+7) and RH 3–4 note upper structure.
- **Spacing**: close (within an octave); seconds inside the voicing are a feature (the 9 rubbing on the 3rd or b3).
- **Length/velocity**: sustained or comped. Velocity changes tone (bark above ~100), so vary it by ±10 rather than using one value.
- Example, `Dm9 G13 Cmaj9` over a bass: C3 E3 F3 A3 (60 64 65 69) → B2 E3 F3 A3 (59 64 65 69) → B2 D3 E3 G3 (59 62 64 67). Only one or two notes move per change.

## Acoustic piano [`piano`]
- **Register**: LH ~C1–C3 (36–60), RH ~C3–C5 (60–84).
- **Density**: 4–6 notes. LH root+7th or root+3rd/10th (if no separate bass), RH 3 notes of colour.
- **Spacing**: open at the bottom (5ths, 7ths, 10ths), closer on top. Avoid close LH 3rds below C2 (48).
- Without a bass part (`--no-bass`), the piano's lowest note is the root. Example `Dm9` (no bass): D2 C3 | E3 F3 A3 (50 60 | 64 65 69).
- Piano house: bright triads/7ths in the right hand, octave-doubled top, rhythmic.

## Synth pads [`pad`]
- **Register**: wide — bottom ~Ab1–C2 (44–48) only with open intervals, top up to C5 (84).
- **Density**: 4–6 voices; doubling the root or 5th high is fine.
- **Spacing**: open at the bottom (5ths, octaves, 7ths), clusters/2nds higher up. Slow attack makes clusters lush instead of harsh.
- **Length**: full chord length or overlapping (legato) so the release tails crossfade.
- **Bass**: if a sub is playing, keep the pad's lowest note above ~C2 (48) or high-pass the pad.
- Example `Fm9 Dbmaj9 Ebm9 Ab13` over a bass: Ab2 G3 C4 Eb4 (56 67 72 75) → Ab2 F3 C4 Eb4 (56 65 72 75) → Bb2 Gb3 Db4 F4 (58 66 73 77) → Bb2 Gb3 C4 F4 (58 66 72 77). Wide 7th/6th at the bottom, the colour notes on top.

## Synth stabs [`stab`]
- **Register**: mid, ~G2–G4 (55–79).
- **Density**: 3 notes (sometimes 4). m7/m9/m11 shapes are the deep-house classic.
- **Spacing**: tight, one hand.
- **Length**: short (1/16–1/8), rhythmic. Same shape moved in parallel ("chord memory") is a genre signature — see `harmony.md` §4.
- Use `--hits` for rhythm, e.g. `--hits 0.5,1.5,2.5,3.5 --hit-len 0.25` for offbeat 8ths.

## Organ [`organ`]
- **Register**: C2–G4 (48–79).
- **Density**: 3–4 close notes; root and 5th welcome. Drawbars already add harmonics, so fewer notes go further.
- **Style**: quartal shapes (stacked 4ths) for modal jazz/acid jazz; triads with the root doubled for house/gospel.

## Plucked synths [`pluck`]
- **Register**: higher, ~C3–E5 (60–88).
- **Density**: 2–3 notes; or arpeggiate the voicing (order the script's notes and space them by 1/16).
- **Length**: short; the envelope does the work. Wider voicings (spread over an octave+) sound better arpeggiated.

## Bass synthesizers
- **Register**: sub E0–G1 (28–43); mid/funk bass up to ~G2 (55) (`--bass-range 36-55`).
- **Density**: one note. Octave jumps and 5ths are the only "chords" that survive low down, and only above ~C1 (36).
- **Interaction**: the bass note decides the chord's root/inversion. If the bass plays the 3rd or 7th, the chord changes character (see `basslines.md`).

## Avoiding low-frequency overlap (all instruments)
- Only one part owns each register: sub (bass), low-mid (one of: Rhodes LH, pad bottom, piano LH), mid (chords), top (melody, pad top).
- If keys and pad both play chords, give them different registers or different notes (keys rootless 3-7-9, pad 5-9-13 higher).
- Check a combined voicing with `mc.py check <chord> <notes> --bass <bass note>` — it flags mud, overlap with the bass, and anything below the low-interval limits.

## Quick colour menu (same chord, different flavours)
For `Fm` in a minor-key loop: Fm7 (plain soul) · Fm9 (lush default) · Fm11 (open, modal, quartal-friendly) · Fm6/9 (dorian, film-noir) · Fm(maj9) (spy/mysterious). Change the symbol, then re-voice.
