# Relay — Debugger → Planner — card firmware builds: reproducible hash check — 2026-10-26

For the Planner. This is build work the debug track needs; the Debugger does not implement it. The relay holds pointers only. The finding is in the V7R-014 raw notes.

## 1. Problem

- **Card firmware deltas are approved by a hash** of `firmware.bin` (`lab/evidence/V7R-0NN/src/u3/firmware.sha256`; V7R-012, V7R-014). Each session rebuilds the image from the committed sources in its own scratchpad and is expected to match that hash before flashing.
- **The same sources don't give the same hash when built from a different folder.** On 2026-10-26, V7R-014's `u3-static` rebuilt from `lab/evidence/V7R-014/src/u3/` gave `b3205a0b…`. A second rebuild using the original layout gave `0a31c4a6…`. The approved hash is `493a0235…`.
- **Cause, from the diff:**
  - Every loadable segment is byte-identical.
  - The image differs only at `0xb0–0xcf` (the embedded ELF SHA256, `--elf-sha256-offset 0xb0`) and in the last 33 bytes (the checksum and the appended SHA256).
  - In the ELF, only `.debug_line` and `.debug_str` differ. They carry the absolute build folder (it includes the session's scratchpad UUID) and the generated sketch name (`src/<name>.ino.cpp`).
- **Effect:** a whole-file hash check fails on every new session, even when the code is unchanged. It also can't tell a path-only difference apart from a real code change without a manual diff.
- **Second, related gap:** the approved binary currently exists only in the building session's scratchpad (`/private/tmp/…/scratchpad/`). If that is cleared, the hash can no longer be met.

## 2. Ask

- **Make the check pass for a path-only difference and fail for any other.** Two possible routes:
  - (a) Make card builds path-independent: `-ffile-prefix-map=<project>=.` (or `-fdebug-prefix-map`) in the card's `platformio.ini`, plus a fixed sketch file name.
  - (b) Keep the builds as they are, and hash only the image's loadable segments (header and segments, excluding the ELF-SHA field and the trailer). Record that hash next to, or in place of, the whole-file hash.
  The Planner chooses; (a) changes the approved build flags, so it applies to new cards only, never to an already-approved image.
- **A small tool** (e.g. `tools/lab/fw_check.py <project dir> <sha file>`) that builds in a scratch folder, compares the result and prints which ranges differ. Tests in `tools/lab/tests/`.
- **Decide where flashed card images are kept** so they survive the building session: in `lab/evidence/` (about 285 KB each), in a backed-up folder outside git like `lab/captures/`, or nowhere, relying on a reproducible rebuild.

## 3. Check

- On V7R-014's committed sources, the new check must accept the original `493a0235…` image and the two rebuilds (`b3205a0b…`, `0a31c4a6…`) as the same code.
- It must reject an image built with a one-line change to `v7_static_low.ino`, and also V7R-012's `u3-drv2` against `u3-drv3`.

## 4. Not asked

- No change to V7R-014's approved image or card; V7R-014 flashes the original `493a0235…` binary.
- No change to `capture.py`, `check_state.py` or the pre-commit hook.
