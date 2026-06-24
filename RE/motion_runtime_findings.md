# uModel 3D Animation Runtime — Core Evaluation Pipeline

Analysis of the per-frame skeletal animation evaluator in `uModel` (DX9 target,
`DevilMayCry4_DX9.exe`). Focus: the runtime that turns loaded LMT motion data
(`rMotionList`) into the final per-joint local pose written to `uModel::Joint`.

## Data layout (already defined in IDB)

### `uModel::Joint` (144B, array `mpJoint`, count `mJointNum`)
Skeletal node — both static hierarchy and the **decoded output pose**.

| Off  | Field           | Role |
|------|-----------------|------|
| +0x04 | `mAttr` (byte)  | bit0 = joint enabled (gates blend) |
| +0x05 | `mParentIndex`  | parent joint idx; 255 = root/end of chain |
| +0x06 | `mType` (byte)  | constraint/blend mode — drives the `switch` in updateMotionParam |
| +0x08 | `mSymmetryIndex`| mirror-pair joint (255 = none) |
| +0x0C | `mpConstraint`  | constraint object ptr (IK/dir/aim) |
| +0x20 | `mQuat`         | **decoded local rotation** (output) |
| +0x30 | `mScale`        | **decoded local scale** (output) |
| +0x40 | `mTrans`        | **decoded local translation** (output) |
| +0x50 | `mWmat`         | final world matrix (built downstream from the above) |

### `uModel::Motion` (224B, `MotionArray[8]`, active count `mBlendNum`)
One **blend layer / playback slot**. Up to 8 simultaneously blended motions.

| Off   | Field         | Notes |
|-------|---------------|-------|
| +0x04 | `mMotionNo`   | 0xFFFF = inactive slot |
| +0x08 | `mState`      | bit1 (`&2`) = needs track rebind → triggers setupMotionParam |
| +0x0A | `mAttr`       | `MOT_ATTR` flags: `&0x24`=loop, `&0x100`=mirrored, `&0x800`=integer-frame, `&0x200`/`&0x400` root-motion |
| +0x18 | `mFrame`      | current playback frame (float) |
| +0x1C | `mFrameMax`   | clip length |
| +0x20 | `mLoopFrame`  | loop restart point |
| +0x60 | `mNullQuat`   | sampled **root quaternion** (pass 1 output) |
| +0x90 | `mNullTrans`  | sampled **root translation** (pass 1 output) |
| +0xA0 | `mTransParam` / +0xB0 `mQuatParam` | `MPARAM_WORK` track cursors |
| +0xD8 | `mJoint`      | `MJOINT_WORK*` — per-joint track-cursor buffer (mJointNum × 96B) |

### `uModel::MPARAM_WORK` (16B) — per-track playback cursor
`pparam`(TrackHeader*) · `cur_frame` · `pcur_param`(keyframe cursor) · `weight`

### `uModel::MJOINT_WORK` (96B) — per-joint, per-slot decode scratch
`mQuatParam`(16) · `mTransParam`(16) · `mScaleParam`(16) · `mHQuat`(16) · `mHTrans`(16) · `mHScale`(16)

### `rMotionList::TrackHeader` (32B) — one bone track in the LMT file
`BufferType`(encoding class, byte0) · `TrackType`(channel: 0=trans 1=rot 2=scale 3/4=root) ·
`BoneType` · `BoneIndex` · `Weight` · `BufferSize` · `BufferOfs` · `Reference`(vec4 default)

## Per-frame call graph

```
uModel::moveMotion              0x9f89d0  per-frame driver (guards mpRModel)
 ├─ uModel::setupMotionParam    0x9f9060  (re)bind tracks for slots with mState&2
 │    ├─ calcMotionVector / calcMotionQuaternion   (pre-sample root motion)
 │    └─ calcSymmetry
 ├─ uModel::updateMotionParam   0x9fa1e0  BLEND ENGINE  ← main analysis
 │    ├─ calcMotionVector       0xae0050  translation/scale track interp
 │    ├─ calcMotionQuaternion   0xae0400  rotation track decode (codec: see quat-format notes)
 │    └─ calcSymmetry           0x9f9c80  mirror transform
 └─ uModel::updateFrame         0x9fce60  advance mFrame, loop/end handling
```

## `uModel::moveMotion` (0x9f89d0)
Top-level driver. For each blend slot flagged `mState&2` (rebind needed): zero the
`MJOINT_WORK` buffer, reset accumulators to Identity quat / Zero trans, call
setupMotionParam. The large unrolled loops copy `mpJoint[].mQuat/mTrans/mScale` into
the per-slot joint-work buffer (4-wide unroll + scalar remainder). Adds `mWaistAdjust`
to the waist joint. Then runs updateMotionParam (blend) and updateFrame (advance).

## `uModel::setupMotionParam` (0x9f9060)
Runs on motion change. Resolves `motionNo` → `mpMotionListArr[(no>>8)&0xF]` →
`MOTION_INFO[no&0xFF]`, sets `mFrameMax`/`mLoopFrame` and the keyframe-stream pointers.
Walks each `TrackHeader` (stride 32) and binds it via `switch(TrackType)` to the right
`MJOINT_WORK` channel (quat/trans/scale at +0/+16/+32) for the remapped bone. A second
`switch` on a per-bone compute mode tags symmetry/constraint joints. Tail handles
root-motion extraction: pre-samples the root track and computes a per-frame delta
quaternion via SLERP (the `acos`/`sin` block).

## `uModel::calcMotionVector` (0xae0050) — translation/scale track interpolator
`(base@eax, MPARAM_WORK*@ecx, out_vec3, frame, frame_max)`. If `pparam==0` → emit base
vec unchanged. Else dispatch on `BufferType-1`: type0→Zero, type1→constant vec3,
type8→full keyframe stream (walk cursor to bracket frame, compute `t`, SIMD lerp
`(next-cur)*t+cur`). `frame_max` gates loop-wrap (reads loop-start sample from the
TrackHeader instead of the next keyframe at clip end).

## `uModel::updateMotionParam` (0x9fa1e0) — **the blend engine**  ★
161 basic blocks, cyclomatic complexity 74. Two passes over `MotionArray[0..mBlendNum-1]`.

### Pass 1 — base/root sample
Finds the first active slot, clamps its `mFrame` against `mFrameMax`
(`mAttr&0x24`=loop wrap, else clamp; `mAttr&0x800`=floor to integer frame via the
`0x4B000000` float→int trick). Samples the slot's **root translation** track →
`Motion.mNullTrans (+0x90)` and **root quaternion** track → `Motion.mNullQuat (+0x60)`.
Applies `calcSymmetry` when `mAttr&0x100` (mirrored motion).

### Pass 2 — per-joint blend accumulate
For each active slot, iterates every joint (`mpJoint`, stride 144) with its matching
`MJOINT_WORK` (stride 96):

- **Joint gate:** `Joint.mAttr & 1` (disabled joints skipped).
- **Quaternion source:**
  - If the joint has a quat keyframe track → `calcMotionQuaternion`.
  - If `*pparam == 0` (no quat track, constraint-driven joint) → **reconstruct the
    quaternion from the joint's matrix** via Shepperd's method:
    `w = sqrt(trace+1)*0.5`, off-diagonal differences `(m6-m9, m8-m2, m1-m4) * (0.5/w)`,
    with a `trace<=0` branch that selects the **largest diagonal element** for numerical
    stability (the `n2` index selection picking axis 0/1/2).
- **Translation/scale:** `calcMotionVector` for each (or fall back to the joint's
  reference value when the track pointer is null).
- Decoded pose is staged into a large stack scratch buffer (`frame[1]` = quaternion
  array, `frame[257]` = translation array), indexed by per-joint stride.
- **`switch(Joint.mType @ +6)` — constraint joint handling:**
  - cases `5,6,0xF-0x12,0x15,0x16` → **parent-matrix forward kinematics**: transform the
    local offset by the parent's world matrix (the 3×3 `v196..v198` multiply), walking the
    parent chain until `mParentIndex == 255`.
  - case `0x14` → **aim/direction constraint**: build target vector, normalize it
    (`dmc4_sqrt` of squared length then `1/len`; epsilon guard `1.19e-7`), store into the
    joint-work direction slot.
  - default → straight blended pose.

Final per-joint blended pose lands in `mpJoint[].mQuat/.mTrans/.mScale`, consumed
downstream to build each `Joint.mWmat`.

## `uModel::updateFrame` (0x9fce60) — frame advance + sequence events
Per blend slot: decays the interpolation counter (`mInterCount` via `MtEaseCurve::easeIn`
→ `mInterRate`), advances `mFrame += mSpeed*dt` unless `A_STOP`, and handles end-of-clip:
- `A_LOOP_OFF` set → clamp `mFrame` to `mFrameMax-1`, raise `mState|1` (ended).
- `A_LOOP_OFF` clear → wrap by `(mFrameMax - mLoopFrame)` and **accumulate the per-loop
  root-motion delta** (the quaternion-multiply + translation-add block at +0x40/+0x70),
  so looping motions keep travelling. Handles both forward (`mSpeed>0`) and reverse play.
- `mState` bits set here: bit0 = reached end this tick, bit2 = looped this tick
  (consumed by `uActor::isMotionEnd`/`isMotionEndAll`).
Tail walks the motion's two sequence-event tables (`mpSeqInfo[0/1]`) and OR-accumulates
the events crossed between `mFrame` and the next frame into `mSequence[0/1]` (skipped when
`A_STOP` or `A_LOOP_OFF`). These drive footstep/SE/attack-window triggers.

## `uModel::MOT_ATTR` (2B enum) — CONFIRMED against canonical names
The enum was already populated in the IDB with the real MT Framework `A_*` names. Every
bit was independently confirmed by its read/write sites in the functions above. The
`A_NULL_*` prefix refers to the **root ("null") bone** that carries root motion;
`FIX` = absolute override, `ADD` = additive accumulation.

| Bit    | Name                     | Confirmed behavior (site) |
|--------|--------------------------|---------------------------|
| 0x0001 | `A_NULL_TRANS_OFF`       | caller flag; disable root translation |
| 0x0002 | `A_FIRST_TRANS_ON`       | use first-frame translation as base |
| 0x0004 | `A_LOOP_OFF`             | **clamp at end, no wrap** (updateFrame); forced by setMotionEx/setupMotionParam when `MOTION_INFO` loop value < 0 |
| 0x0008 | `A_ADD_TRANS_OFF`        | caller flag; disable additive translation (setupMotionParam branch @9F9631) |
| 0x0010 | `A_STOP`                 | **freeze frame** — skip `mFrame` advance + sequence events (updateFrame @9FCF38/9FD448) |
| 0x0020 | `A_NULL_TRANS_FIX`       | **absolute root translation** — overwrite `model->mPos`, skip mScale (updateMotionParam @9FB5D6) |
| 0x0040 | `A_ENABLE_SCALE`         | **has scale track** — set on TrackType==2 (setupMotionParam @9F91D8) |
| 0x0080 | `A_NULL_ANGLE_FIX`       | **absolute root rotation** — overwrite `model->mQuat`, no accumulate (updateMotionParam @9FB651) |
| 0x0100 | `A_SYMMETRY`             | **mirrored** — triggers `calcSymmetry` (setupMotionParam, updateMotionParam, pass 1) |
| 0x0200 | `A_NULL_ONLY`            | **suppress root-rotation matrix build** (updateMotionParam @9FB81F) |
| 0x0400 | `A_PREV_TRANS_ON`        | use previous-frame translation as base |
| 0x0800 | `A_INTEGER_FRAME`        | **floor `mFrame`** before sampling (updateMotionParam @9FA30D, slot scan @9FBA1D) |
| 0x1000 | `A_ADD_ROT_OFF`          | disable additive rotation |
| 0x2000 | `A_NULL_TRANS_FIX_SCALE` | absolute root translation incl. scale |
| 0x4000 | `A_SCALE_INHERIT_OFF`    | don't inherit parent scale |
| 0x8000 | `A_NULL_SYMMETRY`        | mirror the root bone |

Caller-supplied attr immediates (1209 setMotionEx call sites): 0x0 (868, default), 0x8
(27), 0x4 (16), 0x1 (13), 0x10 (2), 0x5 (1). The high bits (0x20–0x8000) are set by the
motion data / runtime, not by gameplay callers.

## Open threads / next steps
- `calcSymmetry` (0x9f9c80) — mirror transform using `Joint.mSymmetryIndex`.
- The constraint-joint `switch(Joint.mType)` cases in updateMotionParam (dir/pos/aim FK)
  could be cross-referenced with `cCnsChain`/`cCnsIK`/`cCnsDirPos` to name each mode.
- Quaternion keyframe codec (`calcMotionQuaternion` cases 3–7, masks 0x1FFFF/0x7FFFF,
  dequant constants) — format already held externally; not re-derived here.
