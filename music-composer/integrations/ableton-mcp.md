# Ableton Live via an MCP server (optional)

The skill works without any DAW connection. When an Ableton MCP server is available, use it to read context and write **new** clips. The skill's verified notes are always the source; the server is just the transport.

## 1. Discover, don't assume

1. Look at the tools actually available. Ableton servers appear under names like `AbletonMCP`, `ableton-live`, `ableton-mcp`, sometimes behind a prefix (e.g. `mcp__AbletonMCP__…`, `mcp__remote-devices__AbletonMCP__…`). If the server offers a self-description tool (e.g. `describe_capabilities`), call it first — it states conventions such as which calls replace content.
2. Map what you need by *intent*, then read each candidate tool's description before using it:

| Intent | Typical names | Check in the description |
|---|---|---|
| Session overview (tempo, tracks, devices) | `get_session_snapshot`, `get_session_info` | read-only |
| Track details / which clip slots are empty | `get_track_info` | slot list |
| Read notes from a Session clip | `get_clip_notes`, `get_notes` | read-only; Session vs Arrangement |
| Read Arrangement clips | `get_arrangement_clips` | may return clip refs, not notes |
| Read a saved set offline | `als_extract_midi`, `als_list_tracks` | works with Live closed |
| Key/scale of the set or a clip | `get_scale_info`, `detect_clip_key`, `detect_session_key` | estimate only |
| Create a clip | `create_clip` | should *fail* on an occupied slot (good) |
| Write notes | `add_notes_to_clip`, `set_notes`, `edit_notes` | **replace vs append** |
| Name a clip / track | `set_clip_name`, `set_track_name` | |
| New MIDI track | `create_midi_track` | |
| Copy a clip | `duplicate_clip_to`, `duplicate_clip` | **may overwrite the destination** |
| Built-in generators | `generate_chord_progression`, `generate_voiced_progression`, `generate_melody`, `generate_bassline`… | usually **replace** clip contents |

3. If a needed capability is missing (e.g. no note reading), say so in one line and use the fallback (§6).

## 2. Safety rules

- **Never overwrite or modify existing musical material without explicit permission.** Explicit means the user named the clip/track and asked for it to be changed ("replace the chords in the Rhodes clip", "yes, overwrite slot 2"). "Make it better" is not permission to overwrite.
- **Treat any note-writing call on an existing clip as destructive** unless its description clearly says it only appends. Several servers' `add_notes_to_clip` *replaces all notes* (at least one widely used server says so explicitly in its tool description), and generator tools replace clip contents.
- **Default target: a new clip in an empty slot.** Prefer the same track as the material it varies (so it uses the same instrument), else a new MIDI track. Confirm the slot is empty with the track info before creating; rely on `create_clip` refusing occupied slots as a second guard.
- **Copies**: before duplicating, check the destination slot is empty — duplicate tools often overwrite.
- **Don't use the server's generators to stand in for the skill's musical choices.** If the user wants a quick generated idea from the server specifically, say it will write into a clip and choose an empty slot.
- Never delete clips, tracks or devices, or change mix/device settings, as part of composition work.
- Transport (play/stop/fire clip) only when the user asks to audition.

## 3. Reading existing material

1. `get_session_snapshot` (or equivalent) for tempo, track names, devices — tells you which track is bass, keys, pads.
2. Read notes with the clip-notes tool. Save the raw result to a JSON file in the working directory.
3. Analyse: `python3 ${CLAUDE_SKILL_DIR}/scripts/mc.py notes clip.json` (it accepts the MCP's JSON as-is, including `{"result": "<json string>"}` wrappers and `start`/`start_time` keys). For a bass or melody clip add `--window 4`.
4. For "what chords work with my bassline": also read the chord/keys clips if any; run the bassline procedure in `references/basslines.md`.
5. Report what you found in musical terms (chords per bar, key candidates, ambiguities) before proposing changes.

## 4. Writing a new idea

1. Generate and verify notes: `mc.py --json voice "<progression>" --style <style> --bpm <tempo>` (or write melody/bass notes and `validate` them). The JSON's `clip.tracks[i].notes` items already use the MCP note shape: `pitch`, `start_time`, `duration`, `velocity`, `mute` — in beats, `pitch` 60 = C3 as in Live.
2. Pick the target: an empty slot on the relevant track, or a new MIDI track (name it, e.g. "MC Rhodes").
3. `create_clip(track, empty_slot, length_in_beats)` — length = the progression length (`clip.length_beats`).
4. Write the notes into **that new clip only**.
5. Name the clip after the idea and version: "A – Minor drift", "B – tritone turnaround".
6. **Verify the round trip**: read the clip's notes back, save to JSON, run `mc.py validate back.json --chords "<progression>" --role chords` (or `--role bass|melody`). Report any mismatch.
7. Tell the user where it is (track name, slot/scene number) and that nothing existing was changed. Mention if the track has no instrument loaded; load one only if asked.

Separate parts (chords, bass, melody) go to separate clips/tracks so they can be muted and swapped independently.

## 5. Variations of an existing clip

Read the original → generate the variation (preserving what the user wants kept) → write it to a **new** empty slot on the same track, named "<original name> – var B". The original stays untouched. If the user explicitly wants the original replaced, confirm once, then (when possible) duplicate the original to an empty slot first as a backup.

## 6. Fallback: no MCP, missing capability, or user preference

- Deliver `.mid` files: `mc.py voice "<progression>" --mid idea.mid` writes one file per part (`idea-rhodes-chords.mid`, `idea-bass.mid`); `mc.py midi-write clip.json out.mid --split` for hand-written parts. Tempo is embedded; files drop straight into Live (Session slot or Arrangement).
- Always also give the note table (names, MIDI numbers, beats) so the idea survives without any file.
- For analysis without an MCP: the user can drag a clip out of Live to save it as `.mid`, then share it; or paste note names/MIDI numbers.

## 7. Conventions recap

- Indices from the server are usually 0-based; times and lengths in beats (4.0 = one 4/4 bar).
- Pitch numbers are standard MIDI; Live labels 60 as C3, same as this skill's default naming.
- Velocities 1–127; keep keys parts varied (the script uses one value; humanise in Live or vary ±10 by hand).
