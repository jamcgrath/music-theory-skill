"""Minimal Standard MIDI File reader/writer (stdlib only).

Clip JSON format used throughout the skill (times in beats, 1 beat = quarter note):

    {"bpm": 174, "time_signature": [4, 4],
     "tracks": [{"name": "Rhodes", "channel": 0,
                 "notes": [{"pitch": 60, "start_time": 0.0, "duration": 4.0, "velocity": 80}]}]}

Note dicts use the same keys as Ableton MCP servers (pitch, start_time, duration, velocity, mute),
so a track's "notes" list can be passed straight to a note-writing MCP tool.
"""
from __future__ import annotations

import struct

PPQ = 480


def _vlq(n: int) -> bytes:
    out = [n & 0x7F]
    n >>= 7
    while n:
        out.append((n & 0x7F) | 0x80)
        n >>= 7
    return bytes(reversed(out))


def _track_chunk(events: list[tuple[int, int, bytes]]) -> bytes:
    events.sort(key=lambda e: (e[0], e[1]))
    data, last = bytearray(), 0
    for tick, _, payload in events:
        data += _vlq(tick - last) + payload
        last = tick
    data += _vlq(0) + b"\xff\x2f\x00"
    return b"MTrk" + struct.pack(">I", len(data)) + bytes(data)


def write_midi(clip: dict, path: str, track_filter: int | None = None) -> None:
    bpm = float(clip.get("bpm", 120))
    num, den = clip.get("time_signature", [4, 4])
    tracks = clip["tracks"] if track_filter is None else [clip["tracks"][track_filter]]
    chunks = []
    tempo = int(round(60_000_000 / bpm))
    den_pow = {1: 0, 2: 1, 4: 2, 8: 3, 16: 4}[int(den)]
    for i, tr in enumerate(tracks):
        ev: list[tuple[int, int, bytes]] = []
        name = tr.get("name", f"Track {i + 1}").encode("utf-8")[:120]
        ev.append((0, 0, b"\xff\x03" + _vlq(len(name)) + name))
        if i == 0:
            ev.append((0, 0, b"\xff\x51\x03" + tempo.to_bytes(3, "big")))
            ev.append((0, 0, bytes([0xFF, 0x58, 0x04, int(num), den_pow, 24, 8])))
        ch = int(tr.get("channel", 0)) & 0x0F
        for n in tr.get("notes", []):
            if n.get("mute"):
                continue
            p = int(n["pitch"])
            if not 0 <= p <= 127:
                raise ValueError(f"pitch {p} is outside MIDI range 0-127")
            v = max(1, min(127, int(n.get("velocity", 100))))
            if float(n["duration"]) <= 0 or float(n["start_time"]) < 0:
                raise ValueError(f"note {n} needs start_time >= 0 and duration > 0")
            on = int(round(float(n["start_time"]) * PPQ))
            off = int(round((float(n["start_time"]) + float(n["duration"])) * PPQ))
            if off <= on:
                off = on + 1
            ev.append((on, 2, bytes([0x90 | ch, p, v])))
            ev.append((off, 1, bytes([0x80 | ch, p, 0])))  # offs sort before ons at the same tick
        chunks.append(_track_chunk(ev))
    header = b"MThd" + struct.pack(">IHHH", 6, 1, len(chunks), PPQ)
    with open(path, "wb") as f:
        f.write(header + b"".join(chunks))


def _read_vlq(data: bytes, i: int) -> tuple[int, int]:
    n = 0
    while True:
        b = data[i]
        i += 1
        n = (n << 7) | (b & 0x7F)
        if not b & 0x80:
            return n, i


def read_midi(path: str) -> dict:
    with open(path, "rb") as f:
        data = f.read()
    if data[:4] != b"MThd":
        raise ValueError("not a Standard MIDI File")
    hlen = struct.unpack(">I", data[4:8])[0]
    fmt, ntrks, division = struct.unpack(">HHH", data[8:14])
    if division & 0x8000:
        raise ValueError("SMPTE-timed MIDI files are not supported")
    ppq = division
    i = 8 + hlen
    bpm, ts = 120.0, [4, 4]
    tracks = []
    for _ in range(ntrks):
        if data[i:i + 4] != b"MTrk":
            break
        length = struct.unpack(">I", data[i + 4:i + 8])[0]
        j, end = i + 8, i + 8 + length
        tick, status, name = 0, 0, None
        open_notes: dict[tuple[int, int], list[tuple[int, int]]] = {}
        notes = []
        while j < end:
            delta, j = _read_vlq(data, j)
            tick += delta
            b = data[j]
            if b == 0xFF:
                mtype = data[j + 1]
                mlen, k = _read_vlq(data, j + 2)
                payload = data[k:k + mlen]
                if mtype == 0x51 and mlen == 3:
                    bpm = round(60_000_000 / int.from_bytes(payload, "big"), 3)
                elif mtype == 0x58 and mlen >= 2:
                    ts = [payload[0], 2 ** payload[1]]
                elif mtype == 0x03:
                    name = payload.decode("utf-8", "replace")
                j = k + mlen
                continue
            if b in (0xF0, 0xF7):
                slen, k = _read_vlq(data, j + 1)
                j = k + slen
                continue
            if b & 0x80:
                status = b
                j += 1
            kind, ch = status & 0xF0, status & 0x0F
            nbytes = 1 if kind in (0xC0, 0xD0) else 2
            d = data[j:j + nbytes]
            j += nbytes
            if kind == 0x90 and d[1] > 0:
                open_notes.setdefault((ch, d[0]), []).append((tick, d[1]))
            elif kind == 0x80 or (kind == 0x90 and d[1] == 0):
                stack = open_notes.get((ch, d[0]))
                if stack:
                    on, vel = stack.pop(0)
                    notes.append({"pitch": d[0], "start_time": round(on / ppq, 6),
                                  "duration": round((tick - on) / ppq, 6), "velocity": vel, "mute": False})
        i = end
        if notes or name:
            notes.sort(key=lambda n: (n["start_time"], n["pitch"]))
            tracks.append({"name": name or f"Track {len(tracks) + 1}", "notes": notes})
    tracks = [t for t in tracks if t["notes"]]
    return {"bpm": bpm, "time_signature": ts, "format": fmt, "tracks": tracks}
