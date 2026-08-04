# Line-Segment Cast (Raycast) — sCollision

The engine has no dedicated "raycast" primitive.  A ray is expressed as a
**line segment** (two world-space endpoints) and runs through the same
`ScrCollisionCore` pipeline used for sphere and capsule queries.

---

## Entry points

| Function | Address | Notes |
|----------|---------|-------|
| `sDevil4Collision::findIntersection` | `0x95B320` | Thin wrapper — fills the callback struct, then tail-calls `ScrCollisionCore`. Takes a pre-filled `sCollision::Param*` in `eax`; caller must still do all `Param` setup. |
| `sCollision::ScrCollisionCore` | `0x95CF20` | The real dispatch — call directly if you want full control (most game code does). |
| `cUtil::checkGround` | `0x45E790` | Canonical two-pass ground probe: sweeps down, then up from result to bracket the ground plane. Good reference implementation. |

---

## Callback triples

Install one of these sets via `sCollision::ScrCollisionBeforeFunc` (`0x940470`)
before calling `ScrCollisionCore`.

| Narrowphase | Broadphase | Store | Use-case |
|-------------|------------|-------|----------|
| `collNarrow_LineSeg` `0x955970` | `collBounds_LineSeg` `0x9532C0` | `collStore_LineInfo` `0x955940` | Standard intersection — accumulates up to `correctionNum` hits. Used by `findIntersection`, camera, player ground checks, weapons, etc. |
| `collNarrow_FootprintLine` `0x9486C0` | `collBounds_LineSegA` `0x948980` | *(none — result baked into narrowphase)* | Footprint / decal ground probe. `uModel::checkFootPrintCollision`, `cFootprintCtrl::update`. |
| `collNarrow_LineFirstHit` `0x9498C0` | `collBounds_LineSegB` `0x949A10` | *(none)* | Early-exit on first geometry contact. `sub_94B660`. |

The `A` / `B` suffixes on `collBounds` are alternate broadphase AABB derivations
from the segment endpoints — not different shapes.

---

## Step-by-step: minimal single line-cast

### 1. Fill `sCollision::Param` on the stack

```c
sCollision::Param q;
q.type             = 127;       // 0x7F — test all SBC types
q.hitCallback      = nullptr;   // no per-hit callback wanted
q.hitCallback_this = nullptr;
q.hitCallback_data = nullptr;
q.handle_exclude_0 = -1;        // no handle exclusion
q.handle_exclude_1 = -1;
q._unk20           = 0;
q.correctionNum    = 10;        // max contacts to collect
q.bAdjMvRelSet     = 1;
q._flag29          = 0;
q.bAdjAntiStop     = 1;
q._flag2B          = 0;
q.capsuleFwdLimit  = FLT_MAX;   // line seg: no endpoint clamping needed
q.capsuleBwdLimit  = FLT_MAX;
q._unk34           = 0.0f;
q.partsFilter      = 0;
q.filter           = myGroupMask; // <-- the only field that varies per-caller
```

`type = 127` and `correctionNum = 10` are the values every line-segment
caller in the binary uses.  `filter` is the group mask that selects which
SBCs participate; pass the same value to `ScrCollisionBeforeFunc`.

### 2. Fill `MtLineSegment`

```c
MtLineSegment seg;
seg.p0 = worldStart;   // world-space start point
seg.p1 = worldEnd;     // world-space end point  (NOT direction + length)
```

`MtLineSegment` is two `MtVector3`s.  Direction and length are implicit in
the difference `p1 - p0`.

### 3. Install callbacks and dispatch

```c
sCollision::callback_struct_t cb;
sCollision::ScrCollisionBeforeFunc(
    &cb,
    sCollision::collNarrow_LineSeg,   // 0x955970
    sCollision::collBounds_LineSeg,   // 0x9532C0
    sCollision::collStore_LineInfo,   // 0x955940
    nullptr,
    (int)myGroupMask,
    0);

MtVector3 hitPos;
bool hit = sCollision::ScrCollisionCore(
    sDevil4Collision::mpInstance,
    &q,
    (MtMatrix*)&seg,   // line segment passed as the geometry argument
    0,                 // bothSidesFlag: 0 = one-sided, 1 = both-sided
    &hitPos,
    &cb) != 0;
```

On return:
- Nonzero return → at least one hit occurred
- `hitPos` receives the intersection point (`collStore_LineInfo` fills it)

---

## Using `sDevil4Collision::findIntersection` instead

`findIntersection` saves you the three `ScrCollisionBeforeFunc` lines:

```c
// eax = &q  (usercall convention)
sDevil4Collision::findIntersection(&q, sDevil4Collision::mpInstance,
                                   &seg.p0, /*bothSidesFlag=*/0, &hitPos);
```

It installs `collNarrow_LineSeg` / `collBounds_LineSeg` / `collStore_LineInfo`
internally and tail-calls `ScrCollisionCore`.  You must still fill `q`
yourself — `findIntersection` does not default any `Param` fields.

---

## `cUtil::checkGround` — two-pass ground probe

`checkGround` (`0x45E790`) runs the query **twice**:

1. Sweep **down** from the probe origin by `param_3` units → finds the
   floor below.
2. Sweep **up** from the first hit by the same delta → confirms the hit is
   solid from below (avoids one-sided floor surfaces).

The second hit's Y coordinate is the authoritative ground height.  For a
simple "where does this segment hit?" one call to `ScrCollisionCore` is
sufficient.

---

## Notes

- `bothSidesFlag = 0` is used by every caller except explicit two-sided
  checks.  Set to 1 only when geometry may be entered from either side
  (e.g. portals, thin walls).
- `partsFilter = 0` includes all parts.  Non-zero values restrict to
  specific material/part types (same field forwarded to `ContactDefine.mPartsFilter`).
- There is no "infinite ray" mode.  Clamp `p1` to a large but finite
  distance (e.g. `p0 + dir * 10000.0f`) to approximate one.
