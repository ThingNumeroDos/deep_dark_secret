# uEffectVFR Particle Generator — Reverse Engineering Findings

## Overview

`uEffectVFR` is the MT Framework particle effect unit in DMC4 DX9. It owns one or more `Generator` sub-objects, each of which manages a particle pool (stock free-list + active move-list). The analysed functions span particle emission (`initParticle`), per-frame generator tick (`moveGenerator`, `moveGenerators`, `Generator::update`), pool management (`openParticle`, `closeParticle`), and request start/stop (`setRequest`, `finish_requests`).

SE cross-reference note: the SE binary uses `cParticleGenerator` class hierarchy rather than `uEffectVFR::Generator`. All field offsets differ between DX9 and SE; the render-type enum (18 types) is the one verified-identical value. SE was used for naming hints only — no SE offsets were applied to DX9.

---

## Types Declared

### `uEffectVFR::Generator` (key fields) — 0x220 (544) bytes, no vtable

> Re-synced 2026-10-05 against the IDB type (`type_inspect`). An earlier version of this table (vtable @0,
> list heads @+0x18..+0x24, `pGeneratorParam` @+0x44, sound/effect callbacks) predated the typed struct and was
> wrong throughout — the Generator has **no vtable**; offset 0 is the move-list head.

| Offset | Type | Name | Notes |
|--------|------|------|-------|
| +0x00 | `Particle*` | mpMoveTopParticle | live (move) list head |
| +0x04 | `Particle*` | mpMoveBotParticle | live list tail |
| +0x08 | `Particle*` | mpStockTopParticle | free (stock) list head |
| +0x0C | `Particle*` | mpStockBotParticle | free list tail |
| +0x10 | `s16` | mParticleNum | pool capacity |
| +0x12 | `s16` | mParticleMoveNum | zeroed before the move-loop dispatch each frame |
| +0x14 | `s16` | mParticleSize | per-node byte size (per render type); `openParticle` memsets this many bytes |
| +0x16 | `s16` | mStatus | 0x1000 = vibration request live, 0x2000 = sound request live, 0x8000 = finished, 0x10 = matrix sub-block |
| +0x18 | `u32` | mFlags | state nibble = bits 24–27; move one-shot guard = bit 28 |
| +0x1C | `u8` | EntryType | prim entry type (`sPrim::getcPrim`) |
| +0x1D | `u8` | mTransType | render-dispatch key (see `mTransType` section) |
| +0x20 | `u32` | mRandCtr | |
| +0x24 / +0x28 / +0x2C | `u32` | mTimer / mSetParticleTotal / mSetFrameTotal | |
| +0x30 / +0x32 | `s16` | mSetTimer / mLoopCtr | |
| +0x34 / +0x38 | `float` | mSetFrameOfs / mIntervalFrameOfs | |
| +0x3C / +0x40 | `float` | mParticleScaleBase / mParticleScale | |
| +0x44 / +0x50 | `MtFloat3` / `MtVector3` | mLscaleBase / mLscale | |
| +0xB0 | `EFL_GENERATOR*` | mpGeneratorParam | on-disk generator descriptor (`RE/efl_generator_struct.md`) |
| +0xB4 / +0xB8 / +0xBC | | mpParticleParam / mpLifeParam / mpMoveParam | |
| +0xC0 / +0xC1 / +0xC2 / +0xC3 | `u8` | mGeneratorType / **mParticleType** / mLifeType / **mMoveType** | |
| +0xC4 | `s16` | mListNo | |
| +0xC6 / +0xC8 / +0xCA / +0xCC | `s16` | mPosWorkOffset / mCullingWorkOffset / mLifeWorkOffset / mMoveWorkOffset | per-node work-block offsets |
| +0xCE | `s16` | mWaitFrame | |
| +0xD0 | `ResourceInfo*` | mResourceInfo | `mpExtVibration`, `mpSoundRequest`, … (stride 0x34) |
| +0xD4 | `EFL_PARAM_COLLISION*` | mpCollParam | `get_coll_param(mpMoveParam)`, set in `Generator::AllocMemory`; NULL if no collision block |

### `uEffectVFR::ptclData` (per-particle output block)

> **Superseded / unverified.** This layout predates the current particle-struct analysis and was not
> re-verified this session. The per-particle node is a `uEffectVFR::Particle` virtual class (0x40-byte
> base header; double-buffer parity byte at node+0x0B), with a per-render-type body declared as
> `uEffectVFR::Ptcl<Type>` structs — see `RE/particle_type_structs.md` and the `mParticleType`/
> `mTransType` sections below. Treat the offsets in the table below as historical, not authoritative.

Passed by pointer to `initParticle` as the 4th argument; receives computed initial state.

| Offset | Type | Name | Notes |
|--------|------|------|-------|
| +0x00 | `char[0x10]` | pad_00 | |
| +0x10 | `void*` | pSubObj | sub-object pointer |
| +0x14 | `char[0x0C]` | pad_14 | |
| +0x20 | `float` | posX | current world pos X |
| +0x24 | `float` | posY | current world pos Y (x87-copied from prevPosY) |
| +0x28 | `float` | posZ | current world pos Z (x87-copied from prevPosZ) |
| +0x2C | `char[0x04]` | pad_2C | |
| +0x30 | `float` | prevPosX | previous world pos X |
| +0x34 | `float` | prevPosY | previous world pos Y |
| +0x38 | `float` | prevPosZ | previous world pos Z |
| +0x3C | `char[0x04]` | pad_3C | |
| +0x40 | `float` | posW | W component |
| +0x44 | `char[0x04]` | pad_44 | |
| +0x48 | `float` | pos2X | secondary pos X |
| +0x4C | `float` | pos2Y | secondary pos Y |
| +0x50 | `float` | pos2Z | secondary pos Z |
| +0x54 | `char[0x76]` | pad_54 | |
| +0xCA | `byte` | mParticleType | particle type flags |
| +0xCB | `byte` | mRenderType | render type (0-17) |

---

## Functions Analysed

### `uEffectVFR::moveGenerator` — 0x96FD00

Per-frame tick for one generator, called only from `uEffectVFR::move`. Returns 1 = still active, 0 = expired.
It spawns this frame's batch (`openParticle` → `initParticle`, `closeParticle` on init failure), runs the
move-loop dispatch below, caches the world position for next-frame interpolation, and on expiry calls
`Generator::finish_requests` (0x9DE140).

> The earlier phase list here (`mAge`/`mLifespan`/`mSpawnTimer` fields, a `moveGeneratorSetLoop` call) was
> written against the stale Generator layout and has been removed. Those fields don't exist at the offsets
> claimed; see the re-synced Generator table above.

**Move-loop dispatch** — `switch (pGen->mParticleType)` (+0xC1), verified 2026-10-05 from the decompile.
(An earlier banner here called this table superseded. It isn't: these are the real targets of `moveGenerator`.)

| `mParticleType` | Function | Address | Type |
|-------|----------|---------|------|
| 0x0 | `uEffectVFR::moveParticleLoop_type0` | 0x98D9B0 | Billboard |
| 0x1, 0xC | `uEffectVFR::moveParticleLoop_type1_C` | 0x98DA10 | Polyline / PolygonStrip |
| 0x2 | `uEffectVFR::moveParticleLoop_type2` | 0x98DA70 | Polygon |
| 0x3, 0xD | `uEffectVFR::moveParticleLoop_type3_D` | 0x98DAD0 | Texline / Texline(alt) |
| 0x4, 0xE | `uEffectVFR::moveParticleLoop_type4_E` | 0x98DB30 | Line / Line(alt) |
| 0x5 | `uEffectVFR::moveParticleLoop_type5` | 0x98DB90 | Model |
| 0x6 | `uEffectVFR::moveParticleLoop_type6` | 0x98DBF0 | PrimModel |
| 0x7 | `uEffectVFR::moveParticleLoop_type7` | 0x98DC50 | LensFlare |
| 0x8 | `uEffectVFR::moveParticleLoop_type8` | 0x98DCB0 | MassBillboard |
| 0x9 | `uEffectVFR::moveParticleLoop_type9` | 0x98DD10 | Filter |
| 0xA | `uEffectVFR::moveParticleLoop_typeA` | 0x98DD60 | Light |
| 0xB | `uEffectVFR::moveParticleLoop_typeB` | 0x98DDC0 | Hit |
| 0xF | `uEffectVFR::moveParticleLoop_typeF` | 0x98DEE0 | PolygonStrip(alt) |
| 0x10 | `uEffectVFR::moveParticleLoop_type10` | 0x98DFA0 | LiteBillboard (per-particle via owner vtbl +0xB0) |
| 0x11 | `uEffectVFR::moveParticleLoop_type11` | 0x98DF40 | SizeBillboard |

The IDB's inline comment on this switch (@0x96FDD4) previously labeled 7/0xB/0xF/0x11 as
PolygonStrip/LensFlare/Hit/"custom". It has been corrected to the writer-verified enum above.

**Second dispatcher — `uEffectVFR::moveGenerators` (0x99B5B0).** Called from `uEffectVFR::move`, `move2` and
`sub_964A00`. It is a separate per-generator loop that also runs the path-move step (`calcPathStripLength`
for mMoveType 3) and switches on `mParticleType` into a **different** set of loops: `moveParticleLoopPolyline`
(0x99B800, type 1), `moveParticleLoop_case2_17` (2/0x11), `moveParticleLoopTexline` (3), `moveParticleLoopLine` (4),
`moveParticleLoopModel` (5), `moveParticleLoopPrimModel` (6), `moveParticleLoopLight` (0xA),
`moveParticleLoopPolygonStrip` (0x99BD10, 0xF), and others. When each of the two dispatchers runs is not yet
established. Both are real; neither supersedes the other.

---

### ~~`uEffectVFR::moveGeneratorSetLoop` — 0x9DDB00~~ (removed)

0x9DDB00 is not a function entry. It is `uEffectVFR::Generator::update`+0x20. The section that used to sit here
described a function that doesn't exist at that address, and its contents were unverified. Removed 2026-10-05.

---

### `uEffectVFR::initParticle` — 0x970F10

1438-instruction initialization function for a newly spawned particle. Signature (after annotation):

```c
int __userpurge uEffectVFR::initParticle@<eax>(
    void *pEffect@<edi>,                 // scratch; role differs per caller — leave untyped
    uEffectVFR *pOwner,                  // the emitter object (NOT a Generator)
    uEffectVFR::Generator *pGen,         // the real generator
    uEffectVFR::ptclData *pPtclData,     // the particle node (really a uEffectVFR::Particle)
    float burstT,
    float *pDirOut)
```

(Signature re-synced with the IDB 2026-10-05. An earlier copy here had `pGen` as arg2 and an `int pParticle`
arg3, which is the owner/Generator aliasing trap: arg2 is the owner, arg3 is the Generator.)

Nine phases:

1. **Parameter block fetch**: reads `mpGeneratorParam` from `pGen+0xB0`; stores in local.
2. **`burstT` local copy**: `burstT_local = burstT` — x87 store to stack (unavoidable `__asm` at 0x970FA7).
3. **Emitter shape dispatch** (4 cases): selects spawn position based on shape type (point/sphere/box/cylinder); writes to `spawnPos` matrix and `inheritedPos` fields.
4. **Inline matrix inversion** (~200 instructions): if particle has a parent attachment, computes full 4x4 cofactor expansion to get inverse world matrix of the parent, then transforms spawn position into parent-local space. Hand-unrolled, not a library call.
5. **Velocity computation** (7 move-type sub-dispatch): reads base velocity from params, applies randomization, writes `velX/Y/Z` locals.
6. **`mParticleType` sub-dispatch** (18 types): sets initial visual state (`ptclScale`, `ptclScaleArg_a/b/c`) and calls a type-specific init sub. Switch key = `mParticleType` (Generator+0xC1), NOT a per-node "render type". Values below are writer-sourced (verified via `initGeneratorParam` (0x96AEC0, switch @0x96B691) — see the `mTransType` section near the end of this file); 16/17 are taken from the corrected table there:

   | `mParticleType` | Name |
   |------|-------------|
   | 0 | Billboard |
   | 1 | Polyline |
   | 2 | Polygon |
   | 3 | Texline |
   | 4 | Line |
   | 5 | Model |
   | 6 | PrimModel |
   | 7 | LensFlare |
   | 8 | MassBillboard |
   | 9 | Filter |
   | 10 | Light |
   | 11 | Hit |
   | 12 | PolygonStrip |
   | 13 | Texline (alt) |
   | 14 | Line (alt) |
   | 15 | PolygonStrip (alt) |
   | 16 | LiteBillboard |
   | 17 | SizeBillboard |

   > **Corrected.** A prior version of this table mislabeled the column "render type (0-17)" and listed
   > 3=Polygon/4=Polyline/5=Line/6=TexLine/9=Decal/11=Distortion. That ordering was wrong; the values
   > above come from the generator-param writer. The earlier `uEffectVFR::ptclData` and move-loop tables
   > in this file (the `mRenderType`/`mParticleType` byte at node+0xCA/0xCB and the `0x98Dxxx`
   > `moveParticleLoop_typeN` dispatch) predate this analysis and were **not** re-verified — see the
   > forward-pointers on those sections.

7. **Position write**: writes `spawnPosX/Y/Z` into `pPtclData->pos*` and `pPtclData->prevPos*`. Memory-to-memory float copy via x87 at 0x97267A/83 is unavoidable.
8. **Direction output**: if `pDirOut != nullptr`, writes normalized velocity direction to `*pDirOut`.
9. **Return**: 1 on success, 0 if no particle allocated.

---

### `uEffectVFR::Generator::openParticle` — 0x9DF2D0

Pops the head of the Stock list and appends it to the tail of the Move list (`pGen@eax`).

- `mpStockTopParticle` null → returns null (pool exhausted).
- Unlinks the head from Stock, appends at `mpMoveBotParticle`.
- `memset`s `mParticleSize` bytes, preserving `mpPrev` and `mSetNo`.
- Seeds the header: `mSerial` = `mSetFrameTotal` if `mFlags & 0x20000` else `mSetParticleTotal`; `mAge = 0`,
  `mStatus = 0`, `mAlive = 1`, `mParity = 0`.
- Returns the node. **No count field is touched** (there is no `mParticleCount`).

---

### `uEffectVFR::Generator::closeParticle` — 0xB1ABE0 (was `closeParticleAll`)

Closes **one** particle (`this@eax`, `pPtcl@ecx`) and returns `pPtcl->mpNext` so move loops can keep iterating.
Unlinks from the Move list (head and tail fixups), appends to the **tail** of the Stock list, and clears `mpNext`.
No count is decremented. The IDB name `closeParticleAll` was wrong and has been renamed back to SE's
`cParticleGenerator::closeParticle`. Callers: `moveGenerator`, every `moveParticleLoop_type*`, `uEffectVFR::doRestart`.

---

### `uEffectVFR::Generator::finish_requests` — 0x9DE140 (was `finishSoundAndCallback`)

The counterpart of `setRequest`: it stops the requests that `setRequest` started. **No callbacks are invoked.**
The earlier description (sound handle and callback pointers) was based on the stale Generator layout.

1. If `EFL_GENERATOR.mVibReqType != 0 && VibOptionFlag & 1 && mStatus & 0x1000` → `sVibration::stopVib(mVibrationId)`,
   `mVibrationId = -1`, clear 0x1000.
2. If `mResourceInfo->mpSoundRequest && SeOptionFlag & 1` (dword @+0x1C8 `& 0x10000`) `&& mStatus & 0x2000` →
   `uEffectVFR::stopSoundSe(...)`, clear 0x2000.

Callers: `moveGenerator`, `moveUnitGenerator`, `sub_9DDA70`.

---

## `__asm` Artifact Table

Three `__asm { fld/fstp }` blocks remain in the `initParticle` decompile output as genuine IDA/Hex-Rays limitations — not analysis errors. All three have explanatory comments in the IDB.

| Address | Pattern | Cause |
|---------|---------|-------|
| 0x970FA7 | `burstT_local = burstT` | float arg via `[ebp+param_5]`, x87 load while xmm dominates context |
| 0x97267A | `pPtclData->posY = pPtclData->prevPosY` | memory-to-memory float copy interleaved with xmm sequence |
| 0x972683 | `pPtclData->posZ = pPtclData->prevPosZ` | same pattern |

---

## SE Cross-Reference Summary

| DX9 name | SE equivalent | Match quality |
|----------|---------------|---------------|
| `uEffectVFR::Generator` | `cParticleGenerator` | Conceptual only; all offsets differ |
| `moveGenerator` | (per-particle-loop tick; no single SE analog) | **Not** `updateSingleGenerator`; see the reconciliation below |
| `Generator::updateSingleGenerator` (0x9DDBF0) / `uknGenBehaviorFunc1` | `cParticleGenerator::updateSingleGenerator` | State machine match |
| `openParticle` | `cParticleGenerator::openParticle` | Name confirmed via PDB |
| `closeParticle` | `cParticleGenerator::closeParticle` | Name confirmed via PDB |
| `finish_requests` (ex-`finishSoundAndCallback`) | stop side of `cParticleManager::setRequest` | Behaviour-matched (stops vib + SE) |
| `initParticle` | `cParticleGenerator::setup` (approx.) | Naming inferred |
| Render-type enum (18 types) | Identical enum values | **Exact match verified** |
| Move-loop dispatch | SE uses virtual dispatch; DX9 uses switch | Implementation differs |

SE subclasses of `cParticleGenerator` (reference only):
`cBillboardGenerator`, `cPolygonGenerator`, `cPolylineGenerator`, `cLineGenerator`,
`cTexlineGenerator`, `cModelGenerator`, `cLensflareGenerator`, `cDecalGenerator`,
`cLightGenerator`, `cDistortionGenerator`

---

## Generator state-machine tick + emit/spawn pipeline (2026-05-28)

This session cross-referenced `sub_9DDBF0` (now `uEffectVFR::Generator::updateSingleGenerator`) against SE `cParticleGenerator::updateSingleGenerator`
(SE `0xD93710`, demangled from `?updateSingleGenerator@cParticleGenerator@@IAEIXZ`) and traced the
DX9 emit path down to the particle pool allocator.

### `Generator::updateSingleGenerator` (0x9DDBF0, ex-`sub_9DDBF0`) — generator state-machine tick

This is the **structurally closest** DX9 match to SE `updateSingleGenerator` — a compact state machine,
**not** the large per-particle-loop tick documented above as `moveGenerator` (0x96FD00).

> ✅ **Reconciliation (resolved 2026-05-28):** the SE-cross-reference table above maps `moveGenerator`
> (0x96FD00) → `cParticleGenerator::updateSingleGenerator`. That mapping is **incorrect**. SE
> `updateSingleGenerator` is the small state machine (init→wait→fire→run→revival), which corresponds to
> the **`uEffectVFR::Generator::update` behaviour family** (0x9DDAE0 dispatcher), *not* the big 0x96FD00
> per-particle-loop function. See the "Generator::update dispatch" subsection below for the full mapping.

State = high nibble of `mFlags` (`HIBYTE(mFlags) & 0xF`); SE stores the same state as a **plain byte**
at `+0x43`. State values match exactly:

| State | Role | DX9 action | SE action |
|-------|------|-----------|-----------|
| 0 | init | zero mTimer/mSetFrameTotal/mSetParticleTotal; `mSetTimer = mWaitFrame`; → 1 | same zeroes; wait = joint_wait × `mWaitFrameCoef`; → 1 |
| 1 | wait/countdown | if `mSetTimer` `--`; else `setRequest()`, → 3, fall through | (gated by `mStatus&4`) if counter `--`; else `setRequest()`, → 3, `finish()` |
| 3 | fire | `mStatus \|= 0x8000`; `++mTimer`; → 5 | virtual `finish(this,0)`; `++mTimer` |
| 5 | running | `++mTimer` | `++mTimer` |
| 6 | revival/loop | **absent in DX9** | reseed wait via `RevivalFrame + mTrandom[mRandCtr&0xFFF] % (n+1)`; → 1 |

- DX9 `mStatus \|= 0x8000` (state 3) == SE's virtual `finish()` call.
- **Correction:** an earlier draft put DX9 `mSetTimer` at +0xF2 by matching SE's `*((WORD*)this+121)`.
  The actual DX9 field (from the typed `uEffectVFR::Generator`) is **`mSetTimer` @ +0x30** (WORD), with
  `mLoopCtr` @ +0x32. +0xF2 is the *SE* offset only — DX9 differs, as CLAUDE.md warns. The init seed is
  `mWaitFrame` @ +0xCE.

### Generator::update dispatch (0x9DDAE0) — the real `updateSingleGenerator` family

`uEffectVFR::Generator::update` runs once per generator per frame and selects a **spawn-count behaviour**
by the `mGeneratorType` byte (`pGen + 0xC0`):

| `mGeneratorType` | Behaviour fn | Notes |
|------------------|--------------|-------|
| 0 | (none) | returns 0, no extra spawn count |
| 1 | `Generator::updateSingleGenerator` (0x9DDBF0) | simpler variant — no firing-effect dispatch, no loop reseed |
| 2 | `uEffectVFR::uknGenBehaviorFunc1` (0x9DDCB0) | full variant — closest DX9 match to SE `updateSingleGenerator` |

So `updateSingleGenerator` and `uknGenBehaviorFunc1` are **sibling behaviour modes, not duplicate functions** — both
operate on the same `uEffectVFR::Generator` layout (state nibble in `mFlags` @ +0x18, `mSetTimer` @ +0x30,
`mLoopCtr` @ +0x32, counters `mTimer`/`mSetParticleTotal`/`mSetFrameTotal` @ +0x24/+0x28/+0x2C).

### `uEffectVFR::uknGenBehaviorFunc1` — 0x9DDCB0 (type-2 behaviour)

6-state machine (state = `HIBYTE(mFlags) & 0xF`), returns the per-frame spawn count. Signature applied:
`int __usercall …@<eax>(uEffectVFR::Generator *pGen@<edi>, uEffectVFR *owner@<esi>)`.

| State | Role |
|-------|------|
| 0 init | zero `mTimer`/`mSetParticleTotal`/`mSetFrameTotal`; `mSetTimer = mWaitFrame`; → 1 |
| 1 wait/fire | if `mSetTimer--` nonzero return 0; else `setRequest()`, pick firing effect via `sub_95FD00` (RNG = `sDevil4Effect::mpInstance[+0x20 + 4*(++owner->mRandCtr & 0xFFF)]`), store handle in `mLoopCtr`; → 2 |
| 2 setup | `uknGeneratorTimerFunc` reseeds `mSetTimer` from `LoopNum` param; → 3 |
| 3 active | if `mStatus & 0x20` run effect (`sub_963EC0`/`sub_964060`), else fire `sub_95FD00`; then spawn-count smoothing (`mFlags` bits 0x400000/0x800000 + `>>1` halving spreads count across frames); falls into loop logic |
| 4 loop | `--mSetTimer`; at 0 decrement `mLoopCtr`; if exhausted set `mStatus \|= 0x8000` (finished) → 5, else `uknGenLoopFunc` reseed (`SetFrame` param) → 2 |
| 5 run | `++mTimer` |

**Reseed helpers (= SE `case 6` revival math):**

- `uEffectVFR::uknGeneratorTimerFunc` (0x9DE250) — reseeds from `LoopNum` (per-burst loop window) + `SetInterval` fractional distribution.
- `uEffectVFR::uknGenLoopFunc` (0x9DE360) — reseeds from `SetFrame` (inter-burst interval) + `SetFrameDist`.

Both compute `base.s + rand % (base.r + 1)` using `sDevil4Effect::mpInstance[+0x20 + 4*(randCtr&0xFFF)]` as
the RNG — the DX9 equivalent of SE's `MtMath::mTrandom[mRandCtr & 0xFFF] % (RevivalFrame + 1)`. This is what
confirms `uknGenBehaviorFunc1` (not the count-less `updateSingleGenerator`) carries SE's `case 6` revival/loop semantics.

The `*(float *)&pGen` artifact in the two timer-func calls is benign: the helpers declare their first
param as `float@<edi>` and merely receive `pGen` through edi.

### `uEffectVFR::Generator::setRequest` — 0x9DDF40 (doc previously called it `emit_request`)

DX9 analog of SE `cParticleManager::setRequest` (SE `0xDBE750`). **The bodies match.** Both issue a
controller **vibration** request and then a sound request. An earlier version of this section said DX9
"spawns particles" here. That was wrong: the typed decompile passes `this = sVibration::mpInstance` and the
`.vib` resource `mResourceInfo->mpExtVibration` to every `req_*` call (re-verified 2026-10-05).

Skeleton (state 1→3): switch on `EFL_GENERATOR.mVibReqType` (**+0x13C**, u8; disasm `cmp byte ptr [edi+13Ch], 0`)
→ store the result in `pGen->mVibrationId` → `if (mVibrationId != -1) mStatus |= 0x1000` → if
`mResourceInfo->mpSoundRequest`: `mStatus |= 0x2000`, `sDevil4Sound::requestSe(sSoundN::mpInstance, …)` (sound arg
from param +0xE4). The stop side is `Generator::finish_requests` (0x9DE140).

| `mVibReqType` (+0x13C) | Call |
|---------------------------|--------------------|
| 0 | (no vibration; sound branch only) |
| 1 | `sVibration::req_simple` |
| 2 | `sVibration::req_at_pos` (generator world pos `mWmat.vectors[3]`) |
| 3 | `sVibration::req_with_parent` (if owner `mParent`, joint = `ParentNo` @+0x3C), else `req_at_pos` |

Common args: `VibReqNo` (u16 @+0x1C0), `VibPriority` (@+0x1C4), `mpExtVibration`, `&MESS_QUEUE_DATA`,
`mVibReqArg0 | mVibReqArg1 << 16` (bytes @+0x13E/+0x13F).

### Vibration request pool (`sVibration`, formerly mis-filed `particle_pool` / `particle_rec`)

```
setRequest (0x9DDF40)
  ├─ type 1 → sVibration::req_simple      (0x908920) ─┐
  ├─ type 2 → sVibration::req_at_pos      (0x908990) ─┤ CRITICAL_SECTION-guarded wrappers
  └─ type 3 → sVibration::req_with_parent (0x908A10) ─┘
                         │
                         ▼
          sVibration::alloc_slot (0x909A10)
              scans 8-slot × 176-byte (0xB0) array, bails if used ≥ 8,
              bumps 31-bit rolling serial, returns slot addr (176*i + base + 112)
                         │
                         ├─ sVibration::rec_init (0x909AE0)
                         │     refcount cResource (+0x10, addRef/release), read 16B descriptor,
                         │     set type flags 0x11/0x22/0x100/0x200 (+0x2C),
                         │     fill ten 1.0f ramp floats (+0x30..+0x54), zero pos vecs (+0x70/+0x80/+0x90)
                         │
                  per type, post-alloc configurator:
                  ├─ req_simple      → reads slot serial (+0x1C)
                  ├─ req_at_pos      → sVibration::rec_set_position   (0x909E30)
                  └─ req_with_parent → sVibration::rec_attach_parent  (0x909E80)
                         │
                         ▼
          sVibration::rec_resolve_transform (0x90A1B0)
              resolve parent-joint world transform (vtable +0x3C → translation),
              then per-channel distance attenuation (dmc4_sqrt of squared deltas,
              near/far ramp) into channel arrays +0x30 (2 ch) / +0x38 (8 ch)
              = rumble strength falloff by distance. Also called from sub_909CA0.
```

**Pool object** = the **`sVibration`** singleton (`sVibration::mpInstance` @0xE559CC, which the IDB had mis-named
`sVibrator::mpInstance`). DTI-confirmed: `sVibration::ctor` (0x907180) installs `sVibration::vftable` (0xC0371C), whose
`getDTI` returns `sVibration::DTI` (class `sVibration`, parent `cSystem`, size 0x820), and lays out the 8 slots at
0x70 + 0xB0·i. Layout:
`CRITICAL_SECTION` @ +0x04, job-safe flag @ +0x28 (also gated by `cSystem::mJobSafe`), rolling 31-bit serial
@ +0x68, 8 slots of 176-byte request records from ~+0x70.

**Callers:** the `req_*` API has two callers, `setRequest` (effects) and `sub_9098D0` (called from
`sub_908130`, not yet identified). Method names stay lowercase placeholders. The class is anchored by the
`sVibration::mpInstance` argument, and the class is confirmed by its DTI (above).

### Names (current IDB)

| Addr | Name | Notes |
|------|------|-------|
| 0x9DDF40 | `uEffectVFR::Generator::setRequest` | SE name |
| 0x9DE140 | `uEffectVFR::Generator::finish_requests` | stop side; was `finishSoundAndCallback` |
| 0x9DDBF0 | `uEffectVFR::Generator::updateSingleGenerator` | type-1 behaviour (was `sub_9DDBF0`) |
| 0x909A10 | `sVibration::alloc_slot` | was `particle_pool::alloc_slot` |
| 0x909AE0 | `sVibration::rec_init` | was `particle_rec::init` |
| 0x90A1B0 | `sVibration::rec_resolve_transform` | was `particle_rec::resolve_transform` |
| 0x909E30 | `sVibration::rec_set_position` | was `particle_rec::set_position` |
| 0x909E80 | `sVibration::rec_attach_parent` | was `particle_rec::attach_parent` |
| 0x908920 | `sVibration::req_simple` | was `particle_pool::spawn_simple` |
| 0x908990 | `sVibration::req_at_pos` | was `particle_pool::spawn_at_pos` |
| 0x908A10 | `sVibration::req_with_parent` | was `particle_pool::spawn_with_parent` |

---

## Move-param dispatch — `uEffectVFR::movePath` (0x9DE1D0, ex-`movePath`) — 2026-05-28

> Names/addresses re-synced to the IDB 2026-10-05. The old address 0x9DE1B0 was a typo: it falls inside
> `finish_requests`. The function starts at 0x9DE1D0, and its one caller (@0x9DDBD6) is unchanged.

User hypothesis: maps to the `mpPath` block in SE's `cParticleGenerator::move`. **Confirmed (partial/divergent).**

### What it is

A discrete **move-param dispatch step** invoked from within the per-frame generator tick.
DX9 xref is conclusive: `movePath` has exactly **one caller** — `uEffectVFR::Generator::update` (0x9DDAE0, @0x9ddbd6). So it is a "block within move" exactly as the user framed it, from DX9 evidence (not just inferred from SE).

Dispatches on **`mMoveType`** (`Generator+0xC3`; confirmed via disasm `movzx eax, byte [edi+0C3h]` @0x9de1db) with a **one-shot first-frame guard**. (The `+0xE4` field `mMoveSpreadCount` is **not** the selector — it appears only as an *argument* in the mMoveType==4 branch.)

- Guard = `mFlags & 0xF0000000` (bit `0x10000000`, bits 28–31). On first call the test is zero → init branch runs and the bit is set; thereafter the else (per-frame) branch runs.
- ⚠️ **This guard bit is NOT the state nibble.** The tick state machine documented earlier keys on `HIBYTE(mFlags) & 0xF` = bits **24–27**. The move guard is bits **28–31** of the same dword — a separate one-shot flag. Do not conflate them.

| mMoveType | first frame (guard clear) | subsequent (guard set) |
|-----------|---------------------------|------------------------|
| 3 | `calcPathStripLength(param, pGen, 1)` | `calcPathStripLength(param, pGen, 0)` |
| 4 | `initPathChain` (init+sample+apply) | `movePathChain` (re-sample+apply), only if `!param_2` |
| other | no-op | no-op |

### Callees (renamed, lowercase placeholders)

| Addr | New name | Role |
|------|----------|------|
| 0x9DE470 | `uEffectVFR::Generator::calcPathStripLength` | mMoveType==3: walk path point list, write running per-segment distance array into `rec+228`. Path sub-type at `mpMoveParam+120`: case1=open polyline, case2=multi-strip, case3=loop. |
| 0x984250 | `uEffectVFR::Generator::initPathChain` | mMoveType==4 first frame: set rec init bytes (+0x1C=1, +0x1D=type), sample up to 4 keyframe channels via `sub_963EC0` (mask `rec+0x1E` bits 0x4/0x8/0x10/0x20), tail-call apply `moveChain`-sibling `sub_984350` with AxisZ basis. |
| 0x994B40 | `uEffectVFR::Generator::movePathChain` | mMoveType==4 per-frame: re-sample the same 4 channels, tail-call apply `moveChain`. |
| 0x994C20 | `uEffectVFR::Generator::moveChain` | apply-tail: keyframe-driven per-particle **orientation/direction** build + emit. Calls `uEffectVFR::calcKeyframeF32`/`calcKeyframeVector`/`calcDir`, builds an **axis-angle quaternion** rotation, writes particle dir vectors (rec +0x50/+0x5C/+0x80), then loops emitting/transforming each particle in the strip. |

### SE correspondence (hedged)

The SE generator move dispatcher is `cParticleGenerator::moveParticleMove` (SE **0xDBDBA0**) — a 12-way switch on a 4-bit move-type field `(... >> 20) & 0xF`, dispatching to `moveParticleMove{None,Add,Mul,PathStrip,PathChain,PathKeyframe,PathLine,Custom,Spin,AddFast,MulFast,SpinFast}`. The four `Path*` variants are the "mpPath block."

- **mMoveType==3 (DX9)** matches the **SE PathStrip family** — `calcPathStripLength` builds the per-segment distance array, the same job as SE `getPathStripLengthArraySize` / `updateParticleMovePathStripDistance`.
- **mMoveType==4 (DX9) = SE PathChain** (CONFIRMED 2026-05-29 by structurally matching the per-particle integrators against SE — see the move-type init section below). `sub_994C20` (the per-frame generator facet of mMoveType==4) does keyframe-driven **orientation**; chain motion builds per-node orientation quaternions too, so `sub_994C20` is the orientation facet of *chain* — **not** evidence of a separate "keyframe type." (Earlier this section guessed mMoveType==4 ≈ PathKeyframe "not chain"; that was wrong — it leaned on `calcKeyframe*` usage, which all move-types share and which does not discriminate.)

Net: DX9 `movePath` is the **path/move-param slice** of the SE move dispatch, reached per-frame from `Generator::update` — confirming the user's "mpPath block in move" reading. The full DX9→SE move-type mapping (3=Strip, 4=Chain, 5=Keyframe, 6=Line) is resolved in the section below.

---

## Per-particle motion-model init — `initParticle`'s `mMoveType` switch (cases 0–6) — 2026-05-29

The final `switch (pGen->mMoveType)` in `initParticle` (0xC3, **same enum** as `movePath`) seeds the particle's **move-work block** (`pPtclData + mMoveWorkOffset`) with randomized motion parameters. One initializer per move-type. All share a skeleton: sample randomized values from `mpMoveParam` via the effect RNG (`sDevil4Effect::mpInstance[idx*4 + 16416]` floats / `+32` ints), drive keyframe curves (`calcKeyframeF32`/`calcKeyframeVector`/`calcDir`), and set a per-particle flag accumulator at move-work `+0x68` (word). They differ in motion model.

### Initializers (renamed; lowercase placeholders, subtype-neutral)

| case | addr | name | model | SE correspondence |
|------|------|------|-------|-------------------|
| 0 | 0x972D60 | `initParticleMoveNone` | direct/none: copy basis, optional single fixed normalized velocity | **CONFIRMED** `initParticleMoveNone` |
| 1 | 0x972F00 | `initParticleMoveAdd` (ex-`initMove1_vel`) | velocity: writes speedVec +0x40 **and accelVec +0x50**, rate +0x14; returns 0x180 | **CONFIRMED** Add (2026-10-05) |
| 2 | 0x973460 | `initParticleMoveMul` (ex-`initMove2_vel`) | velocity: speedVec +0x40 + mul rate +0x14 only | **CONFIRMED** Mul (2026-10-05) |
| 3 | 0x9739D0 | `initParticleMovePathStrip` | drag+basis+dir-curve, `calcParticleMovePathStripPos`, renorm vel on flag 0x10000 | **CONFIRMED** `initParticleMovePathStrip` |
| 4 | 0x974040 | `initParticleMovePathChain` | same setup, integrator `calcParticleMovePathChainPos` | **CONFIRMED** `initParticleMovePathChain` |
| 5 | 0x974560 | `initParticleMovePathKeyframe` | two curve control points + spin, `calcParticleMovePathKeyframePos` | **CONFIRMED** `initParticleMovePathKeyframe` |
| 6 | 0x974A50 | `initParticleMovePathLine` | twin of case 3 but integrator `calcParticleMovePathLinePos` (clamp, not wrap) | **CONFIRMED** `initParticleMovePathLine` |

### Shared position/velocity integrators (renamed)

| addr | name | role | SE |
|------|------|------|----|
| 0x9750B0 | `movevel_transform` | velocity-family: mWscale+basis transform, optional dir-blend (cases 1,2) | velocity helper *(hedged)* |
| 0x975440 | `calcParticleMovePathStripPos` | walks point-list; sub-mode @mpMoveParam+120 → sub_ADA2B0=linear / sub_ADA680=hermite / sub_ADAA50=spline (≡ SE `switch(Node)` 1/2/3 calcPathLinear/Hermite/SplineVertex); wraps or clamps; returns 0x400 on end | **CONFIRMED** SE same name |
| 0x975BA0 | `calcParticleMovePathChainPos` | walks point-list, per-node orientation quaternion + full 4×4 inverse frame (the Chain discriminator vs Strip) | **CONFIRMED** SE same name |
| 0x977070 | `calcParticleMovePathKeyframePos` | scale+rot applied to a precomputed offset; no walk, no clamp, returns 0 (≡ SE Keyframe) | **CONFIRMED** SE same name |
| 0x977240 | `calcParticleMovePathLinePos` | **clamps** distance (non-wrapping), moves along an axis vector, no segment walk (the Line discriminator) | **CONFIRMED** SE same name |

### Reconciliation with the `movePath` section above (important)

`movePath` and this `initParticle` switch read the **same byte** `mMoveType@0xC3` — **not** different enums. They are **different stages of the same move-type**:
- `movePath` = per-frame, generator-level move-spread setup (only acts on mMoveType 3 & 4 — the path types — consistent with path-spread mattering only for path motion).
- `initParticle`'s switch = per-particle spawn init.

For **mMoveType==4** specifically: the generator facet (`movePath` → `moveChain`/sub_994C20) does **keyframe orientation**; the per-particle facet (`initParticleMovePathChain` 0x974040 → `calcParticleMovePathChainPos` 0x975BA0) does **chain position** (per-node orientation frame). Both are true and complementary: `moveChain` (0x994C20) is the generator-level orientation facet of the same Chain move type.

### Path-subtype resolution (2026-05-29, SE cross-referenced)

The path-subtype split was confirmed by decompiling SE's four `cParticleGenerator::calcParticleMovePath{Strip,Chain,Keyframe,Line}Pos` and matching each DX9 integrator by **structural fingerprint** (not case position):

- **Strip** — `switch` over an interpolation mode (linear/hermite/spline) while walking the point-list. DX9 `calcParticleMovePathStripPos` (0x975440) has the identical 3-way `switch(mpMoveParam+120)`.
- **Chain** — walks the point-list **and** builds a per-node orientation quaternion + full 4×4 inverse frame. DX9 `calcParticleMovePathChainPos` (0x975BA0) is the only integrator doing both.
- **Keyframe** — no walk, no clamp, `return 0`; applies scale+rot to a precomputed offset. DX9 `calcParticleMovePathKeyframePos` (0x977070) matches exactly.
- **Line** — clamps distance (non-wrapping) and moves along a single axis vector, no segments. DX9 `calcParticleMovePathLinePos` (0x977240) matches.

So **mMoveType 3/4/5/6 = Strip/Chain/Keyframe/Line** — which also happens to be SE's `moveParticleMove` dispatcher order (cross-validation). The match is structural; the sequential agreement is confirmation, not the basis. Cases 3/4/6 all walk point-lists, so the discriminators are: Strip=interp-mode switch, Chain=per-node inverse frame, Line=clamp+axis (no walk).

**Resolved (2026-10-05): 1 = Add, 2 = Mul.** The full per-particle dispatcher `uEffectVFR::move_particle_move` (0x995CF0,
called from every per-type move sub) splits the two cases. An instruction diff of the two near-identical integrators
(0x5F9 / 0x5FA bytes) differs in exactly one step:
- `moveParticleMoveAdd` (0x996160): `speedVec(+0x40..48) += accelVec(+0x50..58)`
- `moveParticleMoveMul` (0x996760): `speedVec(+0x40..48) *= rate(+0x14)`

Both then do `fallSpeed(+0x1C) += gravity(+0x18)`. The lighter dispatcher `moveParticleMoveParam` sends both cases to
the shared `moveParticleMoveVel`, which is why the earlier analysis couldn't tell them apart. The earlier statement that
neither init writes a second vector was wrong: the Add init writes accelVec at +0x50..0x58.

---

## `uEffectVFR::renderGenerators` (0x964AD0) — the per-frame DRAW dispatcher, and the `mTransType` enum

`sub_964AD0` (renamed **`uEffectVFR::renderGenerators`**) is the render-pass counterpart to the
move dispatchers. It is reached via the 5-byte thunk `sub_53C340` (`jmp 0x964AD0`) and its address
is stored at `0xC0613C` (a `uEffectVFR` vtable slot). It walks every Generator in
`EffectArr[mGeneratorNum]` and, for each that passes the `sub_53D460(scene,&gen)` visibility test,
dispatches on **`Generator.mTransType` (Generator+0x1D)** to a per-render-type routine that submits
primitives.

- **Gate:** returns early if `sub_521710(this)` (the `mMode&2` predicate) or `(mMode & 0x1000)`.
- **Scratch:** `getMem(size = this->member_0x11c)` once per call when nonzero, threaded into the targets.
- **Verified draw semantics:** case 0 → `sub_99E0D0` fetches a `cPrim` (`sPrim::getcPrim` using
  `Generator.EntryType` @+0x1C), sets prim/tex env (`setPrimEnv`, `getTexHandleWrapper`), walks the
  `mpMoveTopParticle` list and emits prims interpolated across the `+0x0B` double-buffer parity.
- **Two flag-selected variants of one function** (NOT two vtable methods), gated by `mAxisType & 0x400`:
  variant A (`case0=sub_99E0D0 … case0x1D=vtbl[+49]`) vs variant B (`case0=sub_99DE40 … case0x1D=vtbl[+48]`).
  **Resolved (2026-10-05): this is NOT world vs screen orientation. It is sub-frame time interpolation.** In all 24
  PrimModel leaves, every `_interp` (ex-`_axis`) variant (and none of the plain ones) reads `uEffectVFR+0xFC` `mTimeInterpolationRate`
  and lerps both of the node's double-buffer slots (position, rotation, scale, shape, colour, anim frame) instead of reading
  one slot. The geometry and orientation code is identical. Orientation is a separate per-generator setting
  (`param+0x170` bits 24–27 → `uEffectVFR::build_view_basis`). **All 37 `_axis` render leaves were renamed `_interp`**
  (2026-10-05). The flag lives in **`uEffectVFR.mStateFlags`** (byte +0x10D). The compiler accesses it through dword
  ops on +0x10C, which is why it reads as `mAxisType & 0x400`. Bit 0x04 (dword-view 0x400) is set in `move` when there is
  a fractional time remainder this frame. Bit 0x01 (dword-view 0x100) = generators built (`createGenerator`). The
  byte at +0x10C (`mAxisType`) is a separate state byte, written with the value 6 by `moveUnitGenerator` and `setParamConst`.
  The neighbouring fields were re-typed from code widths: `stepCount` u16 @0x10E, u8 @0x110/0x111, `loopLimit` u16
  @0x112 (was an int overlapping 0x114), u16 @0x114.

### `mTransType` is NOT a new enum — it is `mParticleType` + a culling render-variant remap (formerly called "Lite")

Ground truth: **`uEffectVFR::initGeneratorParam` (0x96AEC0; the switch is at 0x96B691)** is the writer. It `switch`es on
`mParticleType` (Generator+0xC1) and stores `mTransType` (Generator+0x1D). The remap depends on the
descriptor's **`CullingFlag` bit 0** `(EFL_PARTICLE_COMMON+2 & 1)`. (This was earlier mis-attributed to SE
`mLiteParticleFlag`; corrected 2026-10-05, see the note below.):

| mParticleType | Name | mTransType (normal) | mTransType (CullingFlag set) |
|--:|---|--:|--:|
| 0 | Billboard | 0 | 0x11 |
| 1 | Polyline | 1 | 0x12 |
| 2 | Polygon | 2 | 0x13 |
| 3 | Texline | 3 | 0x14 |
| 4 | Line | 4 | 0x15 |
| 5 | Model | 5 | 0x16 |
| 6 | PrimModel | 6 | 0x17 |
| 7 | LensFlare | 7 | — |
| 8 | MassBillboard | 8 | — |
| 9 | Filter | 9 | — (non-prim) |
| 10 | Light | 10 | — (non-prim) |
| 11 | Hit | 11 | — (non-prim) |
| 12 | PolygonStrip | 12 | 0x18 |
| 13 | Texline (alt) | 13 | 0x19 |
| 14 | Line (alt) | 14 | 0x1A |
| 15 | PolygonStrip (alt) | 15 | 0x1B |
| 16 | **LiteBillboard** | **0x1D** (always) | 0x1D |
| 17 | **SizeBillboard** | **0x10** | 0x1C |
| default | — | 0x1E | — |

> The base-type/alt-type pairing (1↔13 Polyline/Texline, 3↔13, 4↔14, 15 PolygonStrip) follows the
> confirmed `mParticleType` enum; 13/14/15 are the "alt" geometry variants noted there.

> **Correction (2026-10-05, SE-confirmed): the "Lite" render variants are SE's *culling* variants.**
> - In SE, every `cParticleGenerator*::initParam` sets `mDrawType = initCullingParam() ? <culling draw type> : <normal>`.
>   Example: PrimModel uses 6 / 0x1F, and `cParticleGeneratorPrimModel::draw` routes `mDrawType != 6` to the
>   `drawParticleCulling…Loop` functions.
> - `cParticleGenerator::initCullingParam` returns true exactly when `EFL_PARTICLE_COMMON` word@+2 (`CullingFlag`) has
>   bit 0 set. With bit 0x40 it also initialises a `cEffectCulling` from an `EFL_PARAM_CULLING` block at a u16
>   self-relative offset. That is DX9's `DRAW_COMMON.CullingParamOffset` (0x46) block, which our "Lite" leaves fade with.
> - SE's genuine "Lite" is a different concept: the `cParticleGeneratorLite{Billboard,Polyline,Polygon}` classes and
>   `cParticleGenerator::mLiteParticleFlag`. In DX9 that is particle type 16 (LiteBillboard).
> - **Renamed in the IDB:** all 34 `render<Type>Lite[_interp]` → `render<Type>Culling[_interp]`, and
>   `calc_lite_fade` → `calc_culling_fade`. `initParticleLiteBillboard`/`moveParticleLiteBillboard` (the real type 16)
>   are unchanged. Wherever "Lite" below refers to the 0x11–0x1C transTypes, read it as "Culling".

Consequences, all consistent with the dispatcher's case table:
- **Cases 0x11–0x1C are the Culling-variant draws** (CullingFlag bit0 set): 0x11–0x17 = culling variant of types
  0–6, 0x18–0x1B = culling variant of 12–15, **0x1C = culling variant of SizeBillboard(17)**.
- **Case 0x10 = SizeBillboard (normal)** — particle type 17. (PType 17 is written by `case 0x11:` in
  `initGeneratorParam`, storing 0x10 normal / 0x1C lite.)
- **Case 0x1D = LiteBillboard** — particle type 16, written by `case 0x10:`, always 0x1D. In
  renderGenerators case 0x1D defers to a **virtual** (`vtbl[+48]`/`vtbl[+49]`), so LiteBillboard is
  drawn through that virtual, not a leaf. (Correction: an earlier draft of this table swapped the
  16↔17 rows and mis-named case 0x1D as SizeBillboard via a misattributed `sub_9A8590` — that leaf is
  actually the **case 0x11** variant-A target = Billboard-lite. The writer at 0x96B691 is the source of
  truth.)
- **Gaps at cases 9/0xA/0xB** (Filter/Light/Hit) are intentional: these non-prim types render through
  `uEffectVFR::updateParticles2` (updateParticleFilter/updateParticleLight/…), not here.

`initGeneratorParam` also derives a blend slot `(v4+28)` from `EFL_PARTICLE_COMMON+1` (EntryType) and
sets numerous generator flags; for the culling/keyframe types it additionally calls
`getKeyFrameSmthOffset` + `calcDirWrapper`.

**Cross-reference (SE, PDB-authoritative):** SE implements every type as a distinct C++ subclass
(`cParticleGeneratorBillboard`, `…Polyline`, `…SizeBillboard`, `…LiteBillboard`, etc.) selected by
vtable; DX9 flattened those into the `mParticleType`/`mTransType` byte pair. The on-disk descriptor
`rEffectList::EFL_PARTICLE_COMMON` carries `EntryType` (+0x1) and the type-specific layout; it has no
explicit "particle type" field — the type is chosen by the loader, then materialized into the bytes
above. SE `cParticleGenerator` has no single type byte either, confirming the structural encoding.

### Render-leaf targets named (both axis variants)

All leaf renderers in both `renderGenerators` switch variants are now named (verified each against the
renderer fingerprint — `sPrim::getcPrim` + `setPrimEnv` + `getTexHandleWrapper` + `mpMoveTopParticle`
list walk — and against the type's already-named move-loop/update fn). Naming scheme:
`uEffectVFR::render<Type>` for plain (`mStateFlags & 4` clear) and `render<Type>_interp` (ex-`_axis`) for the sub-frame interpolated variant
(flag set); culling cases use `<Type>Culling` (named `<Type>Lite` before the 2026-10-05 rename). Types: Billboard, Polyline, Polygon, Texline, Line, Model,
LensFlare, MassBillboard, PolygonStrip, Texline13, Line14, PolygonStrip15, SizeBillboard, and their
Culling variants. 46 functions renamed, 0 geometry contradictions.

- **MassBillboard (case 0x8)** is a renderer but uses a **batched** submission path (builds a 16-DWORD/
  particle vertex buffer, one submit via `calcPrimMaterial` + `sub_AA87C0`) instead of per-particle
  `getcPrim` — consistent with "mass" billboard. Named, deviation noted in its comment.
- **PrimModel (case 0x6) and PrimModelCulling (case 0x17)** are second-level dispatchers, now named
  `uEffectVFR::renderPrimModel` / `_interp` / `renderPrimModelCulling` / `_interp` (0x9A5630 / 0x9A56C0 / 0x9AFCB0 / 0x9AFD40).
  Each switches on `mpParticleParam[+0x170] & 0xF` into 6 sub-renderers. **All 24 are mapped (2026-10-05)**; see
  `RE/particle_type_structs.md` → "PrimModel render sub-types".
- **case 0x1D = LiteBillboard** has no leaf — it defers to a virtual (`vtbl[+48]`/`vtbl[+49]`).
