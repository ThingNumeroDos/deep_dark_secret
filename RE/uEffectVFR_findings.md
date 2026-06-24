# uEffectVFR Particle Generator — Reverse Engineering Findings

## Overview

`uEffectVFR` is the MT Framework particle effect unit in DMC4 DX9. It owns one or more `Generator` sub-objects, each of which manages a particle pool (stock free-list + active move-list). The analysed functions span particle emission (`initParticle`), per-frame generator tick (`moveGenerator`, `moveGeneratorSetLoop`), pool management (`openParticle`, `closeParticle`), and cleanup (`finishSoundAndCallback`).

SE cross-reference note: the SE binary uses `cParticleGenerator` class hierarchy rather than `uEffectVFR::Generator`. All field offsets differ between DX9 and SE; the render-type enum (18 types) is the one verified-identical value. SE was used for naming hints only — no SE offsets were applied to DX9.

---

## Types Declared

### `uEffectVFR::Generator` (key fields)

| Offset | Type | Name | Notes |
|--------|------|------|-------|
| +0x00 | `void*` | vtable | |
| +0x04 | `uEffectVFR::Generator*` | pNext | doubly-linked list next |
| +0x08 | `uEffectVFR::Generator*` | pPrev | doubly-linked list prev |
| +0x14 | `int` | mParticleCount | active particle count |
| +0x18 | `void*` | pStockHead | free-pool list head |
| +0x1C | `void*` | pStockTail | free-pool list tail |
| +0x20 | `void*` | pActiveHead | active move-list head |
| +0x24 | `void*` | pActiveTail | active move-list tail |
| +0x28 | `int` | mMaxParticles | capacity |
| +0x2C | `float` | mAge | generator age in frames |
| +0x30 | `float` | mLifespan | total lifespan |
| +0x34 | `float` | mSpawnTimer | fractional emit accumulator |
| +0x38 | `int` | mSpawnParity | alternating parity flag (0/1) for burst logic |
| +0x3C | `int` | mFlags | state flags |
| +0x44 | `void*` | pGeneratorParam | pointer to parameter block |
| +0x48 | `MtMath::MtMatrix` | mLocalMatrix | local-space bind matrix (16 floats) |
| +0x88 | `void*` | pSoundCallback | sound event callback pointer |
| +0x8C | `int` | mSoundHandle | handle for active sound |
| +0xEC | `void*` | pEffectCallback | effect-lifetime callback |

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

Per-frame tick dispatched for each active generator. Six execution phases:

1. **Age check**: if `mAge >= mLifespan`, call `finishSoundAndCallback` and mark generator expired.
2. **Active particle loop**: walk `pActiveHead` linked list; call the per-particle move function via the `mRenderType` dispatch table (15 entries, indexed by `mParticleType & 0xF`).
3. **Expiry check**: if any particle age >= lifespan, unlink via `closeParticle` and push back to stock.
4. **Spawn gate**: if `mAge < mSpawnStart` or flags indicate suppression, skip spawn.
5. **Burst/continuous spawn**: compute delta emit count from `mSpawnTimer`; for each new particle, pop from stock via `openParticle`, call `initParticle`, call `moveGeneratorSetLoop`.
6. **Advance age**: `mAge += deltaTime`.

Move-loop dispatch table (indexed by `mParticleType & 0xF`):

> **Superseded / unverified.** The `0x98Dxxx` addresses and `moveParticleLoop_typeN` names below were
> not re-verified this session and are *different functions* from the per-frame move-loop family that
> was verified and renamed (`0x99B800 moveParticleLoopPolyline`, `0x99BD10 moveParticleLoopPolygonStrip`,
> etc. — keyed on `mParticleType` at Generator+0xC1). For the verified move/render dispatch, see the
> `moveParticleMoveParam` notes and the `renderGenerators`/`mTransType` sections in this file. The table
> below is retained as historical only.

| Index | Function | Address |
|-------|----------|---------|
| 0x0 | `uEffectVFR::moveParticleLoop_type0` | 0x98D9B0 |
| 0x1 | `uEffectVFR::moveParticleLoop_type1_C` | 0x98DA10 |
| 0x2 | `uEffectVFR::moveParticleLoop_type2` | 0x98DA70 |
| 0x3 | `uEffectVFR::moveParticleLoop_type3_D` | 0x98DAD0 |
| 0x4 | `uEffectVFR::moveParticleLoop_type4_E` | 0x98DB30 |
| 0x5 | `uEffectVFR::moveParticleLoop_type5` | 0x98DB90 |
| 0x6 | `uEffectVFR::moveParticleLoop_type6` | 0x98DBF0 |
| 0x7 | `uEffectVFR::moveParticleLoop_type7` | 0x98DC50 |
| 0x8 | `uEffectVFR::moveParticleLoop_type8` | 0x98DCB0 |
| 0x9 | `uEffectVFR::moveParticleLoop_type9` | 0x98DD10 |
| 0xA | `uEffectVFR::moveParticleLoop_typeA` | 0x98DD60 |
| 0xB | `uEffectVFR::moveParticleLoop_typeB` | 0x98DDC0 |
| 0xF | `uEffectVFR::moveParticleLoop_typeF` | 0x98DEE0 |
| 0x10 | `uEffectVFR::moveParticleLoop_type10` | 0x98DFA0 |
| 0x11 | `uEffectVFR::moveParticleLoop_type11` | 0x98DF40 |

---

### `uEffectVFR::moveGeneratorSetLoop` — 0x9DDB00

Called once per newly spawned particle immediately after `initParticle`. Six steps:

1. **Parity toggle**: `mSpawnParity ^= 1` — alternates between 0 and 1 for even/odd burst indexing.
2. **Spawn count math**: accumulates `mSpawnTimer += emitRate * deltaTime`; integer part = particles to spawn this frame.
3. **Delta computation**: computes interpolated spawn position between current and previous generator position using `burstT` (0.0-1.0 lerp parameter).
4. **Local-space bind**: if the generator has a parent object, multiplies the spawn position by `mLocalMatrix` to transform to local space.
5. **`initParticle` call**: dispatches to `uEffectVFR::initParticle` with the spawned particle pointer, generator param block, `pPtclData`, `burstT`, and output direction pointer.
6. **Active list link**: calls `openParticle` to insert the new particle into the active list.

---

### `uEffectVFR::initParticle` — 0x970F10

1438-instruction initialization function for a newly spawned particle. Signature (after annotation):

```c
int __userpurge uEffectVFR::initParticle@<eax>(
    int pEffect@<edi>,
    uEffectVFR::Generator *pGen,
    int pParticle,
    uEffectVFR::ptclData *pPtclData,
    float burstT,
    float *pDirOut)
```

Nine phases:

1. **Parameter block fetch**: reads `pGeneratorParam` from `pGen+0x44`; stores in local.
2. **`burstT` local copy**: `burstT_local = burstT` — x87 store to stack (unavoidable `__asm` at 0x970FA7).
3. **Emitter shape dispatch** (4 cases): selects spawn position based on shape type (point/sphere/box/cylinder); writes to `spawnPos` matrix and `inheritedPos` fields.
4. **Inline matrix inversion** (~200 instructions): if particle has a parent attachment, computes full 4x4 cofactor expansion to get inverse world matrix of the parent, then transforms spawn position into parent-local space. Hand-unrolled, not a library call.
5. **Velocity computation** (7 move-type sub-dispatch): reads base velocity from params, applies randomization, writes `velX/Y/Z` locals.
6. **`mParticleType` sub-dispatch** (18 types): sets initial visual state (`ptclScale`, `ptclScaleArg_a/b/c`) and calls a type-specific init sub. Switch key = `mParticleType` (Generator+0xC1), NOT a per-node "render type". Values below are writer-sourced (verified via `initGeneratorParam` @0x96B691 — see the `mTransType` section near the end of this file); 16/17 are taken from the corrected table there:

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

Pops one node from the stock (free) list and pushes it onto the active (move) list.

- Reads `pStockHead` — if null, returns 0 (pool exhausted).
- Advances `pStockHead` to `node->pNext`, patches `pNext->pPrev` if list non-empty.
- Appends to `pActiveTail`; updates both list head/tail pointers as appropriate.
- Increments `mParticleCount`.
- Returns the new particle pointer.

---

### `uEffectVFR::Generator::closeParticle` — 0xB1ABE0

Two paths depending on whether the particle is the list tail:

- **Mid-list**: unlinks node by patching `prev->pNext` and `next->pPrev`; pushes to stock head.
- **Tail**: advances `pActiveTail`; pushes node to stock head.
- Decrements `mParticleCount`.

---

### `uEffectVFR::Generator::finishSoundAndCallback` — 0x9DE140

Called when `mAge >= mLifespan`:

1. If `mSoundHandle != 0`, stops via `sSound::stopSound(mSoundHandle)` and zeros handle.
2. If `pSoundCallback != nullptr`, calls `pSoundCallback(pEffect, pGen)`.
3. Sets generator expired flag in `mFlags`.
4. If `pEffectCallback != nullptr`, calls `pEffectCallback(pEffect)`.

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
| `moveGenerator` | `cParticleGenerator::updateSingleGenerator` | Matching logic; different offsets |
| `openParticle` | `cParticleGenerator::openParticle` | Name confirmed via PDB |
| `closeParticle` | `cParticleGenerator::closeParticle` | Name confirmed via PDB |
| `finishSoundAndCallback` | `cParticleGenerator::finish` (approx.) | Naming inferred |
| `initParticle` | `cParticleGenerator::setup` (approx.) | Naming inferred |
| Render-type enum (18 types) | Identical enum values | **Exact match verified** |
| Move-loop dispatch | SE uses virtual dispatch; DX9 uses switch | Implementation differs |

SE subclasses of `cParticleGenerator` (reference only):
`cBillboardGenerator`, `cPolygonGenerator`, `cPolylineGenerator`, `cLineGenerator`,
`cTexlineGenerator`, `cModelGenerator`, `cLensflareGenerator`, `cDecalGenerator`,
`cLightGenerator`, `cDistortionGenerator`

---

## Generator state-machine tick + emit/spawn pipeline (2026-05-28)

This session cross-referenced `sub_9DDBF0` against SE `cParticleGenerator::updateSingleGenerator`
(SE `0xD93710`, demangled from `?updateSingleGenerator@cParticleGenerator@@IAEIXZ`) and traced the
DX9 emit path down to the particle pool allocator.

### `sub_9DDBF0` — generator state-machine tick (renamed: kept as `sub_9DDBF0`, commented)

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
| 1 | wait/countdown | if `mSetTimer` `--`; else `emit_request()`, → 3, fall through | (gated by `mStatus&4`) if counter `--`; else `setRequest()`, → 3, `finish()` |
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
| 1 | `sub_9DDBF0` | simpler variant — no firing-effect dispatch, no loop reseed |
| 2 | `uEffectVFR::uknGenBehaviorFunc1` (0x9DDCB0) | full variant — closest DX9 match to SE `updateSingleGenerator` |

So `sub_9DDBF0` and `uknGenBehaviorFunc1` are **sibling behaviour modes, not duplicate functions** — both
operate on the same `uEffectVFR::Generator` layout (state nibble in `mFlags` @ +0x18, `mSetTimer` @ +0x30,
`mLoopCtr` @ +0x32, counters `mTimer`/`mSetParticleTotal`/`mSetFrameTotal` @ +0x24/+0x28/+0x2C).

### `uEffectVFR::uknGenBehaviorFunc1` — 0x9DDCB0 (type-2 behaviour)

6-state machine (state = `HIBYTE(mFlags) & 0xF`), returns the per-frame spawn count. Signature applied:
`int __usercall …@<eax>(uEffectVFR::Generator *pGen@<edi>, uEffectVFR *owner@<esi>)`.

| State | Role |
|-------|------|
| 0 init | zero `mTimer`/`mSetParticleTotal`/`mSetFrameTotal`; `mSetTimer = mWaitFrame`; → 1 |
| 1 wait/fire | if `mSetTimer--` nonzero return 0; else `emit_request()`, pick firing effect via `sub_95FD00` (RNG = `sDevil4Effect::mpInstance[+0x20 + 4*(++owner->mRandCtr & 0xFFF)]`), store handle in `mLoopCtr`; → 2 |
| 2 setup | `uknGeneratorTimerFunc` reseeds `mSetTimer` from `LoopNum` param; → 3 |
| 3 active | if `mStatus & 0x20` run effect (`sub_963EC0`/`sub_964060`), else fire `sub_95FD00`; then spawn-count smoothing (`mFlags` bits 0x400000/0x800000 + `>>1` halving spreads count across frames); falls into loop logic |
| 4 loop | `--mSetTimer`; at 0 decrement `mLoopCtr`; if exhausted set `mStatus \|= 0x8000` (finished) → 5, else `uknGenLoopFunc` reseed (`SetFrame` param) → 2 |
| 5 run | `++mTimer` |

**Reseed helpers (= SE `case 6` revival math):**

- `uEffectVFR::uknGeneratorTimerFunc` (0x9DE250) — reseeds from `LoopNum` (per-burst loop window) + `SetInterval` fractional distribution.
- `uEffectVFR::uknGenLoopFunc` (0x9DE360) — reseeds from `SetFrame` (inter-burst interval) + `SetFrameDist`.

Both compute `base.s + rand % (base.r + 1)` using `sDevil4Effect::mpInstance[+0x20 + 4*(randCtr&0xFFF)]` as
the RNG — the DX9 equivalent of SE's `MtMath::mTrandom[mRandCtr & 0xFFF] % (RevivalFrame + 1)`. This is what
confirms `uknGenBehaviorFunc1` (not the count-less `sub_9DDBF0`) carries SE's `case 6` revival/loop semantics.

The `*(float *)&pGen` artifact in the two timer-func calls is benign: the helpers declare their first
param as `float@<edi>` and merely receive `pGen` through edi.

### `uEffectVFR::Generator::emit_request` — 0x9DDF40 (was `sub_9DDF40`)

DX9 analog of SE `cParticleManager::setRequest` (SE `0xDBE750`). **The bodies diverge by build:**

- **SE `setRequest`**: emits a controller **vibration** (`sVibration::reqVib`) + a sound request.
- **DX9 `emit_request`**: **spawns particles** via the `particle_pool::spawn_*` family + a sound
  request (`sDevil4Sound::requestSe(sSoundN::mpInstance, …)`).

They map because they share the same skeleton and call site (state 1→3): switch on a spawn-mode byte
in the generator param block (`mpGeneratorParam + 0x138`) → write the resulting handle to
`pGen->member_0x21c` → `if (handle != -1) mStatus |= 0x1000` → trailing `if (mResourceInfo[+0x28])`
sound branch (sets `mStatus |= 0x2000`). SE's analog flag bits are `0x10`/`0x20`/`0x40`.

| Spawn mode (`+0x138` byte) | DX9 wrapper called |
|---------------------------|--------------------|
| 0 | (skip — no spawn) |
| 1 | `particle_pool::spawn_simple` |
| 2 | `particle_pool::spawn_at_pos` (passes generator world pos `mWmat.vectors[3]`) |
| 3 | `particle_pool::spawn_with_parent` (if `param_1[+24]`), else `spawn_at_pos` |

### Particle pool / record pipeline

```
emit_request (0x9DDF40)
  ├─ mode 1 → particle_pool::spawn_simple      (0x908920) ─┐
  ├─ mode 2 → particle_pool::spawn_at_pos      (0x908990) ─┤ CRITICAL_SECTION-guarded wrappers
  └─ mode 3 → particle_pool::spawn_with_parent (0x908A10) ─┘
                         │
                         ▼
          particle_pool::alloc_slot (0x909A10)
              scans 8-slot × 176-byte (0xB0) array, bails if used ≥ 8,
              bumps 31-bit rolling serial, returns slot addr (176*i + base + 112)
                         │
                         ├─ particle_rec::init (0x909AE0)
                         │     refcount cResource (+0x10, addRef/release), read 16B descriptor,
                         │     set type flags 0x11/0x22/0x100/0x200 (+0x2C),
                         │     fill ten 1.0f ramp floats (+0x30..+0x54), zero pos vecs (+0x70/+0x80/+0x90)
                         │
                  per mode, post-alloc configurator:
                  ├─ spawn_simple      → reads slot serial (+0x1C)
                  ├─ spawn_at_pos      → particle_rec::set_position   (0x909E30)
                  └─ spawn_with_parent → particle_rec::attach_parent  (0x909E80)
                         │
                         ▼
          particle_rec::resolve_transform (0x90A1B0)
              resolve parent-joint world transform (vtable +0x3C → translation),
              then per-channel distance attenuation (dmc4_sqrt of squared deltas,
              near/far ramp) into channel arrays +0x30 (2 ch) / +0x38 (8 ch).
              Shared finalize — also called from sub_909CA0.
```

**Pool object** (the implicit `this` in `alloc_slot`): `CRITICAL_SECTION` @ +0x04, job-safe flag
@ +0x28 (also gated by `cSystem::mJobSafe`), rolling 31-bit serial @ +0x68, 8-slot array of 176-byte
records from ~+0x70/+146. Reached **only** via the three `spawn_*` wrappers. Records are SE `cParticle`-like.

**Scope check (xrefs):** the `spawn_*` API has exactly two callers — `emit_request` (0x9DDF40) and a
sibling `sub_9098D0` (same mode-switch shape). So this is a tightly-scoped effect-spawn subsystem,
not a generic engine pool — but the class identities (`particle_pool`, `particle_rec`) are **inferred
from SE layout, not confirmed by a DX9 DTI/vtable**, hence the lowercase placeholder names.

### Names applied this session (all placeholders — lowercase per CLAUDE.md)

| Addr | New name | Notes |
|------|----------|-------|
| 0x9DDF40 | `uEffectVFR::Generator::emit_request` | class confirmed (existing DX9 type); method placeholder |
| 0x909A10 | `particle_pool::alloc_slot` | inferred class |
| 0x909AE0 | `particle_rec::init` | inferred class |
| 0x90A1B0 | `particle_rec::resolve_transform` | inferred class; shared finalize |
| 0x909E30 | `particle_rec::set_position` | inferred class |
| 0x909E80 | `particle_rec::attach_parent` | inferred class |
| 0x908920 | `particle_pool::spawn_simple` | inferred class |
| 0x908990 | `particle_pool::spawn_at_pos` | inferred class |
| 0x908A10 | `particle_pool::spawn_with_parent` | inferred class |

`sub_9DDBF0` left un-renamed (only commented) pending the 0x96FD00 reconciliation above.
Cross-ref comments documenting the SE correspondence were applied at all ten function heads.

---

## Move-param dispatch — `uEffectVFR::uknMoveFunc1` (0x9DE1B0) — 2026-05-28

User hypothesis: maps to the `mpPath` block in SE's `cParticleGenerator::move`. **Confirmed (partial/divergent).**

### What it is

A discrete **move-param dispatch step** invoked from within the per-frame generator tick.
DX9 xref is conclusive: `uknMoveFunc1` has exactly **one caller** — `uEffectVFR::Generator::update` (0x9DDAE0, @0x9ddbd6). So it is a "block within move" exactly as the user framed it, from DX9 evidence (not just inferred from SE).

Dispatches on **`mMoveType`** (`Generator+0xC3`; confirmed via disasm `movzx eax, byte [edi+0C3h]` @0x9de1db) with a **one-shot first-frame guard**. (The `+0xE4` field `mMoveSpreadCount` is **not** the selector — it appears only as an *argument* in the mMoveType==4 branch.)

- Guard = `mFlags & 0xF0000000` (bit `0x10000000`, bits 28–31). On first call the test is zero → init branch runs and the bit is set; thereafter the else (per-frame) branch runs.
- ⚠️ **This guard bit is NOT the state nibble.** The tick state machine documented earlier keys on `HIBYTE(mFlags) & 0xF` = bits **24–27**. The move guard is bits **28–31** of the same dword — a separate one-shot flag. Do not conflate them.

| mMoveType | first frame (guard clear) | subsequent (guard set) |
|-----------|---------------------------|------------------------|
| 3 | `movepath_strip_lengths(param, pGen, 1)` | `movepath_strip_lengths(param, pGen, 0)` |
| 4 | `movekf_init_apply` (init+sample+apply) | `movekf_update_apply` (re-sample+apply), only if `!param_2` |
| other | no-op | no-op |

### Callees (renamed, lowercase placeholders)

| Addr | New name | Role |
|------|----------|------|
| 0x9DE470 | `uEffectVFR::Generator::movepath_strip_lengths` | mMoveType==3: walk path point list, write running per-segment distance array into `rec+228`. Path sub-type at `mpMoveParam+120`: case1=open polyline, case2=multi-strip, case3=loop. |
| 0x984250 | `uEffectVFR::Generator::movekf_init_apply` | mMoveType==4 first frame: set rec init bytes (+0x1C=1, +0x1D=type), sample up to 4 keyframe channels via `sub_963EC0` (mask `rec+0x1E` bits 0x4/0x8/0x10/0x20), tail-call apply `movekf_apply_tail`-sibling `sub_984350` with AxisZ basis. |
| 0x994B40 | `uEffectVFR::Generator::movekf_update_apply` | mMoveType==4 per-frame: re-sample the same 4 channels, tail-call apply `movekf_apply_tail`. |
| 0x994C20 | `uEffectVFR::Generator::movekf_apply_tail` | apply-tail: keyframe-driven per-particle **orientation/direction** build + emit. Calls `uEffectVFR::calcKeyframeF32`/`calcKeyframeVector`/`calcDir`, builds an **axis-angle quaternion** rotation, writes particle dir vectors (rec +0x50/+0x5C/+0x80), then loops emitting/transforming each particle in the strip. |

### SE correspondence (hedged)

The SE generator move dispatcher is `cParticleGenerator::moveParticleMove` (SE **0xDBDBA0**) — a 12-way switch on a 4-bit move-type field `(... >> 20) & 0xF`, dispatching to `moveParticleMove{None,Add,Mul,PathStrip,PathChain,PathKeyframe,PathLine,Custom,Spin,AddFast,MulFast,SpinFast}`. The four `Path*` variants are the "mpPath block."

- **mMoveType==3 (DX9)** matches the **SE PathStrip family** — `movepath_strip_lengths` builds the per-segment distance array, the same job as SE `getPathStripLengthArraySize` / `updateParticleMovePathStripDistance`.
- **mMoveType==4 (DX9) = SE PathChain** (CONFIRMED 2026-05-29 by structurally matching the per-particle integrators against SE — see the move-type init section below). `sub_994C20` (the per-frame generator facet of mMoveType==4) does keyframe-driven **orientation**; chain motion builds per-node orientation quaternions too, so `sub_994C20` is the orientation facet of *chain* — **not** evidence of a separate "keyframe type." (Earlier this section guessed mMoveType==4 ≈ PathKeyframe "not chain"; that was wrong — it leaned on `calcKeyframe*` usage, which all move-types share and which does not discriminate.)

Net: DX9 `uknMoveFunc1` is the **path/move-param slice** of the SE move dispatch, reached per-frame from `Generator::update` — confirming the user's "mpPath block in move" reading. The full DX9→SE move-type mapping (3=Strip, 4=Chain, 5=Keyframe, 6=Line) is resolved in the section below.

---

## Per-particle motion-model init — `initParticle`'s `mMoveType` switch (cases 0–6) — 2026-05-29

The final `switch (pGen->mMoveType)` in `initParticle` (0xC3, **same enum** as `uknMoveFunc1`) seeds the particle's **move-work block** (`pPtclData + mMoveWorkOffset`) with randomized motion parameters. One initializer per move-type. All share a skeleton: sample randomized values from `mpMoveParam` via the effect RNG (`sDevil4Effect::mpInstance[idx*4 + 16416]` floats / `+32` ints), drive keyframe curves (`calcKeyframeF32`/`calcKeyframeVector`/`calcDir`), and set a per-particle flag accumulator at move-work `+0x68` (word). They differ in motion model.

### Initializers (renamed; lowercase placeholders, subtype-neutral)

| case | addr | name | model | SE correspondence |
|------|------|------|-------|-------------------|
| 0 | 0x972D60 | `initParticleMoveNone` | direct/none: copy basis, optional single fixed normalized velocity | **CONFIRMED** `initParticleMoveNone` |
| 1 | 0x972F00 | `initMove1_vel` | velocity: sample vel + speed + accel via `movevel_transform`; returns 0x180 | velocity-family — Add/Mul *(hedged: not decidable from init; lives in the move-loop)* |
| 2 | 0x973460 | `initMove2_vel` | velocity (sibling of case 1, minor scheduling diff) | the other Add/Mul (or *Fast) *(hedged)* |
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

### Reconciliation with the `uknMoveFunc1` section above (important)

`uknMoveFunc1` and this `initParticle` switch read the **same byte** `mMoveType@0xC3` — **not** different enums. They are **different stages of the same move-type**:
- `uknMoveFunc1` = per-frame, generator-level move-spread setup (only acts on mMoveType 3 & 4 — the path types — consistent with path-spread mattering only for path motion).
- `initParticle`'s switch = per-particle spawn init.

For **mMoveType==4** specifically: the generator facet (`uknMoveFunc1` → `movekf_apply_tail`/sub_994C20) does **keyframe orientation**; the per-particle facet (`initMove4_pathstrip` → `movepath_strip_pos2`) does **strip position**. Both true and complementary — the earlier "orientation, not chain" note correctly describes sub_994C20 and stands.

### Path-subtype resolution (2026-05-29, SE cross-referenced)

The path-subtype split was confirmed by decompiling SE's four `cParticleGenerator::calcParticleMovePath{Strip,Chain,Keyframe,Line}Pos` and matching each DX9 integrator by **structural fingerprint** (not case position):

- **Strip** — `switch` over an interpolation mode (linear/hermite/spline) while walking the point-list. DX9 `calcParticleMovePathStripPos` (0x975440) has the identical 3-way `switch(mpMoveParam+120)`.
- **Chain** — walks the point-list **and** builds a per-node orientation quaternion + full 4×4 inverse frame. DX9 `calcParticleMovePathChainPos` (0x975BA0) is the only integrator doing both.
- **Keyframe** — no walk, no clamp, `return 0`; applies scale+rot to a precomputed offset. DX9 `calcParticleMovePathKeyframePos` (0x977070) matches exactly.
- **Line** — clamps distance (non-wrapping) and moves along a single axis vector, no segments. DX9 `calcParticleMovePathLinePos` (0x977240) matches.

So **mMoveType 3/4/5/6 = Strip/Chain/Keyframe/Line** — which also happens to be SE's `moveParticleMove` dispatcher order (cross-validation). The match is structural; the sequential agreement is confirmation, not the basis. Cases 3/4/6 all walk point-lists, so the discriminators are: Strip=interp-mode switch, Chain=per-node inverse frame, Line=clamp+axis (no walk).

**Still hedged:** cases **1/2** (velocity-family) — Add-vs-Mul(-vs-Fast) is not decidable from the init function; that distinction lives in the per-frame `moveParticleLoop_*` functions. Names left neutral (`initMove1_vel`/`initMove2_vel`).

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
  Hypothesis (UNVERIFIED): selects world-oriented vs screen/free prim build.

### `mTransType` is NOT a new enum — it is `mParticleType` + a "Lite" render-variant remap

Ground truth: **`uEffectVFR::initGeneratorParam` (0x96B691)** is the writer. It `switch`es on
`mParticleType` (Generator+0xC1) and stores `mTransType` (Generator+0x1D). The remap depends on the
descriptor's **Lite-particle flag** `(EFL_PARTICLE_COMMON+2 & 1)` (= SE `mLiteParticleFlag`):

| mParticleType | Name | mTransType (normal) | mTransType (Lite flag set) |
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

Consequences, all consistent with the dispatcher's case table:
- **Cases 0x11–0x1C are the Lite-variant draws** (mLiteParticleFlag set): 0x11–0x17 = lite of types
  0–6, 0x18–0x1B = lite of 12–15, **0x1C = lite of SizeBillboard(17)**.
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
sets numerous generator flags; for the Lite/keyframe types it additionally calls
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
`uEffectVFR::render<Type>` for variant B (`mAxisType&0x400` clear) and `render<Type>_axis` for variant A
(flag set); Lite cases use `<Type>Lite`. Types: Billboard, Polyline, Polygon, Texline, Line, Model,
LensFlare, MassBillboard, PolygonStrip, Texline13, Line14, PolygonStrip15, SizeBillboard, and their
Lite variants. 46 functions renamed, 0 geometry contradictions.

- **MassBillboard (case 0x8)** is a renderer but uses a **batched** submission path (builds a 16-DWORD/
  particle vertex buffer, one submit via `calcPrimMaterial` + `sub_AA87C0`) instead of per-particle
  `getcPrim` — consistent with "mass" billboard. Named, deviation noted in its comment.
- **PrimModel (case 0x6) and PrimModelLite (case 0x17)** are NOT leaf renderers in either variant.
  Each is a 0x73-byte second-level dispatcher: `if(ptr) switch(mpParticleParam[+0x170] & 0xF)` fanning
  out to 6 PrimModel sub-renderers. So PrimModel has its own 6-way render family (24 subs total across
  the 4 axis/lite cells, range ~0x9B5D20–0x9CBE10), mirroring SE's separate `cParticleGeneratorPrimModel`
  hierarchy. These 4 dispatchers are left unnamed/annotated; the 24 sub-renderers are unmapped (future work).
- **case 0x1D = LiteBillboard** has no leaf — it defers to a virtual (`vtbl[+48]`/`vtbl[+49]`).
