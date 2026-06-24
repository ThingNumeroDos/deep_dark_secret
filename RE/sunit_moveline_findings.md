# sUnit — Dynamic Object Manager (Move Lines)

## Overview

`sUnit` is the MT Framework singleton that manages all live dynamic objects (`u`-prefixed units).
It organizes objects into **32 linked lists called "move lines"**, each serviced by its own thread.
The thread handles three lifecycle phases for objects in its line: **init → tick → destruction**.

- `sUnit::mpInstance` = `0xE552CC`
- Registered size: **800 bytes** (= 32-byte header + 32 × 24-byte move line entries)
- Parent class: `MtDTI_cSystem`

---

## sUnit Struct Layout

```
+0x00 (4)   vtable          sUnit::vtable @ 0xBFF890
+0x04 (24)  CRITICAL_SECTION  threading guard
+0x1C (1)   bool            job-safe / running flag
+0x1D..1F   padding (3)
+0x20 (768) move_line[32]   array of 32 × 24-byte entries
```

### move_line[N] entry (24 bytes, at sUnit+0x20+N×24)

| Offset | Type | Content |
|--------|------|---------|
| +0x00 | ptr | `&off_BFF8D0` — sUnit_MoveLine vtable / line descriptor |
| +0x04 | ptr | Name string ptr (`"Line0"` … `"Line31"` — debug label) |
| +0x08 | DWORD | Flags: `bits[0]` = active; `bits[3:9]` = encoded line ID (set to `8*N`) |
| +0x0C | ptr | Head (top) of linked list — first object on this line |
| +0x10 | ptr | Tail (bottom) of linked list — last added object |
| +0x14 | float | Per-line delta-time multiplier (default 1.0f) |

The line ID is encoded into each **unit's own flags DWORD** at `unit+4` (bits [3:9] = `8*N`),
so any unit can report its own move line without querying sUnit.

---

## Unit Linked-List Node Layout (within each dynamic object)

Based on `sUnit::addBottom` and `sUnit::reset`:

| Offset in unit | Content |
|----------------|---------|
| +0x00 | vtable ptr |
| +0x04 | flags DWORD (bits 0-2 = lifecycle state; bits 3-9 = move line ID) |
| +0x08 | next ptr in linked list (null if this is the tail) |
| +0x0C | prev ptr in linked list (null if this is the head) |
| +0x10 | delta-time float (written by sUnit::move each frame) |

---

## Lifecycle State Machine

Driven by `sUnit::move` (vtable slot [8]):

| `flags & 7` | State | Action |
|-------------|-------|--------|
| 1 | INIT | Calls `vtable[5]` = `init()` at `+0x14`; transitions → ACTIVE (2) |
| 2 | ACTIVE | Calls `vtable[6]` = `tick()` at `+0x18` each frame (if flag 0x400 set) |
| 3 | PENDING_KILL | Transitions → KILLING (4) |
| 4 | KILLING | Calls `vtable[0](unit, 1)` (destructor); removes from list |
| 0 | DEAD | Not visited |

`killAll` (vtable slot [12] on each unit = `kill()` at `+0x30`) force-transitions all objects on a
line to DEAD and clears the list.

---

## Key API

| Function | Address | Role |
|----------|---------|------|
| `sUnit::addBottom(line, unit, ?)` | `0x8DC540` | Add unit to the TAIL of move line `line` |
| `sUnit::killAll(line)` | `0x8DC6F0` | Kill every unit on move line `line` |
| `sUnit::move(this, lineIdx)` | `0x8DC290` | Per-frame lifecycle dispatch for line `lineIdx` |
| `sUnit::reset` | `0x8DC1E0` | Destroy all units on all 32 lines and clear list ptrs |

---

## Move Line Assignment Map

From enumerating all 401 `sUnit::addBottom` call sites (pattern: `push <N>` before call):

| Line | Entity Category | Key Callers / Evidence |
|------|----------------|----------------------|
| 0 | Player (variant) / benchmark objects | `sGameState::player_spawn_state` |
| 1 | Room persistent entities | `aRoom::setRoom` |
| 2 | UI / demo scripted objects | `aRoom::demo`, state machine objects |
| 3 | Player secondary state objects | `sWorkRate::calc` caller, player-adjacent |
| 4 | — | small set, enemy-range addresses |
| 5 | — | `sub_757E00` only |
| 6 | — | `sub_4ABE50` only |
| 7 | Schedulers / resource loaders | `uScheduler`, `sResource::create` |
| 8 | — | two callers in 0x6E/0x88 range |
| 9 | — | `sub_4822D0`, `sub_870820` |
| 10 | Game-state / mission HUD objects | multiple 0x404/0x88C callers |
| 11 | Collision resource objects | `sCollision::registResource`, `sCollisionGame::SetScrAttribute` |
| 12 | (no call sites found) | — |
| **13** | **Player (uPlayerNero / uPlayerDante)** | `sGameState::player_spawn_state`, `aRoom::setRoom` |
| 14 | Player sub-object (Nero-specific?) | `sub_7E2C10` (0xAE4 bytes; 0x7Exxxx = uPlayerNero range) |
| 15 | Enemies (batch 1) | `sub_5EE690`, `sub_631FD0`, `sub_698690` |
| 16 | Enemies (main batch) | 20+ enemy-spawn functions (0x457/0x544/0x5B8…) |
| 17 | (no call sites found) | — |
| 18 | Enemies (main batch 2) | 20+ enemy-spawn functions (0x54D/0x5A3/0x5B2…) |
| 19 | — | `sub_6BE920` |
| 20 | Effects / footprints | `cFootprintCtrl::update`, many 0x5/0x6/0x7 range |
| 21 | Animation / particle VFX? | `sub_831280` → `sub_535100`, `sub_537EF0` |
| 22 | Camera objects | `uDevilCamera::vibReq`, camera vibration factories |
| 23 | Room triggers / scripted actors | `aRoom::setRoom`, camera + trigger range |
| 24 | — | `sub_404940`, `sub_631FD0` |
| 25 | Collision / room geometry | `aRoom::setRoom`, `sCollision`-adjacent callers |
| 26 | Mission / game state | `aMission::load`, `sGameState::player_spawn_state` |
| 27 | UI / fades / HUD | `sMediator::setFadeOut`, `sMediator::setFade` |
| 28 | Random / procedural seed | `MtRandom::nextTable` caller |
| 29 | Room sub-objects | `sub_40BB10`, `sub_40D120` |
| 30 | — | `sub_710D30`, `sub_74FB90` |
| 31 | Room boundary / final | `aRoom::setRoom` |

---

## Multiplayer Relevance

**Line 13 = the player line.** For N-player support, each player instance must live on its own
move line (or the engine must support more than one object per player line).

The move line threading model means each player's per-frame `tick()` + `init()` + `kill()` 
is naturally isolated — but every *cross-line* system (enemies on 15/16/18, camera on 22,
HUD on 27) holds a single `sMediator::mpPlayer` pointer and would need to index by player.

The **enemy lines (15–16, 18)** are the highest-volume callers of `sMediator::mpPlayer` — every
enemy AI tick reads the singleton to find its target. Multiplayer will require a per-target query
(`getNearestPlayer()` or explicit player-index routing) at those sites.
