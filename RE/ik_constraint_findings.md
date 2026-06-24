# IK & Constraint System — `cCnsIK` / `cLegIkCtrl`

Analysis of the inverse-kinematics constraint subsystem in the DX9 target. This is a
secondary skeletal solver that runs **after** the base motion pose is evaluated
(`uModel::updateMotionParam`, see `motion_runtime_findings.md`) and modifies specific
joints — in practice, **terrain-adaptive foot/leg IK** for the player.

## Class hierarchy

```
cConstraint (32B base)
 └─ cCnsIK (464B)          generic analytic 2-bone IK primitive
      embedded in:
        uCnsIK (500B)      unit wrapper (cUnit + uActor* + cCnsIK @ +0x24)
        cLegIkCtrl         player foot-IK controller (cCnsIK @ +0x20)
sibling constraints sharing the base: cCnsChain, cCnsDirPos, cCnsMatrix, cCnsRandom, cCnsOffset
```

### `cConstraint` (32B) — constraint base
| Off | Field | Role |
|-----|-------|------|
| +0x00 | `vtable` | |
| +0x04 | `mBlendWeight` | current blend amount (ramped toward `mBlend`) |
| +0x08 | `mRno` | |
| +0x0C | `mBlendVel` | ramp speed per frame |
| +0x10 | `mBlend` | target blend amount |
| +0x14 | `mRate` | rate scale |
| +0x18 | `mIgnoreRate` | force `mRate`=1 |
| +0x19 | `mEnable` | |
| +0x1C | `mID` | |

### `cCnsIK` (464B) — 2-bone IK constraint
| Off | Field | Role |
|-----|-------|------|
| +0x00 | `cConstraint` base | |
| +0x20 | `mMat0` | bone0 world matrix (4×4) |
| +0x60 | `mMat1` | bone1 world matrix |
| +0xA0 | `mMatEff` | effector world matrix |
| +0xE0 | `mLMat0` | bone0 local matrix |
| +0x120 | `mLMat1` | bone1 local matrix |
| +0x160 | `mNeedIK` (byte) | run solve this frame |
| +0x161 | `mLastIKOn` | previous-frame state (for blend) |
| +0x164 | `mBone0` | upper-limb joint index (thigh) |
| +0x168 | `mBone1` | lower-limb joint index (shin) |
| +0x16C | `mEff` | effector joint index (foot/ankle) |
| +0x170 | `mDir` | aim/pole direction joint |
| +0x174 | `mUp` | up-vector joint (knee pole) |
| +0x178 | `mKeepRot` | preserve effector rotation |
| +0x180 | `mLocalOffset` | effector local offset |
| +0x190 | `mWorldOffset` | effector world offset (target) |
| +0x1A0 | `mFloorLevel` | floor height clamp |
| +0x1A4 | `mLimit` | max reach/stretch limit |
| +0x1B0 | `mPos` | IK target position |
| +0x1C0 | `mCnsPos` (byte) | constrain-position flag |
| +0x1C4 | `mpReportActor` | actor notified on contact |

## How the solve works

**It is an analytic 2-bone IK, computed with vector math (dot/cross + `sqrt`), NOT inverse
trigonometry.** Confirmed: no function in the constraint code region (0x42B000–0x452000)
calls `acos`/`asin`; the apply path uses only `dmc4_sqrt` and normalization. The elbow/knee
bend is derived geometrically (law-of-cosines via squared lengths), and the **target is
supplied as a world position by the controller** — the constraint positions the chain to
reach it.

Key functions:

| Addr | Name | Role |
|------|------|------|
| 0x43B2C0 | `cCnsIK::ctor` | init: `mBone0..mUp` indices, Identity matrices, `mFloorLevel`/`mLimit` |
| 0x43B020 | `cCnsIK::createProperty` | registers 9 editable `MtProperty` fields |
| 0x43AFA0 | `cCnsIK::getDTI` | returns `&cCnsIK::DTI` (0xE56EA8) |
| 0x447780 | `cConstraint::move` | **blend-weight ramp** — eases `mBlendWeight`→`mBlend` at `mBlendVel*mRate`/frame |
| 0x4477E0 | `cConstraint::composeWorldMatrix` | shared FK matrix builder (parent×local→world); used by all `cCns*` |

DTI: `cCnsIK::DTI` @ 0xE56EA8, parent `cConstraint::DTI` @ 0xE56F48, alloc size 0x1D0 (464).
Instance vtable @ 0xB99150.

## Invocation path — player foot IK (`cLegIkCtrl`)

```
uPlayer::moveMotion/tick
 └─ uPlayer::updateLegIk           0x7AB9B0   drives BOTH feet
     ├─ left  foot ctrl @ uPlayer+6064
     └─ right foot ctrl @ uPlayer+6592
        each: enable = uActor::getNumberFromMotSeq(...)  ← per-animation toggle via the
              motion's sequence-event track (the mSequence bits emitted by uModel::updateFrame)
        each: cLegIkCtrl::update   0x7B0B50   foot-planting raycast
              ├─ build vertical ray: footY+30.0  →  footY-14.0
              ├─ sCollision::setCallback(collNarrow_LineSeg, collBounds_LineSeg, collStore_LineInfo)
              ├─ sCollision::findIntersection   ← raycast floor/terrain
              ├─ on hit & |Δheight|>1.0: target = hitPoint + 12.0 (foot offset); flag adjusted
              │  else: plant flat at original height
              └─ write target into cCnsIK (ctrl+432/436/440) + apply with blend 0.1
                 → cCnsIK solves the 2-bone leg to reach the target
```

`cLegIkCtrl` ctor @ 0x4FC710; `cLegIkCtrl::update` @ 0x7B0B50; DTI init
`uPlayer::cLegIkCtrl::DTI::init` @ 0xB75370.

So the design splits cleanly:
- **`cCnsIK`** = reusable analytic 2-bone IK primitive (any limb), blended via `mBlendWeight`.
- **`cLegIkCtrl`** = the foot-IK *controller* that raycasts the ground each frame and feeds
  a world-space target. Enabled per-animation through motion sequence events, so feet only
  plant during the animations that ask for it (idle/walk/landing, not e.g. air combos).

## Reproducing this rig in Blender

This system maps onto a standard Blender foot-IK rig. The split is the same: a generic
2-bone IK constraint (`cCnsIK`) plus a controller that ray-casts the ground and feeds a
world-space target (`cLegIkCtrl`).

### Component mapping
| DMC4 component | Blender equivalent |
|---|---|
| `cCnsIK` 2-bone solve (`mBone0`→`mBone1`→`mEff`) | **IK bone constraint** on the foot, Chain Length 2 |
| `mDir` / `mUp` (knee bend plane) | **Pole Target** + Pole Angle |
| `cLegIkCtrl::update` floor raycast (footY+30 → footY−14) | **Shrinkwrap (Project, −Z)** on the IK target, or a raycast driver |
| `+12.0` foot offset above hit point | Shrinkwrap **Distance** (foot rests above surface, no clipping) |
| `mFloorLevel` clamp | **Limit Location** Min Z on the target |
| `cConstraint::mBlendWeight` ramp (blend 0.1) | IK constraint **Influence**, keyframed/driven |
| `getNumberFromMotSeq` per-animation enable | Influence driven by an action/NLA channel |
| `mKeepRot` (preserve effector rotation) | **Copy Rotation** from ground normal, or IK tip rotation off |

### Step-by-step
1. **Bone chain** (Edit Mode) — build a clean 2-bone chain ending at the foot, matching
   `mBone0`/`mBone1`/`mEff`:
   `thigh (mBone0) → shin (mBone1) → foot (mEff)`. Connect `shin` to `thigh`, and give the
   knee a slight forward pre-bend in rest pose (seeds the solve direction, the role
   `mDir`/`mUp` play in the game).
2. **Control bones** (not in the deform chain): `foot_IK` (the target, at the ankle) and
   `knee_pole` (placed in front of the knee).
3. **IK constraint** on the **foot bone** (chain tip = `mEff`): *Bone Constraint → Inverse
   Kinematics*. Target = Armature/`foot_IK`; **Chain Length: 2** (this is what makes it a
   2-bone solve like `cCnsIK`, not a full-leg CCD); Pole Target = Armature/`knee_pole`,
   tune **Pole Angle** so the knee tracks forward. With Chain Length 2 + a pole, Blender's
   solver converges to the same analytic 2-bone pose found in `cCnsIK` (target-driven, no
   inverse-trig).
4. **Floor raycast** (`cLegIkCtrl::update`) — on `foot_IK` (or an empty it copies), add
   *Bone Constraint → Shrinkwrap*: Target = ground mesh; **Wrap Method: Project**, **Axis:
   −Z** (straight down, the game's vertical ray); **Distance ≈ 12.0** (the foot offset);
   optionally **Limit Surface** to cap the cast range (the game's +30/−14 window). The foot
   now snaps to whatever ground is under it.
5. **Floor clamp** (`mFloorLevel`) — add *Limit Location* on `foot_IK`, **Min Z = floor
   height**, so the foot can't be driven below the ground plane if the shrinkwrap misses.
6. **Blend on/off** (`mBlendWeight` ramp) — keyframe the IK constraint's **Influence** 0→1
   over a few frames (the game's `mBlendVel*mRate`, it passed 0.1), or drive Influence from
   a per-action custom property — the analog of `getNumberFromMotSeq` gating foot-plant only
   during idle/walk/landing, not air combos.

### Layering nuance
The game evaluates **base motion pose → IK overrides specific joints → blend in**. In
Blender: keep the imported animation on the FK leg bones, let the IK constraint override on
top, and use **Influence** for the mix. To preserve foot orientation on contact (the game's
`mKeepRot`), add a **Copy Rotation** from the ground normal rather than letting IK rotate
the tip.

### Knee / pole-vector setup — what the binary actually says
A deeper pass clarified the apply path, which changes the knee-setup advice:

- `cCnsIK` has **no unique apply/solve virtual**. Its vtable (0xB99150) shares
  `cConstraint::move` (blend ramp, slot +0x30 → 0x447780) and
  `cConstraint::composeWorldMatrix` (slot +0x34 → 0x4477E0) with every sibling constraint
  (`cCnsChain`, `cCnsDirPos`, `cCnsMatrix`, …).
- `composeWorldMatrix` (0x4477E0) was disassembled in full: it is a **per-joint FK matrix
  build** — load parent world matrix, expand the joint's local quaternion to 3×3,
  **normalize the 3 basis axes** (three `sqrt`+`div` blocks, epsilon `dword_B9A284`), compose
  with the parent, write `Joint.mWmat`. It does **not** read `mBone0`/`mBone1`/`mDir`/`mUp`.

So the 2-bone reach and the knee-plane selection from `mDir`/`mUp` happen in a **separate
constraint-resolve step that has not yet been isolated** (offset-based scans collide with
other classes on the +0x164/+0x170 displacements). The bind-pose orientations of the `mDir`
and `mUp` joints define the bend plane — i.e. the knee direction is **data-driven from the
skeleton**, not a runtime pole-vector cross product computed in the apply.

Practical consequence for the Blender rig: place `knee_pole` along the **bind-pose forward
direction of the `mDir` joint** (the pre-bent knee's facing), with `mUp` as the secondary
axis. That reproduces the data-driven bend plane. Exact instruction-level confirmation of how
`mDir`/`mUp` are consumed is still an open thread.

### Caveats
- Blender's default solver is iterative; Chain Length 2 + pole makes it converge to the same
  analytic pose, so it matches visually but isn't literally the same closed-form path.
- The 2-bone structure, the target-feeding mechanism (raycast → world position → solve), and
  the FK finalize (`composeWorldMatrix`) are confirmed from the binary. The specific function
  that consumes `mDir`/`mUp` to orient the knee is **not yet pinned to instructions**.

## Open threads
- The constraint-resolve function that performs the 2-bone reach and consumes `mDir`/`mUp`
  for the knee plane is not yet isolated (it is NOT `composeWorldMatrix`, which only finalizes
  the FK matrix; and `cCnsIK` has no unique apply virtual). Likely invoked from the model's
  per-frame constraint pass over joints with `mpConstraint` set. Finding it requires tracing
  `cCnsIK::mNeedIK`/`mMatEff` reads without colliding on shared offsets — a typed-pointer xref
  or a breakpoint-style data-flow trace rather than raw displacement scanning.
- Sibling constraints (`cCnsChain` = hair/cloth chain dynamics, `cCnsDirPos`, `cCnsMatrix`)
  reuse `cConstraint::composeWorldMatrix` but have their own apply logic — not analyzed.
- `uCnsIK` (the standalone unit wrapper) vs `cLegIkCtrl` (player-embedded) — whether enemies
  use `uCnsIK` for their own IK.
