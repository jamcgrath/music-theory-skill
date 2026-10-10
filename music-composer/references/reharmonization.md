# Reharmonisation

Changing chords while keeping what the user wants to keep (usually the melody, the bassline, the groove, or specific chords they like).

## Before you change anything

1. **List the constraints**: chords they like (frozen), the melody/top note (must stay a chord tone or available tension — check with `validate --role melody`), the bassline (if fixed, new chords must contain or deliberately colour the bass note — `bass-options`), the loop length.
2. **Decide the intent** of each option. Three reharmonisations should differ in *effect*, e.g.:
   - A: same function, richer colour (extensions, sus, inversions) — the safe upgrade.
   - B: new functional pull (secondary dominants, ii–V, tritone sub) — more motion, more jazz.
   - C: modal/chromatic (borrowed chords, planing, pedal) — darker, floatier or stranger.
3. **Change the fewest chords that achieve the intent.** Reharmonising one chord (often the last of the loop) is frequently enough.

## Toolbox

Each entry: what it is → which notes change → what it does. Examples in C major / F minor; transpose as needed.

**Diatonic substitution.** Swap a chord for one sharing two or three notes with the same job. C → Am7 (shares C, E, G) or Em7 (shares E, G; with Cmaj7 it shares E, G, B); F → Dm7 (shares F, A, C). Softer, same key.

**Extension upgrade/downgrade.** Fm7 → Fm9 (adds G) → Fm11 (adds Bb). Cleaner mixes often want the reverse: Fm11 → Fm9 → Fm7 → just Ab+Eb shell.

**Modal interchange (borrowed chords).** Take a chord from the parallel mode with the same tonic.
- In a major key, from the parallel minor: `iv` (F → Fm: A becomes Ab — instant bittersweet soul), `bVI` (Abmaj7: Ab, Eb — cinematic lift), `bVII` (Bb7 or Bbmaj7: Bb — rock/funk swagger), `bIII` (Ebmaj7), `iiø7` (Dm7b5: Ab — dark pre-dominant).
- In a minor key, from dorian: major `IV` (in F minor, Bb7/Bb9 instead of Bbm7: Db becomes D — lifted, soulful). From major: a major tonic at the end (Picardy third: F instead of Fm).
- Explain with the changed note(s): "Fm7 instead of Fmaj7 — A drops to Ab and E drops to Eb."

**Secondary dominants.** Make any diatonic chord feel arrived-at by putting its own V7 before it. Before Dm7, use A7 (C# is the new note — it leads up to D). Before Am7, E7. Pair with its ii for a full ii–V: Em7b5 A7 → Dm7.

**Tritone substitution.** Replace a dominant with the dominant a tritone away: G7 → Db7 (or Db9/Db13). Same tritone (F and B=Cb), but the bass now slides down by semitone into C. Smooth, sophisticated; very acid-jazz / neo-soul.

**Backdoor dominant.** iv7 – bVII7 – I (Fm7 Bb7 Cmaj7) instead of ii–V–I. Arrives from below; warm, gospel/soul.

**Chromatic approach chords.** Precede a target with the same chord type a semitone above or below: Bbm9 → (A9 or Bm9) → Bbm9… or Abmaj9 → A7 → Bbm9. Works best on short note values / the last beat of a bar.

**Constant structure / planing.** Keep the voicing shape, move the root (Fm9 → Ebm9 → Dbm9 → Ebm9). Ignores the key on purpose. The deep-house and atmospheric-DnB move.

**Pedal point.** Keep the bass on one note while upper chords change (all over F: Fm9, Gbmaj7/F, Ebm9/F, Db/F). Great for intros/breakdowns; tension releases when the bass finally moves.

**Sus the dominant.** G7 → G9sus4 (= F/G or Dm7/G). Removes the B, so the pull to C becomes gentle. Very house/neo-soul.

**Re-bass (inversions/slash chords).** Keep the upper chord, change the bass note: Cmaj7 → Cmaj7/E, Abmaj7 → Abmaj7/C. Makes the bassline melodic without changing the harmony's colour much.

**Deceptive resolution.** Where the ear expects the tonic, go to vi, bVI or IV: G7 → Am7 / Abmaj7. Keeps a loop from feeling finished.

**Chromatic mediant.** Cmaj7 → Abmaj7 or Emaj7. Few shared notes, big colour shift. Use sparingly.

## Descriptor → technique map

| They say | Try first | Then |
|---|---|---|
| darker | borrow from minor/phrygian (bVI, bII, iv), m9→m11, lower the top voice, b9/b13 on dominants | pedal point under minor chords, planing down by whole tones |
| brighter / uplifting | major IV in minor (dorian), maj7→maj9/6/9, lydian #11, raise top voice | modulate up a whole step at a section change |
| more soulful | m9/m11 on ii and vi, dominant 9/13, backdoor iv–bVII, gospel IV/I and Ab/Bb-type slash dominants | chromatic passing diminished chords (C#°7 between C and Dm7) |
| more atmospheric / floating | sus chords, add9, maj7#11, open/quartal voicings, slower harmonic rhythm, pedal | constant-structure moves by thirds or whole tones |
| more tension | dominants with b9/#9/b13, tritone subs, chromatic approach chords, delay the resolution | hold a dominant pedal across a whole phrase |
| less predictable | deceptive resolution, re-bass one chord, replace one diatonic chord with a borrowed one, change the last chord of every 4th repetition | planing to an unexpected root |
| simpler / cleaner | drop extensions, use shells (3+7) or triads, fewer chord changes | |
| jazzier | ii–V–I pairs, secondary dominants, tritone subs, 13ths and alterations | walking bass |
| late-90s atmospheric DnB | m9/maj9 planing, lydian maj7#11, long pads, 1–2 chords per 4 bars | see `genres/jazzy-dnb.md` |

## Explaining a reharmonisation

For each option: the new chords, the voicing (from `mc.py voice`), and one line naming the change in heard terms ("bar 4 now slides down a semitone into bar 1 instead of jumping — that's the tritone sub"). Offer the theory name; don't lead with it.
