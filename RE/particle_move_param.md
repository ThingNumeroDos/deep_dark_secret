# uEffectVFR Particle Move-Param Work Block (DX9)

Per-particle **motion state** struct, written at spawn by the `mMoveType` init dispatch and updated each
frame by the `moveParticleMove*` family. It lives at `particleNode + Generator.mMoveWorkOffset` (a runtime
offset, `Generator+0xCC`), **not** at a fixed node offset. DX9 types: `uEffectVFR::Move*`
(`uEffectVFR::MoveCommon` base + per-type tail). SE-equivalent family: `cParticleMove*`.

Recovered by comparing **DX9 `uEffectVFR::moveParticleMoveNone` (0x995E60)** with
**SE `cParticleGenerator::moveParticleMoveNone` (0x DBA5A0)** plus the DX9 writers
`setupMoveParamCommon` (0x972C40) and `initParticleMoveNone` (the `mMoveType==0` init).

> **Layout is DX9-reordered vs SE.** SE `cParticleMoveNone` = `[cParticleMoveCommon 0x20][cEffectStrip mStrip 0x20]`
> with `mCurDir` at common+0x0 and the status word at common+0x10. DX9 (`uEffectVFR::MoveNone`) drops the leading
> `mCurDir`, puts the **status word first**, and lays the block out as below. SE gives field **names**; DX9 code
> gives every **offset**.

## `uEffectVFR::MoveNone` — DX9 layout (0x40), by-use confirmed

(DX9 name; SE-equivalent `cParticleMoveNone`.)

| Off | Field | Type | Evidence |
|-----|-------|------|----------|
| +0x00 | `mCommon` | `uEffectVFR::MoveCommon` | see below |
| +0x10 | `mOfs` | MtFloat3 | move reads +0x10/14/18, scales by `Generator.mLscale`, transforms by `mWmat` → world pos. = SE `mStrip.mOfs`. |
| +0x1C | `_spawnBasisTail` | char[0x14] | `initParticleMoveNone` copies **4 spawn-basis qwords** into +0x10..+0x2F. For the None type this region is spawn-transform data, **not** strip metadata — left opaque. |
| +0x30 | `mCurDir` | MtFloat3 | init writes normalized spawn-dir × sampled magnitude here (else 0); move copies it to the out-dir param. SE writes `mCurDir` the same way in init. |
| +0x3C | `mInitFlag` | int | init writes `ptclFlags & 0x180`; move sign-tests it to gate the 0x80 status bit. |

### `uEffectVFR::MoveCommon` — DX9 base (0x10)  (SE-equivalent `cParticleMoveCommon`)

Written by **`setupMoveParamCommon` (0x972C40)** — the shared move-init run for *all* move types before the
`mMoveType` switch.

| Off | Field | Notes |
|-----|-------|-------|
| +0x00 | `mMoveRno` (byte0) | 2-bit **mode**, set by value from the collision-resource config (see MOVE_OPTION_FLAG below). |
| +0x01 | `mBounceCtr` (byte) | bounce/hit counter; decremented in `moveParticlePosCollision`. |
| +0x02 | `mCollFrameTimer` (word) | collision re-check countdown; decremented in collision, skips the cast while non-zero. |
| +0x04 | `mForceRate` | float (force/scale rate); `&4` ramp accumulator source in collision. |
| +0x08 | `mCollRadius` | float (from resource +8). |
| +0x0C | `mBounceRate` | float (sampled from resource +40/+44). |

> SE-named scalars `mForceRate/mCollRadius/mBounceRate` are offset-correspondence-derived (written by
> `setupMoveParamCommon`, read in collision) — reasonable, not each individually by-use-proven.

### `uEffectVFR::EffectStrip` (SE-equivalent `cEffectStrip` — interior NOT DX9-verified)

Recreated from the SE leaked PDB for naming reference only. Its interior fields
(`mPartsNo/mRno/mStripFlags/mVertexNo/mVertexNum/mBlendRate0/1`) are **unverified in DX9** — the bytes they
name are spawn-basis floats in the None path. Confirm these in the **PathStrip** move type (`mMoveType==3`),
where code actually reads `mVertexNo`/`mBlendRate`. (A `// SE-derived, NOT DX9-verified` type comment is set on
the struct in the IDB.)

## `mMoveRno` ↔ `rEffectList::MOVE_OPTION_FLAG`

**Question:** does `mMoveRno` reference `MOVE_OPTION_FLAG`, and does it line up in DX9? **Answer: yes, as a 2-bit
mode — not as the OR-able flag bitmask.**

`setupMoveParamCommon` sets the low 2 bits of the status word **by value** from the collision resource
(`Generator+0xD4`):
- collision resource **present** → `(status & ~3) | 1` = `MOVE_OPTION_FLAG_COLLISION` (0x1)
- collision resource **absent** → `(status & ~3) | 2` = `MOVE_OPTION_FLAG_GRAVITY_NO_SCALE` (0x2)

These are written `&~3 | n` (exactly one of bit0/bit1 ever set) → a **mutually-exclusive 2-bit mode**, matching
SE's PDB `mMoveRno:2`. So the values are drawn from `MOVE_OPTION_FLAG`, but the runtime field is a 2-bit view,
**not** the full enum. `moveParticleMoveNone`'s `mMoveRno & 3 == 1` = "COLLISION set, GRAVITY clear" → run
`moveParticlePosCollision`.

The runtime status **dword** also packs counters (`mBounceCtr`@+1, `mCollFrameTimer`@+2), so it cannot *be* the
enum (high bits like `FAST`=0x1000000 physically can't live there). `rEffectList::MOVE_OPTION_FLAG` is the
**descriptor-side** enum (recreated in the DX9 IDB as a bitfield for reference); it is not applied to the runtime
word.

### bit2 — UNRESOLVED
`setupMoveParamCommon` sets bit 2 when `*(resource+4) != 0`. Conflicting labels:
- SE PDB `cParticleMoveCommon` → `mGravityScaleFlag` at bit 2
- `MOVE_OPTION_FLAG` → `HIGH_ACCRACY` = 0x4

In `moveParticlePosCollision` the `&4` branch accumulates `*(resource+4)` into the displacement each frame
(clamped to a max), which **leans gravity/force ramp**, agreeing with the SE PDB over the enum label. Left
**neutral** pending confirmation.

## All move types (0–6) — recovered

Every move type's work block begins with the shared **`uEffectVFR::MoveBase`** (0x40) and adds a per-type tail.
`MoveBase` = `MoveCommon` (0x10) + velocity scalars + dir + rates + status, then per type:

| mMoveType | DX9 struct | size | tail (after MoveBase / MoveCommon) | SE-equivalent |
|-----------|-----------|------|------------------------------------|---------------|
| 0 None | `uEffectVFR::MoveNone` | 0x40 | (uses MoveCommon directly: mOfs@0x10, mCurDir@0x30, mInitFlag@0x3C) | `cParticleMoveNone` |
| 1/2 Vel | `uEffectVFR::MoveVel` | 0x4C | `mSpeedVec`@0x40 | `cParticleMoveAdd`/`cParticleMoveMul` |
| 3 PathStrip | `uEffectVFR::MovePathStrip` | 0x78 | `_spawnBasis`@0x40, `mRot`@0x60, `mDistanceRate[2]`@0x70 | `cParticleMovePathStrip` |
| 4 PathChain | `uEffectVFR::MovePathChain` | 0x5C | `mOfs`@0x40, `mRot`@0x50 | `cParticleMovePathChain` |
| 5 PathKeyframe | `uEffectVFR::MovePathKeyframe` | 0x7C | `_spawnBasis`@0x40, `mRot`@0x60, `mOfsKeyframeRate`@0x70 | `cParticleMovePathKeyframe` |
| 6 PathLine | `uEffectVFR::MovePathLine` | 0x6C | `_spawnBasis`@0x40, `mRot`@0x60 | `cParticleMovePathLine` |

> All sizes are max-offset-touched (DX9), **not** SE's sizes. DX9 layout = SE's `cParticleMoveBase` family shifted
> **−0x10** (DX9 `MoveCommon` is 0x10 vs SE's 0x20). SE gives names; DX9 code gives offsets.

### `uEffectVFR::MoveBase` (0x40) — shared prefix

| Off | Field | Notes |
|-----|-------|-------|
| +0x00 | `mCommon` (MoveCommon) | status/flags/collision (written by `setupMoveParamCommon`) |
| +0x10 | `mSpeed` | all types; descriptor `mpMoveParam[2].ForceRate` (+40/44) or speed keyframe |
| +0x14 | `mForceScalar` | **POLYMORPHIC**: Vel → `mAcceleration` (descriptor +64/68); path types → drag (descriptor ForceRate +72/76). Same offset, different field by move type. Reader-unconfirmed. |
| +0x18 | `mGravity` | Vel-only; descriptor +48/52, ×`mWscale.y` when gravity-scale on |
| +0x1C | `mFallSpeed` | Vel-only; descriptor ForceRate.r +60, ×`mWscale.y` |
| +0x20 | `mDir` (MtFloat3) | initial dir (random or keyframe, descriptor +56); all types |
| +0x2C | `mSpeedKeyframeRate` | |
| +0x30 | `mFallSpeedKeyframeRate` | |
| +0x34 | `mMoveStatus` (word) | per-type status bits (0x2/0x10/0x12/0x30/0x32/0x40/0x80/0x100/0x300) |
| +0x36 | `mReleaseTimer` (word) | path-only; reach-frame count (calcKeyframeU32, descriptor +66/68/70) |
| +0x38 | `mDistance[2]` | path-only reach-distance pair (descriptor +112/116) |

Field-by-field validation used **descriptor source-offset matching** (a field is named only when its `mpMoveParam`
read offset matches the SE init's read for that named field), not positional SE-paste — the one slot that differs by
type (+0x14) is flagged generic.

### `_spawnBasis` is opaque (PathStrip/Line/Keyframe)

The 0x20 block at +0x40 in the three strip/line/keyframe types is filled at init from **4 spawn-transform qwords**
(`p_y`), not parsed strip-config. Proof: the integrators (`calcParticleMovePathStripPos` 0x975440 etc.) read the
actual path point-list from the **resource** (`param_3[13]+24`, indexed by a parts index), never from this block —
it's a spawn-transform cache, consumed by the final world-transform. So `cEffectStrip`'s structured interior
(`mVertexNo`/`mBlendRate`) lives in the resource, **not** the runtime work block — left `char[0x20]` opaque.
(PathChain instead stores a genuine `mOfs` vec3 there, named.)

### Add vs Mul (type 1 vs 2)
Both DX9 inits (`initMove1_vel` 0x972F00, `initMove2_vel` 0x973460) write a single velocity vector (`mSpeedVec`
@+0x40); neither writes a second acceleration vector. So Add vs Mul is **indistinguishable from the init side** —
one neutral `uEffectVFR::MoveVel` covers both (SE splits them as `cParticleMoveAdd` 0x70 with mSpeedVec+mAccelVec
vs `cParticleMoveMul` 0x60 with mSpeedVec only).

## Functions named/typed

| Addr | Name | Role |
|------|------|------|
| 0x972C40 | `uEffectVFR::Generator::setupMoveParamCommon` | shared move-param init (writes `MoveCommon`); runs for all move types before the switch. |
| 0x995E60 | `uEffectVFR::moveParticleMoveNone` | type 0 per-frame update. |
| 0x99A210 | `uEffectVFR::Generator::moveParticlePosCollision` | ray-cast + bounce collision. |
| 0x99BEA0 | `uEffectVFR::moveParticleMoveVel` | type 1/2 per-frame (generator-global velocity add). |
| 0x972F00 / 0x973460 | `initMove1_vel` / `initMove2_vel` | type 1/2 spawn init. |
| 0x9739D0 | `initParticleMovePathStrip` + integrator 0x975440 | type 3. |
| 0x974040 | `initParticleMovePathChain` + integrator 0x975BA0 | type 4. |
| 0x974560 | `initParticleMovePathKeyframe` + integrator 0x977070 | type 5. |
| 0x974A50 | `initParticleMovePathLine` + integrator 0x977240 | type 6. |
| 0x996D60 / 0x9974B0 / 0x997BF0 / 0x998490 | `moveParticleMovePath{Strip,Chain,Keyframe,Line}` | per-frame path move subs. |

## Open / reader-unconfirmed
- **+0x14 (`mForceScalar`)** path-type meaning (drag vs other) is writer-confirmed only; the move-side path subs
  (`moveParticleMovePath*`) would pin it positively. Disproportionate to read 5 more subs for one slot — left flagged.
- **bit2** of `MoveCommon.mMoveRno` (gravity-scale vs HIGH_ACCRACY) — still neutral (see above).
