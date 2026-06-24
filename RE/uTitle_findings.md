# uTitle / uTitlePc — Main Menu / Title Screen UI

## Class Hierarchy

```
MtObject → cUnit → uCoord → uModel → uActor → uTitle
                                                 └── uTitleA   (sub-component)
                                                 └── uTitleB   (sub-component)
                                                 └── uTitleC   (sub-component)
                                                 └── uTitlePc  (sub-component, PC-specific)
```

`uTitle` is the root title-screen controller. It owns embedded instances of the four
sub-component classes at fixed offsets (see layout below). The sub-components manage
individual animated logo sprites and the PC-specific button prompt overlay.

---

## DTI Registration

| Class     | Size (bytes) | DTI global   | Vtable addr | ctor reg fn |
|-----------|-------------|--------------|-------------|-------------|
| `uTitleA` | 52 (0x34)   | `dword_E5BD70` | `0xBF86B4` | `sub_B798E0` |
| `uTitleB` | 52 (0x34)   | `dword_E5BD50` | `0xBF871C` | `sub_B79920` |
| `uTitleC` | 52 (0x34)   | `dword_E5BD90` | `0xBF8784` | `sub_B79960` |
| `uTitlePc`| 116 (0x74)  | `dword_E5BD10` | `0xBF8840` | `sub_B799A0` |
| `uTitle`  | 664 (0x298) | `dword_E5BD30` | `0xBF88F8` | `sub_B799E0` |

All sub-components (`uTitleA/B/C`) inherit from `uTitle` (parent DTI arg = 2 in
`sub_8B69B0`). `uTitle` is a root class (parent arg = 0).

**DTI note:** `uTitlePc::getDTI` (vtable slot 6) returns `&dword_E5BD30` = `uTitle::DTI` — the *parent's* DTI, consistent with the MT Framework rule that `getDTI()` returns the parent DTI. `uTitlePc::DTI` (its own) is at `dword_E5BD10`.

---

## uTitle Layout (664 bytes, from `sub_898870` init + `sub_898D90` property registration)

| Offset | Size | Type       | Name / Notes |
|--------|------|-----------|--------------|
| +0x000 | 4    | vtable*   | `off_BF88F8` (`uTitle` vtable) |
| +0x004 | —    | —         | inherited `cUnit`/`uCoord` fields |
| +0x014 | 1    | byte      | `+(this+5)` — state machine index (`*(this+5)`, cases 0–0xF) |
| +0x018 | 1    | byte      | fade-in sub-state (`*(this+21)`) |
| +0x01C | 1    | byte      | sub-state 2 (`*(this+22)`) |
| +0x03C | 4    | int       | `*(this+27)` — pointer to asset-load trigger object |
| +0x060 | 4    | int       | `*(this+34)` — optional live unit pointer (validated by cUnit status bits & 7 ∈ {1,2}) |
| +0x064 | 4    | int       | `*(this+33)` — optional live unit pointer (same validity pattern) |
| +0x068 | 4    | int       | `*(this+35)` — optional live unit pointer |
| +0x06C | 4    | int       | `*(this+36)` — sub-object (vtable at +0x90; `destroy` at vtbl+48 called on teardown) |
| +0x090 | 4    | int       | `*(this+49)` — sub-object (same teardown pattern) |
| +0x0B4 | 4    | int       | `*(this+62)` — sub-object |
| +0x0D8 | 4    | int       | `*(this+75)` — sub-object |
| +0x06C | 4    | int       | `*(this+31)` — used in state 8: `sub_489780` (mission result?) |
| +0x088 | 4    | int*      | `*(this+34)` — sResource handle (title texture) |
| +0x06C | 4    | int       | `[+0x6C]` = `*(this+27)` pointer to load-state object |
| +0x090 | 4    | vtable*   | `+0x90` = `uTitleA` embedded instance (set to `&uTitleA::vftable`; size 0x34 = 52 B) |
| +0x0B8 | —    | —         | padding/`uTitleA` extent |
| +0x0C4 | —    | —         | `+0xC4` = `uTitleA` instance end |
| +0x0B8 | 4    | vtable*   | `a1+184` = embedded sub-object (vtable `off_BF8848`) |
| +0x0C0 | 4    | int       | `a1+192` = 0 |
| +0x0BC | 4    | int       | `a1+188` = 3 |
| +0x090 | 4    | vtable*   | `a1+144` = **mTitleA** (`uTitlePc::vftable` instance, prop offset 144) |
| +0x0C4 | 4    | vtable*   | `a1+196` = **mTitleB** (`off_BF86C0`, size param 0x1A4) |
| +0x0F8 | 4    | vtable*   | `a1+248` = **mTitleC** (`uTitleA::vftable` instance, size param 0x1A7) |
| +0x12C | 4    | vtable*   | `a1+300` = **mTitlePc** (`off_BF8790`, size param 0x2FD) |
| +0x168 | 4    | int       | `a1+360` = 4 (init constant) |
| +0x190 | 4    | ptr       | `a1+400` = `&unk_C385C0` (texture/resource table ptr) |
| +0x19C | 4    | int       | `a1+412` = 1 |
| +0x28C | 1    | byte      | `a1+652` = 1 (init flag) |
| +0x006 | 1    | byte      | `a1+6` = 1 |

### Property-registered fields (from `sub_898D90`)

| Offset | MtProperty type | Name        | Notes |
|--------|----------------|-------------|-------|
| +0x1A0 | 12 (float)     | `mFTimer0`  | fade timer at `param_3 + 416` |
| +0x1A8 | 10 (int)       | `mMenuNo`   | active menu index at `param_3 + 424` |
| +0x1AC | 4 (byte)       | `mBright`   | brightness at `param_3 + 428` |
| +0x1AD | 4 (byte)       | `mBright2`  | secondary brightness at `param_3 + 429` |
| +0x278 | 15 (color?)    | `mBlackColor` | fade-to-black color at `param_3 + 632` |
| +0x090 | 1 (sub-object) | `mTitleA`   | embedded `uTitleA` at `param_3 + 144` |
| +0x0C4 | 1 (sub-object) | `mTitleB`   | embedded `uTitleB` at `param_3 + 196` |
| +0x0F8 | 1 (sub-object) | `mTitleC`   | embedded `uTitleC` at `param_3 + 248` |
| +0x12C | 1 (sub-object) | `mTitlePc`  | embedded `uTitlePc` at `param_3 + 300` |
| +0x290 | 12 (float)     | `mShiftX`   | horizontal shift at `param_3 + 656` |

---

## uTitlePc Layout (116 bytes, vtable `0xBF8840`, from `sub_898870`)

Embedded at `uTitle+0x12C`. Manages PC-specific button-prompt overlay (main_button textures).
Constructor: `0x895580`. Allocates via `UnitAllocator` with slot 0x10, size 0x74.

Key init fields set at `0x898870` / `0x895580`:
- `[+0x000]` vtable = `0xBF8840`
- `[+0x028]` = 0
- `[+0x02C]` = 3  (cUnit status)
- `[+0x030]` = 0
- `[+0x064]` = `0xC8` (from `sub_4AD7C0(0xC8)` — move-line index or priority)

---

## uTitle Vtable (`0xBF88F8`) — 2 slots

| Slot | Offset | Address    | Name / Role |
|------|--------|------------|-------------|
| 0    | +0x00  | `0x410360` | `sMediator::sMediator` (shared MtObject ctor slot) |
| 1    | +0x04  | `0x895550` | factory/allocator — allocates 0x298 bytes via `UnitAllocator`, calls `sub_898870` |

---

## uTitlePc Vtable (`0xBF8840`) — 46 real slots

Mapped against standard MtObject vtable convention (+0x10 = getDTI, +0x14 = init, +0x18 = tick, +0x78 = behaviour):

| Slot | Offset | Address    | Name / Role |
|------|--------|------------|-------------|
| 0    | +0x00  | `0x410360` | shared MtObject ctor |
| 1    | +0x04  | `0x895530` | factory/allocator (fails decompile — raw alloc stub) |
| 2    | +0x08  | `0x898A50` | unknown (decompile failed) |
| 3    | +0x0C  | `0x8FC2F0` | sub_8FC2F0 |
| 4    | +0x10  | `0x42BAF0` | `cUnit::isEnable` — **getDTI slot** |
| 5    | +0x14  | `0x898D90` | **init / property registration** — registers `mFTimer0`, `mMenuNo`, `mBright`, `mTitleA`…`mTitlePc`, `mShiftX` |
| 6    | +0x18  | `0x895420` | **getDTI** — returns `&dword_E5BD30` (uTitle's DTI global) |
| 7    | +0x1C  | `0x899250` | **randomised character select** — reads `sSave+0x394` unlock flags, Mersenne-Twister RNG picks starting character, stores at `[this+648]`, loads title texture via `sResource::create` |
| 8    | +0x20  | `0x899390` | **main per-frame tick / state machine** — 16 states (0–0xF); accesses `sMediator`, `sDevil4Pad`, `sDevil4Main` |
| 9    | +0x24  | `nullsub_2` | no-op |
| 10   | +0x28  | `nullsub_2` | no-op |
| 11   | +0x2C  | `uDevilCock::draw` | draw dispatch |
| 12   | +0x30  | `0x46D740` | sub_46D740 |
| 13   | +0x34  | `0x8E57E0` | sub_8E57E0 |
| 14   | +0x38  | `0x899090` | **destroy / teardown** — kills embedded sub-unit pointers at `[+0x88]`, `[+0x84]`, `[+0x8C]`, `[+0x90]`, `[+0xC4]`, `[+0xF8]`, `[+0x12C]`, `[+0x294]`; clears cUnit status to dead(3) |
| 15   | +0x3C  | `0x8991E0` | sub_8991E0 |
| 16   | +0x40  | `0x521BF0` | sub_521BF0 |
| 17   | +0x44  | `nullsub_2` | no-op |
| 18   | +0x48  | `0x899530` | mirrors state machine (same body as slot 8 — thunk?) |
| 19   | +0x4C  | `0x76D2E0` | sub_76D2E0 |
| 20   | +0x50  | `0x5341D0` | sub_5341D0 |
| 21   | +0x54  | `0x89CDF0` | sub_89CDF0 |
| 22   | +0x58  | `0x895430` | sub_895430 |
| 23   | +0x5C  | `0x895460` | sub_895460 |
| 24   | +0x60  | `0xB2C9A0` | sub_B2C9A0 |
| 25   | +0x64  | `0x7A2B10` | sub_7A2B10 |
| 26–30| +0x68–0x78 | `nullsub_2` | no-ops |
| 31   | +0x7C  | `0x76D340` | **behaviour** — checks `sDevil4Pad` confirm button OR vtbl+148/152 confirm — title-screen "press start" detection |
| 32   | +0x80  | `0x76D3B0` | sub_76D3B0 |
| … | … | … | … |
| 45   | +0xB4  | `0x4AD860` | sub_4AD860 (probable destructor) |

---

## State Machine (slot 8 / `sub_899390`)

`*(this+5)` (byte) drives 16 sequential states:

| State | Description |
|-------|-------------|
| 0     | Wait for asset load (`*(this+27)` object, flag bit 0 at +0x4C); when ready, calls vtbl+64; if `*(this+162)` == 0 calls `sub_4955F0` (level unload?) |
| 1     | Fade-in animation: accumulates timer via `sDevil4Main` time step; drives child sub-units' alpha (`*(this+35)` at +611); sets `mBright` (`[+0x1AC]`). Clamps to 30.0 frames then transitions to state 3 |
| 2     | `sub_8999E0` |
| 3     | `sub_89A310` |
| 4     | Transition: sets state=5; drives button-prompt child unit at vtbl+104 (`[this+27][+104]`) |
| 5     | Sets state=6 |
| 6     | `sub_89A900` |
| 7     | `sub_89B1B0` |
| 8     | Calls `sub_489780` on `*(this+31)` if non-null |
| 9     | `sub_89B690` |
| 0xA   | `sub_89BEB0` |
| 0xB   | `sub_89C1A0` |
| 0xC   | `sub_89CC20(this)` |
| 0xD   | `sub_89AAF0(this)` |
| 0xE   | `sub_89D5C0` |
| 0xF   | `sub_89D7A0` |

State 1 also sets `sMediator::mpInstance->member_0x4B4 = 1` (signals mediator that title is active)
and acquires the mediator critical section around the write.

---

## Character Select Randomisation (`sub_899250` / vtable slot 7)

Reads `sSave::mpInstance + 0x394` — a bitmask of unlocked characters (bits 0–6 = Nero + 6 bonus chars).
Builds a compact array of available indices, then uses a Mersenne Twister (`dword_EAC6B0`/`dword_EAD070`)
to pick one at random. Result stored at `[this+648]`. If result == 0 (Nero), calls `sub_495590(a1, 0.0)`.
Finally, `sResource::create(&dword_EAD4A0, off_C385D0[selected], 2)` loads the character's title texture;
handle stored at `[this+108]`.

---

## Teardown (`sub_899090` / vtable slot 14)

Destroys embedded sub-units by calling vtbl[+48] (destroy virtual) on each pointer, then nulls them:
- `*(this+34)`, `*(this+33)`, `*(this+35)`
- Four fixed sub-objects at `this+36`, `this+49`, `this+62`, `this+75`
- `*(this+165)`

Then clears `*(this+1) & 7` status bits to 3 (dead) unless the unit has flag `0x2000` set.

---

## "Press Start" Detection (`sub_76D340` / vtable slot 31 / behaviour)

Returns `true` if any of:
1. `sDevil4Pad::mpInstance->mPadInfo[0].mBtn.trg & sDevil4Pad::mpInstance->sPadBase.mDecideButton` (pad confirm)
2. Virtual call at `*(vtable + 148)(this)` returns 1
3. Virtual call at `*(vtable + 152)(this, 0, 0, 0)` returns 1

---

## Key Addresses Summary

| Symbol | Address |
|--------|---------|
| `uTitle` ctor/factory | `0x895550` |
| `uTitle` init body (`sub_898870`) | `0x898870` |
| `uTitle` DTI reg | `sub_B799E0` @ `0xB799E0` |
| `uTitlePc` vtable | `0xBF8840` |
| `uTitlePc` init (property reg) | `sub_898D90` @ `0x898D90` |
| `uTitlePc` state machine | `sub_899390` @ `0x899390` |
| `uTitlePc` char select/random | `sub_899250` @ `0x899250` |
| `uTitlePc` teardown | `sub_899090` @ `0x899090` |
| `uTitlePc` behaviour ("press start") | `sub_76D340` @ `0x76D340` |
