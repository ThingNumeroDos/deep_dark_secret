# uDevilCock — Sprite/UI Cockpit Widget Base Class

## Class Hierarchy

```
MtObject (0x4) → cUnit (0x18) → uSprLayout (0x28) → uDevilCock (0x34)
                                                     → uAreaName, uBMSub, uBPResultBack, uBPResultSuji
                                                     → uBossCock, uButton, uCapLogo, uCinemaScope
                                                     → uCockpit, uCockSuji, uCockpitSub, uDemoButton
                                                     → uDemoSpr, uGameOverBg, uGameOverSuji, uCockSuji02
                                                     → uHddInstall, uLbryModelTitle, uLbryMovieTitle
                                                     → uLbrySelectIcon, uLicence, uLicencePc
                                                     → uListSelect, uLoadMessage, uLockOnDante
                                                     → uMapData, uMapMgr, uMinimap, uResultBack
                                                     → uResultSuji, uMStartSuji, uMStartString1/2
                                                     → uModeClear, uNowLoading, uNowLoadingTex
                                                     → uKiri, uOption, uParaAnm, uPcBenchCock
                                                     → uPowerUpBg, uPowerUpMgr, uScreenBreak
                                                     → uSecretClear, uSecretFailed, uSkillListMgr
                                                     → uStaffRoll, uTgsDemoComing
                                                     → uTitleA, uTitleB, uTitleC, uTitlePc → uTitle
                                                     → uTRResultSuji, uTutorial, uTutorialGame
                                                     → uUseItemBg, uViolence, …
```

`uDevilCock` is the **universal base class for all HUD/UI cockpit widgets** in DMC4 DX9 —
every 2D sprite-based UI element (HUD cockpit, menus, result screens, titles, tutorials)
inherits from it. `uSprLayout` is its direct parent and holds the move-line/scheduling layer.
`uDevilCock` adds the resource handle, sprite-map, sprite animator, and font-layout arrays.

**Note:** `uDevil4Cock` does not exist as a registered DTI class in the DX9 binary. No string match found — this name was DX9-only noise or a misread.

---

## DTI Registration

### `uDevilCock`

| Field       | Value |
|-------------|-------|
| Class name  | `"uDevilCock"` @ `0xBC8CAC` |
| Size        | 52 bytes (`0x34`) |
| Parent DTI  | `uSprLayout::DTI` @ `0xE5B610` |
| DTI global  | `uDevilCock::DTI` @ `0xE58898` |
| Vtable      | `uDevilCock::vftable` @ `0xBF0810` |
| DTI init fn | `uDevilCock::DTI::init` @ `0xB71770` |

**Note:** Slot 4 contains `uSprLayout::getDTI` (`0x85F680`) — `uDevilCock` does not override `getDTI`, so it inherits `uSprLayout`'s stub. This is a normal pattern; `uDevilCock::DTI` at `0xE58898` is confirmed as its own DTI.

### `uSprLayout`

| Field       | Value |
|-------------|-------|
| Class name  | `"uSprLayout"` @ `0xBF07DC` |
| Size        | 40 bytes (`0x28`) |
| Parent DTI  | `cUnit::DTI` @ `0xEAD540` |
| DTI global  | `uSprLayout::DTI` @ `0xE5B610` |
| getDTI stub | `uSprLayout::getDTI` @ `0x85F680` |
| DTI init fn | `uSprLayout::DTI::init` @ `0xB78AE0` |
| No own vtable | `uSprLayout` has no distinct vftable in .rdata — `uDevilCock`'s vtable contains `uSprLayout::getDTI` at slot 4 because `uDevilCock` inherits it without override |

### `rSprLayout` (resource type)

| Field | Value |
|-------|-------|
| Class name | `"rSprLayout"` @ `0xB9D308` |
| Size | 120 bytes (`0x78`) |
| Parent | `cResource` @ `0xEAD4C0` (size 0x60) |
| Vtable | `rSprLayout::vftable` @ `0xB9D378` |
| DTI global | `rSprLayout::DTI` @ `0xE57D38` |

---

## Layouts

### `uSprLayout` (40 bytes, `cUnit` subclass)

`uSprLayout` adds 40 − 24 = **16 bytes** beyond `cUnit` (which is 0x18 = 24 bytes).
Its own constructor was not separately found — it may be inlined into `uDevilCock::uDevilCock`.
The `createProperty` registered for `uSprLayout` (via `sub_8E57F0`, the shared base createProperty)
covers the `cUnit`-inherited fields:

| Property | Offset | MtProp type | Flags | Notes |
|----------|--------|-------------|-------|-------|
| `Unit`   | `this` | 0x19 (GROUP) | 6 | group header |
| `Name`   | — | 0x0E (STRING) | 0x83 | get = `sub_8E5B30`, set = no-op |
| `mMoveLine` | — | 6 (U32) | 0x81 | get = `sub_4FB640`, set = `sub_8E57C0` |
| `mRno`   | `this+0x14` | 6 (U32) | 1 | |
| `Move`   | `this` | 3 (BOOL) | 0x80 | get = `sub_450730`, set = `loc_4090F0` |
| `Trans`  | `this` | 3 (BOOL) | 0x80 | get = `sub_5347E0`, set = `sub_44A380` |
| (unnamed) | `this` | 3 (BOOL) | 0x80 | get = `sub_42BAE0`, set = `sub_402C10` |
| `mTransView` | — | 6 (U32) | 0x80 | get = `loc_43AF90`, set = `sub_8E57B0` |
| `mTransMode` | — | 6 (U32) | 0x80 | get = `sub_57ED40`, set = `sub_7A5690` |
| `mDeltaTime` | `this+0x10` | 0x0C (F32) | 1 | |
| `Default` | `this` | 0x1F (GROUP_END) | 2 | |

These are the `cUnit`/`cTrans` scheduling properties (move-line, name, enable-flags, delta time).

### `uDevilCock` (52 bytes, verified from DX9 constructor `uDevilCock::uDevilCock` @ `0x85F6C0`)

| Offset | Size | Type    | Name           | Notes |
|--------|------|---------|----------------|-------|
| +0x00  | 4    | vtable* | `__vftable`    | `uDevilCock::vftable` @ `0xBF0810` |
| +0x04  | 2    | WORD    | `_cunit_status`| `& 0xFFFF0000 | 0x4DF9` — cUnit init pattern |
| +0x06  | 1    | BYTE    | `mEnable`      | 0 during init, set to 1 after resource alloc |
| +0x07  | 1    | BYTE    | `mMoveLine`    | move-line slot = 15 |
| +0x08  | 4    | ptr     | `mpNextPtr`    | linked-list next pointer (zeroed in ctor) |
| +0x0C  | 4    | int     | `_pad0c`       | zeroed |
| +0x10  | 4    | float   | `_scale`       | 1.0f init (`1065353216`) |
| +0x14  | 4    | int     | `_pad14`       | high QWORD of `_scale` write (= 0) |
| +0x18  | 4    | ptr     | `mpResource`   | `rSprLayout*` — resource handle; zeroed in ctor |
| +0x1C  | 4    | ptr     | `mpData`       | `sprMap*` — zeroed in ctor |
| +0x20  | 4    | ptr     | `mpDispSprMap` | `sprMap**` array — allocated in ctor (72 bytes/entry via `sub_45A2F0`) |
| +0x24  | 4    | ptr     | `mpSprAnm`     | `cSprAnm*` — zeroed in ctor |
| +0x28  | 4    | int     | `_pad28`       | |
| +0x2C  | 4    | int     | `_pad2c`       | |
| +0x30  | 4    | int     | `_pad30`       | |

**cTrans note:** `uDevilCock::dtor` restores `*this = &cTrans::vftable_0` before freeing, indicating `cTrans` is embedded in (or is the base of) `uSprLayout`/`uDevilCock`. This is consistent with the cUnit scheduling properties exposed in `createProperty` — `cTrans` sits inside `cUnit` at offset 0x00 (the vtable slot, `cTrans::vftable_0` shared with `uDevilCock`'s own `vftable` as the base).

SE field names confirmed via PDB: `mStatus`, `mpNextPtr`, `mpDispSprMap`, `mpResource`, `mpData`, `mpFontData`, `mpSprAnm`. DX9 offsets derived from ctor and `createProperty` disasm — SE offsets are +28B larger throughout, not usable as ground truth.

### `loadResource_impl` internal array element sizes

Two heap arrays are allocated inside `uDevilCock::loadResource_impl` (`0x85FA70`):

| Array field | Element size | Count source | Element vtable |
|-------------|-------------|--------------|----------------|
| `mpDispSprMap` (`this+7`) | 72 bytes | `*(mpResource+104)` | `sub_479CB0` ctor |
| `mpFontData` (`this+9`) | 48 bytes | `*(mpResource+108)` | `rSprLayout::vftable` @ `0xB9D378` |

Each `mpFontData` entry (48 bytes, vtable `rSprLayout::vftable`) has these known fields:
- `+0x00`: vtable ptr
- `+0x04`: byte (display/active flag, copied from resource)
- `+0x06`: WORD (field 6, copied)
- `+0x08`: WORD (field 8, copied)
- `+0x0C`: DWORD (copied)
- `+0x10–+0x2C`: DWORDs (copied from resource template)
- `+0x18`/`+0x1C`: "live" copy fields (set = template after load, updated per-frame)

### MtProperty-registered fields (from `uDevilCock::createProperty` @ `0x85F770`)

| Property name | Offset  | MtProp type | Notes |
|---------------|---------|-------------|-------|
| `mpResource`  | +0x18   | 2 (ptr)     | |
| `mpData`      | +0x1C   | 2 (ptr)     | |
| `mpSprAnm`    | +0x20   | 2 (ptr)     | |
| `FontData`    | `this`  | 0x19        | static font table ref |
| `mpFontData`  | `this`  | 2 (ptr), flags 0xA0 | with get/set callbacks `sub_4AD790`/`sub_4AD780` |
| `Default`     | `this`  | 0x1F, flags 2 | |

---

## Vtable (`uDevilCock::vftable` @ `0xBF0810`) — 19 slots

| Slot | Offset | Address    | Name / Role |
|------|--------|------------|-------------|
| 0    | +0x00  | `0x85F740` | `uDevilCock::dtor` — sets vtable, calls `delData`, frees via `UnitAllocator` |
| 1    | +0x04  | `0x8FC2F0` | `sub_8FC2F0` (shared — class query?) |
| 2    | +0x08  | `0x42BAF0` | `cUnit::isEnable` |
| 3    | +0x0C  | `0x85F770` | `uDevilCock::createProperty` — registers 6 MtProperty entries |
| 4    | +0x10  | `0x85F680` | `uSprLayout::getDTI` (inherited, not overridden) — returns `&uSprLayout::DTI` |
| 5    | +0x14  | `nullsub_2`| no-op |
| 6    | +0x18  | `0x85F930` | `uDevilCock::move` — tick: checks `mpResource` (this+6) and state byte (this+20) |
| 7    | +0x1C  | `nullsub_2`| no-op |
| 8    | +0x20  | `nullsub_2`| no-op |
| 9    | +0x24  | `0x85F9B0` | `uDevilCock::transMain` — renders sprites from `mpDispSprMap`, fonts from `mpFontData` |
| 10   | +0x28  | `0x46D740` | `sub_46D740` (shared) |
| 11   | +0x2C  | `0x8E57E0` | `sub_8E57E0` (shared) |
| 12   | +0x30  | `0x42BAB0` | `sub_42BAB0` |
| 13   | +0x34  | `0x85FA60` | `uDevilCock::loadResource` — allocates `mpDispSprMap` and `mpFontData` arrays |
| 14   | +0x38  | `0x521BF0` | `sub_521BF0` (shared) |
| 15   | +0x3C  | `nullsub_2`| no-op |
| 16   | +0x40  | `nullsub_2`| no-op |
| 17   | +0x44  | `0x85F960` | `uDevilCock::transBefore` — sorts/updates sprite priorities for HDTV |
| 18   | +0x48  | `0x85FE40` | `uDevilCock::delData` — frees `mpDispSprMap`, `mpFontData`, `mpSprAnm`, `mpResource` |

Note: SE vtable slot mapping confirmed identical (slots 3, 4, 12, 23=loadResource). SE has more slots due to engine additions.

---

## Key Function Detail

### `uDevilCock::uDevilCock` (constructor) @ `0x85F6C0`
Sets vtable, initialises cUnit status word at +0x04, zeros all pointer fields,
allocates 72 bytes for `mpDispSprMap` via `sub_45A2F0` and stores at +0x20,
then sets `mEnable = 1`.

### `uDevilCock::move` @ `0x85F930`
Checks `*(this+6)` (= `mpResource` guard — `this[6]` at +0x18) and `*(this+20)` (state byte at +0x14):
- If state == 0: calls vtbl+64 (`transMain` thunk)
- If state == 1: calls vtbl+68

### `uDevilCock::transMain` @ `0x85F9B0`
Validates `mpResource` and `isEnable` (vtbl+56), then iterates `mpDispSprMap`
entries (72 bytes each) calling `sub_4B1990` per sprite, and `mpFontData`
entries (48 bytes each) calling `sub_4B1A60` per font glyph. Calls vtbl+60 at end.

### `uDevilCock::loadResource` @ `0x85FA60` → `0x85FA70`
Allocates `mpDispSprMap` array (N×72 bytes, count from `mpResource+104`),
copies sprite params from resource. Allocates `mpFontData` array (N×48 bytes,
count from `mpResource+108`), sets each entry's vtable to `rSprLayout::vftable`
and copies font layout params.

### `uDevilCock::delData` @ `0x85FE40`
Frees in order: `mpDispSprMap[this+7]` (call vtbl[0] with arg 3 or UnitAllocator free),
`mpFontData[this+9]` (same pattern), `mpSprAnm[this+8]` (call vtbl[0] with arg 1),
`mpResource[this+6]` via `cResource::release`.

### `uDevilCock::transBefore` @ `0x85F960`
If `mpResource` and `mpDispSprMap` valid, checks `sub_4AD770()` (HDTV flag?):
for each sprite entry, if `isDisp` byte == 1, increments `pos` field by `vel` field.

---

## Key Addresses Summary

### `uDevilCock`

| Symbol | Address |
|--------|---------|
| `uDevilCock::vftable` | `0xBF0810` |
| `uDevilCock::DTI` global | `0xE58898` |
| `uDevilCock::DTI::init` | `0xB71770` |
| `uDevilCock::uDevilCock` (ctor) | `0x85F6C0` |
| `uDevilCock::dtor` | `0x85F740` |
| `uDevilCock::createProperty` | `0x85F770` |
| `uDevilCock::move` | `0x85F930` |
| `uDevilCock::transMain` | `0x85F9B0` |
| `uDevilCock::loadResource` | `0x85FA60` |
| `uDevilCock::loadResource_impl` | `0x85FA70` |
| `uDevilCock::transBefore` | `0x85F960` |
| `uDevilCock::delData` | `0x85FE40` |

### `uSprLayout`

| Symbol | Address |
|--------|---------|
| `uSprLayout::DTI` global | `0xE5B610` |
| `uSprLayout::DTI::init` | `0xB78AE0` |
| `uSprLayout::getDTI` | `0x85F680` |
| `sub_85F690` (near getDTI — possibly `uSprLayout::someMethod`) | `0x85F690` |
| `sub_8E57F0` (shared `createProperty` base — cUnit/cTrans props) | `0x8E57F0` |

### `rSprLayout`

| Symbol | Address |
|--------|---------|
| `rSprLayout::vftable` | `0xB9D378` |
| `rSprLayout::DTI` global | `0xE57D38` |

---

## Subclass Vtables (DX9)

All share `uDevilCock::draw` (`0x532F50`) at slot 12 (+0x30):

| Class       | Vtable addr | Slots | Notes |
|-------------|-------------|-------|-------|
| `uDevilCock`| `0xBF0810`  | 19    | base class |
| `uTitleA`   | `0xBF86B4`  | —     | (from uTitle_findings.md) |
| `uTitleB`   | `0xBF871C`  | —     | |
| `uTitleC`   | `0xBF8784`  | —     | |
| (unknown)   | `0xBC51EC`  | 47    | has uTitle::isEnd slots 32+ |
| (unknown)   | `0xBC5494`  | 47    | same |
| (unknown)   | `0xBC81F4`  | 47    | same |
| (unknown)   | `0xBF8ACC`  | 47    | same; extends into 2nd vtable block |
| `uTitle`    | `0xBF88F8`  | 2     | (from uTitle_findings.md) |
