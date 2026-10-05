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

### bit2 — RESOLVED (2026-10-05): collision radius growth
`setupMoveParamCommon` sets bit 2 when the collision block's `CollRadiusAdd` (+0x04) is non-zero. In
`moveParticlePosCollision` the `&4` branch adds `CollRadiusAdd` to the collision radius every frame, clamped to
`CollRadius.s + CollRadius.r`. The SE PDB name `EFL_PARAM_COLL::CollRadiusAdd` at the same offset confirms it.
So bit 2 means **"collision radius grows each frame"**: neither `mGravityScaleFlag` nor `HIGH_ACCRACY`.

## All move types (0–6) — recovered

Every move type's work block begins with the shared **`uEffectVFR::MoveBase`** (0x40) and adds a per-type tail.
`MoveBase` = `MoveCommon` (0x10) + velocity scalars + dir + rates + status, then per type:

| mMoveType | DX9 struct | size | tail (after MoveBase / MoveCommon) | SE-equivalent |
|-----------|-----------|------|------------------------------------|---------------|
| 0 None | `uEffectVFR::MoveNone` | 0x40 | (uses MoveCommon directly: mOfs@0x10, mCurDir@0x30, mInitFlag@0x3C) | `cParticleMoveNone` |
| 1 Add | `uEffectVFR::MoveAdd` | 0x5C | `mSpeedVec`@0x40, `mAccelVec`@0x50 | `cParticleMoveAdd` |
| 2 Mul | `uEffectVFR::MoveMul` (ex-`MoveVel`) | 0x4C | `mSpeedVec`@0x40 (rate = `mForceScalar`@0x14) | `cParticleMoveMul` |
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

### Add vs Mul (type 1 vs 2) — RESOLVED 2026-10-05
An earlier version of this section said neither init writes a second vector. That was wrong:
- `initParticleMoveAdd` (0x972F00, ex-`initMove1_vel`) writes `+0x14`, `mSpeedVec` +0x40..0x48 **and** `mAccelVec`
  +0x50..0x58 → `uEffectVFR::MoveAdd` (0x5C, declared).
- `initParticleMoveMul` (0x973460, ex-`initMove2_vel`) writes only `+0x14` (the multiply rate) and `mSpeedVec` → `uEffectVFR::MoveMul`
  (the old `MoveVel` type, renamed).

Per frame (`move_particle_move` 0x995CF0): `moveParticleMoveAdd` (0x996160) does `speed += accel`, and
`moveParticleMoveMul` (0x996760) does `speed *= rate(+0x14)`. Both add gravity(+0x18) into fallSpeed(+0x1C). That settles
the polymorphic `+0x14`: for type 2 it is the **Mul rate**. For type 1 it is written but not used by the Add step
(still unnamed for Add).

## Functions named/typed

| Addr | Name | Role |
|------|------|------|
| 0x972C40 | `uEffectVFR::Generator::setupMoveParamCommon` | shared move-param init (writes `MoveCommon`); runs for all move types before the switch. |
| 0x995E60 | `uEffectVFR::moveParticleMoveNone` | type 0 per-frame update. |
| 0x99A210 | `uEffectVFR::Generator::moveParticlePosCollision` | ray-cast + bounce collision. |
| 0x99BEA0 | `uEffectVFR::moveParticleMoveVel` | type 1/2 shared lighter path (from `moveParticleMoveParam`). |
| 0x995CF0 | `uEffectVFR::move_particle_move` | full per-particle mMoveType dispatcher (splits 1/2). |
| 0x996160 / 0x996760 | `moveParticleMoveAdd` / `moveParticleMoveMul` | type 1 / 2 per-frame integrators. |
| 0x972F00 / 0x973460 | `initParticleMoveAdd` / `initParticleMoveMul` | type 1/2 spawn init. |
| 0x9739D0 | `initParticleMovePathStrip` + integrator 0x975440 | type 3. |
| 0x974040 | `initParticleMovePathChain` + integrator 0x975BA0 | type 4. |
| 0x974560 | `initParticleMovePathKeyframe` + integrator 0x977070 | type 5. |
| 0x974A50 | `initParticleMovePathLine` + integrator 0x977240 | type 6. |
| 0x996D60 / 0x9974B0 / 0x997BF0 / 0x998490 | `moveParticleMovePath{Strip,Chain,Keyframe,Line}` | per-frame path move subs. |

## Open / reader-unconfirmed
- **+0x14 (`mForceScalar`)**: = Mul rate for type 2 (confirmed). Path-type meaning (drag vs other) is still writer-confirmed only; the move-side path subs
  (`moveParticleMovePath*`) would pin it positively. Disproportionate to read 5 more subs for one slot — left flagged.
- ~~bit2 of `MoveCommon.mMoveRno`~~: resolved, collision radius growth (see above).


---

## On-disk move param (`rEffectList::EFL_MOVE_*`, record slot 3) — mapped 2026-10-05

This is the file-side descriptor (`Generator.mpMoveParam` @+0xBC), distinct from the per-particle work blocks above.
The IDB already had `MOVE_COMMON`/`MOVE_BASE`/`MOVE_PATH_COMMON`/`MOVE_PATH_CHAIN`, imported from SE type data. I swept
every read in the move functions and checked each field against DX9 code: the inits and per-frame moves of all 7 types,
the path integrators, `setupMoveParamCommon`, `moveParticlePosCollision`, `create_move_resources`, `AllocMemory`, and
the chain init/move. I declared the missing types, converted the 16-bit bitfields to plain members (so Hex-Rays names
them), and retyped each init's param local. The init decompiles now show field names only, with no raw-offset
leftovers.

**`EFL_MOVE_COMMON` (0x10):**
- 0x00 `MoveOptionFlag` u32 (every init reads it)
- 0x04 `ForceType` u8 (Mul reads the byte)
- 0x05 `RotAxisOrder` u8 (SE nibbles RotAxisType / RotOrder)
- 0x06 **`CollParamOffset`** u16 → collision block
- 0x08 `ForceRate` `MtRangeF` → `MoveCommon.mForceRate` (`setupMoveParamCommon`)

**`EFL_MOVE_BASE` (0x40):**

| Off | Field | Read by |
|---|---|---|
| 0x10 | `Rot` `MtRangeF[3]` | all types |
| 0x28 | `Speed` `MtRangeF` | Add, Strip, Chain, Line |
| 0x30 | `Gravity` `MtRangeF` | Add init, PathLine move |
| 0x38 / 0x3A / 0x3C | `Keyframe{Rot,Speed,FallSpeed}ParamOffset` u16 | self-relative keyframe blocks |

**Per-type tails:**

| Move type | DX9 type (size) | Tail | Evidence |
|---|---|---|---|
| 0 None | (common only) | no param reads beyond the common header | `initParticleMoveNone` |
| 1 Add | `EFL_MOVE_ADD` (0x48) | `Acceleration` `MtRangeF` @0x40 | init `s+rand*r`; move: `speed += accel` |
| 2 Mul | `EFL_MOVE_MUL` (0x48) | `SpeedCoef` `MtRangeF` @0x40 | init `addss [+40h] / mulss [+44h]` → work +0x14 rate; move: `speed *= rate` |
| 3–6 path | `EFL_MOVE_PATH_COMMON` (0x70) | `ReleaseType` u8 @0x40, `OptionFlag` u8 @0x41, `KeyframeReleaseFrameParamOffset` u16 @0x42, `ReleaseFrame` `MtRangeU16` @0x44 (base + `rand % (range+1)`), `Acceleration` @0x48 | all path inits |
| 3 PathStrip | `EFL_MOVE_PATH_STRIP` (0xC0) | `Distance` @0x70, `PathStripType` u8 @0x78 (interp mode), `PathStripFlag` u8 @0x79 (0x08, 0x40), `PathStripPartsNo` u16 @0x7A, `PathCurveDivideNum` @0x7C, `PathStripPath` char[64] @0x80 (`.efs`) | init, `calcParticleMovePathStripPos`, `calcPathStripLength`, `create_move_resources` |
| 4 PathChain | `EFL_MOVE_PATH_CHAIN` (0x110) | `Distance` @0x70, `ChainPosNum` u8 @0x78 (`AllocMemory` sizes the work as 48×N), `EFL_PARAM_CHAIN` @0x80 (reads to 0x100) | init, `initPathChain`, `movePathChain` |
| 5 PathKeyframe | `EFL_MOVE_PATH_KEYFRAME` (0x74) | `KeyframeOfsParamOffset` u32 @0x70 (position-offset keyframe block) | init, `moveParticleMovePathKeyframe`, `AllocMemory` |
| 6 PathLine | `EFL_MOVE_PATH_LINE` (0x7C) | `Distance` @0x70, `PathLength` f32 @0x78 (distance clamp) | init, `calcParticleMovePathLinePos` |

DX9 sizes stop at the last field DX9 reads. SE's types continue further: Add/Mul 0x50 (`AlwaysCorrectReleaseFrame`),
Strip 0xD0 (`ReachCurve`, `ReachFrame`), Keyframe/Line 0x80. No DX9 readers were found for those, so they're
unconfirmed. SE also has `EFL_MOVE_SPIN` and `EFL_MOVE_CUSTOM`, which DX9 lacks (DX9 has only types 0–6).

**`EFL_MOVE_PATH_COMMON` 0x50–0x6F** (`Path3DScaleX/Y/Z`, `PathLengthScale`): **no DX9 param reader found**. Every
+0x50..+0x6F access in the path functions is on the particle work block. These keep their SE names, flagged
unconfirmed.

**Collision block `EFL_PARAM_COLLISION` (DX9 ≥0xB0):** reached as `param + CollParamOffset` via
`uEffectVFR::get_coll_param` (0x960650, ex-`sub_960650`). `Generator::AllocMemory` stores it in
**`Generator.mpCollParam` (+0xD4)**. Its layout diverges from SE's 0x30-byte `EFL_PARAM_COLL`: DX9 stores the effect
paths inline, the same pattern as the generator sidecars.

| Off | Field | Evidence |
|---|---|---|
| 0x01 | `CollFlag` | tested in `moveParticlePosCollision` |
| 0x02 | `CollCancelFrame` | → `MoveCommon.mCollFrameTimer` |
| 0x04 | `CollRadiusAdd` | per-frame radius growth → status bit 2 |
| 0x08 | `CollRadius` `MtRangeF` | s = spawn radius, s+r = clamp |
| 0x10 / 0x18 | `Bounce/FinishEffectParam[2]` | passed when that effect is present |
| 0x20 / 0x21 | `Bounce/FinishEffectMode` | nibble pairs |
| 0x22 / 0x23 | callback flags | owner vtbl +152 / +156 |
| 0x24 / 0x26 | `BounceNumBase` / `BounceNumRange` | count = base + `rand % (range+1)` |
| 0x28 | `BounceRate` `MtRangeF` | |
| 0x30 / 0x70 | `BounceEffectPath` / `FinishEffectPath` char[64] | → `ResourceInfo.mpBounceEffect` / `mpFinishEffect` |

The names at 0x00–0x0F are from SE. Their DX9 behaviour matches.

**Open questions chased (2026-10-05, second pass).** I swept 116 effect functions that load `mpMoveParam` /
`mpCollParam`, and imported SE's effect enums (49, from the SE PDB) into the DX9 IDB. I applied an enum to a field
**only where DX9's own masks and compares agree with it**:

| Field | Enum applied | DX9 evidence |
|---|---|---|
| `EFL_MOVE_COMMON.MoveOptionFlag` | `MOVE_OPTION_FLAG` | `&2` GRAVITY_NO_SCALE (Add/Mul/PathLine), `&4` HIGH_ACCRACY (`sub_967850` → `Gen.mFlags \|= 0x4000`), `&8` ALWAYS_CORRECT (Add) |
| `EFL_MOVE_COMMON.ForceType` | `FORCE_TYPE` (u8) | Mul tests `& 0xF` |
| `EFL_MOVE_PATH_COMMON.ReleaseType` | `PATH_RELEASE_TYPE` (u8) | PathLine branches `==1` WORK_SPEED / `==2` PATH_SPEED (now renders symbolically) |
| `EFL_MOVE_PATH_COMMON.OptionFlag` | `PATH_OPTION_FLAG` (u8) | `&1` RELEASE_PATH_END (with PTCL PATH_END 0x400), `&2` KILL_PATH_END (returns the PTCL kill bit), `&4` KEEP_HOLD_OFF_PATH_END |
| `EFL_MOVE_PATH_STRIP.PathStripType` | `rEffectStrip::STRIP_TYPE` (u8) | interpolation switch 1 LINEAR / 2 HERMITE / 3 SPLINE |
| `EFL_MOVE_PATH_STRIP.PathStripFlag` | `rEffectStrip::STRIP_FLAG` (u8) | `0x08` PATH_LOOP (wrap vs clamp), `0x40` SKINING |
| `EFL_PARAM_COLLISION.CollType` | `COLL_TYPE` (u8) | `!=0` / `==1` MOVE_STOP / `==2` COLL_STOP (0 = KILL); renders symbolically |
| `EFL_PARAM_COLLISION.CollFlag` | `COLL_FLAG` (u8) | bit0 FIN_ANIM_STOP |
| `EFL_GENERATOR.mVibReqType` | `VIB_REQ_TYPE` (u8) | `setRequest` switch 0–3 = NONE / DEFAULT / VIEWPORT_POS / VIEWPORT_PARENT |
| `EFL_GENERATOR.VibOptionFlag` | `VIB_OPTION_FLAG` (u16) | bit0 SYNCHRO_STOP (`finish_requests`) |
| `EFL_PARTICLE_COMMON.ParticleOptionFlag` | `PARTICLE_OPTION_FLAG` | 0x80000 EDGE_ALPHA_OFF (PrimModel border alpha) |
| `EFL_PARTICLE_COMMON.CullingFlag` | `CULLING_FLAG` (u16) | bit0 ON → culling draw variant |

Further cross-confirmations (enums imported, not applied to a field):
- `cParticle::PTCL_FLAG`: CALC_DIR\|CALC_WORLD_DIR = the `& 0x180` in the move inits, PATH_END = 0x400, CONST_UPDATE = the `\| 0x800`.
- `cParticle::PTCL_MOVE_STATUS` = the work-block `mMoveStatus` bits.
- `rEffectAnim::ANIM_FLAG` = the PrimModel node `mAnimFlag` bits.
- `ResourceInfo::STATUS` = every loader failure bit.
- `cParticleManager::MAN_RNO_TBL` = the generator state nibble.
- `rEffectList::GENERATOR_TYPE` = `mGeneratorType` 0/1/2.

**Not applied, SE disagrees:** `SeOptionFlag` bit0. DX9 uses it as "stop the SE on finish", but SE names bit0 FOLLOW_OFF.

**Other results:**
- **`EFL_PARAM_CHAIN` is verified.** Its header matches SE exactly (`OptionFlag` u16, `PreUpdateLoopNum`, RotAxis/Order nibbles @4, BlendRot nibbles @5, `HoldPosNum` @6; DX9 `initChain` reads the same nibbles). The range fields Length…ForceVertexAttenuateRate are all read as `s+rand*r` in `initChain`. Its keyframe offsets @0x80–0x8C are **dwords** in DX9 (SE packs two u16 at 0x84), which is a real build difference.
- **No DX9 reader exists anywhere** for: `EFL_MOVE_PATH_COMMON` 0x50–0x6F (`Path3DScale*`, `PathLengthScale`); anything past the DX9 tail ends (SE's `AlwaysCorrectReleaseFrame`, `ReachCurve`/`ReachFrame`, and the padding); collision 0x03 and 0x25. These are treated as **unused in DX9**: the parser keeps them as raw bytes.
- **Collision +0x20/+0x21 nibble pairs:** for each event, high nibble → the attach-mode argument of `sub_969990` (via the child-effect spawner `sub_99A7F0` → `sub_96A210`), low nibble → the spawned child's `uEffectVFR+0x10C` byte. This is the same pair layout as `EFL_GENERATOR+0x1C` uses for unit generators. It's likely SE's `RELATION_TYPE` / attach-axis pair, but **unverified**: DX9 compares the byte to 6, which doesn't map cleanly.

**Remaining open:**
- The meaning of the nibble pair above.
- `FORCE_TYPE` custom values (2+) per game.
- `EFL_PARAM_CHAIN.OptionFlag` bit usage (DX9 reads it only as a dword, so `CHAIN_OPTION_FLAG` isn't applied).
