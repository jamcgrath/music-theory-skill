# music-composer — a Claude Code skill

A music theory advisor and composition partner for jazz-influenced electronic music (jazzy/liquid DnB, downtempo, acid jazz, house). It suggests chords, progressions, voicings, melodies and basslines, explains them in plain language, and produces MIDI-ready notes that are verified by a deterministic script before you see them. Ableton Live integration is optional and runs through whatever Ableton MCP server you already have.

## Contents

```
music-composer/                 <- the skill (this folder is what gets installed)
├── SKILL.md                    workflow, principles, conventions, cheat sheet, reference map
├── references/                 loaded on demand
│   ├── fundamentals.md         intervals, modes, keys, numerals, MIDI/octave conventions
│   ├── harmony.md              chord anatomy, extensions, functional + modal harmony, devices
│   ├── reharmonization.md      substitution toolbox, "darker/more soulful/…" → technique map
│   ├── voice-leading.md        principles, register, low-interval limits, rootless A/B forms
│   ├── instrument-voicings.md  Rhodes, piano, pads, stabs, organ, plucks, bass synth
│   ├── melody.md               motif development, phrasing, call/response, validation
│   ├── basslines.md            styles, approach notes, sub-bass, harmonising a bassline
│   ├── rhythm.md               harmonic rhythm, pushes, stab patterns (--hits), swing
│   ├── arrangement.md          section roles, variation without monotony, transitions
│   └── teaching.md             the explanation ladder + plain-language glossary
├── genres/                     jazzy-dnb, dnb, jazzy-downtempo, downtempo, acid-jazz, house
├── integrations/ableton-mcp.md discovery, safety rules, read/write/verify flows, fallback
├── scripts/
│   ├── mc.py                   CLI (stdlib only, Python 3.9+)
│   ├── theory_core.py          spelling, identification, voicing search, analysis
│   ├── midi_io.py              Standard MIDI File read/write
│   └── tests/test_theory.py    44 unit tests
└── evals/
    ├── evals.json              14 behaviour scenarios with graded assertions
    └── check_toolchain.py      38 executable checks behind those scenarios
```

## Install

Requires Python 3 on the machine where Claude runs the skill. No packages to install.

**Claude Code, personal (all projects)**
```bash
mkdir -p ~/.claude/skills
cp -r music-composer ~/.claude/skills/
```
**Claude Code, one project**: copy `music-composer/` into the project's `.claude/skills/`.

**claude.ai / Cowork / cloud sessions**: these don't read `~/.claude/skills`. Upload `music-composer.skill` (a zip of the folder) in your claude.ai skill settings and enable it; it then syncs to Cowork, cloud and signed-in terminal sessions.

Check it loaded: run `/skills` in Claude Code, or invoke it directly with `/music-composer`. It also triggers automatically on chord/progression/voicing/bassline/melody requests.

Smoke test:
```bash
python3 ~/.claude/skills/music-composer/scripts/mc.py voice "Fm9 Bbm9 Eb13 Abmaj9" --style rhodes
python3 -m unittest discover -s ~/.claude/skills/music-composer/scripts/tests
python3 ~/.claude/skills/music-composer/evals/check_toolchain.py
```

## Editing

`music-composer/` is the source. After changing it, run `./build.sh` to rebuild `music-composer.skill` and `music-composer-skill.zip` together so they can't drift apart.

## Connecting an existing Ableton MCP

The skill doesn't ship Ableton communication code; it uses the server you have.

1. Install a server and its Live-side Remote Script per the server's README. Two common ones:
   - `ahujasid/ableton-mcp` — `uvx ableton-mcp`, plus the `AbletonMCP` Remote Script selected as a Control Surface in Live's Link/Tempo/MIDI preferences.
   - `wstierhout/ableton-live-mcp` — `uvx mcp-server-ableton-live` (a larger tool set: clip reading, generators, offline .als parsing).
2. Register it with Claude Code, e.g. `claude mcp add ableton -- uvx ableton-mcp` (or the server's documented command). For Claude Desktop/Cowork, add it as a local MCP server in the desktop app's settings.
3. Open Live, then ask something like "read the chords on my Rhodes track". The skill inspects the server's actual tools (it never assumes names), reads clips, and writes new ideas to **new clips in empty slots**, then reads them back to verify.

Safety: the skill never overwrites or edits existing clips without your explicit go-ahead. Some servers' "add notes" tools replace a clip's entire contents and their generators overwrite clips, so the skill treats every write to an existing clip as destructive. With no MCP, it hands you `.mid` files (one per part) plus a note table.

## Example prompts

- "Write a dark, jazzy four-bar progression for a liquid DnB tune at 174 — Rhodes and sub."
- "I like the first two chords but not the last two. Give me three alternatives for bars 3–4."
- "Make this sound more like late-90s atmospheric DnB: Am7 Dm7 G7 Cmaj7."
- "What chords work with my bassline? F1 for three beats then A1, Bb1 then E1, Eb1, Ab1."
- "What are these chords? 41 56 60 63 67 | 46 56 60 61 65 | 39 55 60 61 65 | 44 58 60 63 67"
- "Give me three ways to reharmonise Cmaj7 Am7 Dm7 G7 — keep the melody G C F F."
- "Write a singable 4-bar flute melody over Fm9 Bbm9 Eb13 Abmaj9."
- "Why does Cmaj7 → Fm7 sound bittersweet? Explain it simply."
- "Deep house m9 stabs in A minor, offbeat, as MIDI."
- "Read clip 1 on track 3 in Live, tell me the key and chords, then write a more soulful variation into a new slot."
- "Voice these as pads with the top note following C5 Db5 C5 Bb4."

## Architecture and design decisions

**Three layers, each doing what it's reliable at.**
- *The model* makes musical decisions (which chord, which colour, what a vague word like "soulful" means, rhythm, melody) using concise reference files read on demand.
- *A small deterministic script* handles everything with a right answer: chord spelling (with correct enharmonics), MIDI numbers, voice-led instrument voicings, validation of any note list against chord symbols, chord identification with ranked alternatives, key/scale lookups, roman-numeral analysis, MIDI file I/O. The skill requires every note list to come from or be checked by the script, because note-number arithmetic is where language models make silent mistakes.
- *The MCP*, when present, is only transport: read clips and session context, write new clips.

**No music theory library dependency.** music21 is large and slow to install; lighter libraries (pychord, mingus) don't cover jazz alterations, rootless/voicing validation or loop-aware voice leading. The needed functionality is ~1,200 lines of stdlib Python and fully tested, so the skill installs anywhere with Python 3.

**Chord identity vs voicing.** A chord symbol fixes pitch classes and marks which tones are required (3rd, 7th, named extensions/alterations), optional (5th, implied lower extensions) or the root (usually left to the bass). The voicer never adds tones the symbol doesn't contain — colour changes are made by changing the symbol, explicitly.

**Voicing search.** For each chord, candidate voicings are enumerated inside an instrument's register window, filtered by span (playability) and classic low-interval limits (mud), scored for shape, then a dynamic-programming pass picks the sequence with the least voice movement — including the loop-back from the last chord to the first, which matters for loop-based music. A top-line option pins the highest voice to a melody, and `--bass-file` voices chords over the user's own bassline, keeping them an octave or more above it.

**Octave convention.** MIDI numbers are always shown; names default to Ableton's C3 = 60 so they match the Live piano roll (`--spn` for C4 = 60).

**Progressive disclosure.** `SKILL.md` is ~100 lines; references are 40–80 lines each and only loaded when a request needs them; genre files layer on top of general theory rather than replacing it.

## Testing and evaluation

- `scripts/tests/test_theory.py` — 44 unit tests: note/octave conventions, spelling and enharmonics, chord-symbol aliases, identity rules (e.g. no natural 11 in C13), identification and ambiguity, every voicing of 8 progressions × 6 styles validates and respects register/low-interval limits, voice leading beats naive block chords, top-line pinning, analysis (secondary dominants, tritone subs, borrowed chords, key guess), MIDI round trip, MCP JSON shapes, CLI exit codes, plus regressions for pushed chords, notes held across chord changes, MCP reply wrappers, 11th-chord voicings, #9 placement, user-supplied basslines, per-bar rhythm patterns, maj7 voicings that keep the root off the 7th, chord-aware note spelling in `identify`, cadence-weighted key guessing, and non-chord-tone labels.
- `evals/check_toolchain.py` — 38 checks mapped to the 10 required scenarios (progression generation, Rhodes voicings, bassline harmonisation, identification, three reharmonisations under a melody constraint, plain-language explanation inputs, melody validation, MIDI output, ambiguity, no-MCP delivery).
- `evals/evals.json` — 14 behaviour scenarios with assertions for grading Claude's actual responses (usable with the skill-creator eval loop). Assertions are typed `objective`, `subjective` or `subjective-listening`.

**What tests can't prove.** Passing checks means the notes are what they claim to be, sit in sensible registers, move smoothly and fit the stated chords. Whether a progression is *moving*, a melody *singable*, or a voicing *right for your patch and mix* needs listening: import the generated MIDI, play it with your actual sounds, and judge. Treat the subjective-listening assertions as a checklist for that pass.

## Known limitations

- The chord-symbol parser covers common jazz/pop notation (extensions, b5/#5/b9/#9/#11/b13, alt, sus, add, no3/no5, slash bass). Polychord notation such as `D/C7` (a triad stacked over a seventh chord) is rejected with an error; write it as the equivalent single symbol (`C13#11`).
- Identification is template-based: clusters, quartal stacks and passing-tone-heavy MIDI can return several plausible names or none; that ambiguity is reported, not hidden.
- Key estimation is heuristic (diatonic fit + light tonal-centre cues, and Krumhansl–Kessler for raw notes). Modal and relative-key ambiguity is flagged rather than resolved.
- Voicings are generated per chord style from a fixed set of six instrument profiles; patch-specific voicing (a particular Rhodes sample, a bright supersaw) still needs ears.
- Rhythm generation is basic (`--hits` per chord); complex comping, melodies and basslines are written by the model and then validated.
- 4/4 assumed for timelines and MIDI export; other meters work for note data but aren't tested.
- MCP behaviour varies by server; the skill guards with discovery and conservative write rules but can't verify a server's undocumented side effects.

## Possible future improvements

- Patch-aware voicing profiles (user-defined register/density per instrument, saved in a small JSON file).
- A rhythm/comping pattern library per genre that renders directly to clip JSON.
- Melody and bassline generators with motif transforms, still validated by the existing checker.
- Arrangement renderer: section map → multiple clips/scenes.
- Audio-aware checks via the MCP's analysis tools (e.g. key detection from audio, low-end masking between bass and keys).
