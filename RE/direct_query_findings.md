# sCollision Direct Query — Extensive Reference

A "direct query" is any call to the sCollision geometry pipeline that bypasses
`sCollisionGame`. The caller builds a query packet, selects a callback triple, and
calls one of the `findIntersection` entry points directly. Results come back via the
callback and the `LineInfo` / result buffer.

---

## Entry Points

| Function | Address | When to use |
|----------|---------|-------------|
| `sCollision::findIntersection` | `0x95B370` | General — caller provides explicit callback struct from `setCallback` |
| `sCollision::findIntersection_LineSeg` | `0x95B320` | Convenience: auto-wires LineSeg callbacks; caller only provides query param + shape |
| `sCollision::findIntersection_BoxSweep` | `0x95CBE0` | Swept axis-aligned box; calls internal `sub_95CE50` / `sub_95CE00`, not `findIntersection` |
| `sub_94EF30` | `0x94EF30` | Multi-OBB query; calls `query_all_sbcs` directly; sorts hits by distance |

The vast majority of callers (~100) use `findIntersection` or `findIntersection_LineSeg`.
The box-sweep and OBB paths are camera-specific.

---

## How to Issue a Query — Step by Step

```cpp
// 1. Declare stack buffers
int callback_struct[24];       // callback struct (96 bytes = 64B MtMatrix + 8 fields)
sCollision::Param result;      // receives hit data

// 2. Fill the query param block
int query_block[10] = {0};
query_block[0] = 127;          // type_mask  (0x7F = all geometry types)
query_block[1] = 0x20000000;   // group_filter (which Sbc groups to test)
// query_block[2..5] = 0
query_block[6] = -1;           // handle_exclude[0] (-1 = none)
query_block[7] = -1;           // handle_exclude[1]
query_block[8] = 0;            // flags
query_block[9] = 10;           // max_results (max hits returned)

// 3. Fill the shape data (for LineSeg: two endpoints)
float shape[8];
shape[0] = pos.x; shape[1] = pos.y + 100.0f; shape[2] = pos.z;  // top
// shape[3] unused (MtVector4 padding)
shape[4] = pos.x; shape[5] = pos.y - 100.0f; shape[6] = pos.z;  // bottom

// 4. Set up the callback triple
sCollision::setCallback(
    (int)callback_struct,
    (uintptr_t)sCollision::collNarrow_LineSeg,   // narrowphase
    (uintptr_t)sCollision::collBounds_LineSeg,   // broadphase bounds
    (uintptr_t)sCollision::collStore_LineInfo,   // result commit
    0,                                            // param_4 (overwritten by findIntersection)
    group_filter,                                 // same as query_block[1]
    0);                                           // flags

// 5. Query
bool hit = sCollision::findIntersection(
    sDevil4CollisionPtr,   // global singleton ptr
    (int)query_block,      // query params
    (int)shape,            // shape endpoints
    nullptr,               // TriangleInfo (usually nullptr)
    &result,               // output Param
    (int)callback_struct); // callback struct

// 6. Read results from the Param output (5th arg)
if (hit) {
    // hit_point
    float hit_x = *(float*)((char*)&result + 96);   // result+0x60
    float hit_y = *(float*)((char*)&result + 100);  // result+0x64
    float hit_z = *(float*)((char*)&result + 104);  // result+0x68
    // surface_normal
    float nx = *(float*)((char*)&result + 80);      // result+0x50
    float ny = *(float*)((char*)&result + 84);      // result+0x54
    float nz = *(float*)((char*)&result + 88);      // result+0x58
    // distance along ray (t parameter)
    float t  = *(float*)((char*)&result + 128);     // result+0x80
}
```

Using `findIntersection_LineSeg` (steps 4 and parts of 5 collapse):
```cpp
// step 4 skipped — findIntersection_LineSeg calls setCallback internally
// reading the filter from query_block[1] automatically

bool hit = sCollision::findIntersection_LineSeg(
    (int)query_block,      // a1@eax
    sDevil4CollisionPtr,   // param_2
    (int)shape,            // param_3 = both_sides flag? (usually 0 or 1)
    nullptr,               // TriangleInfo
    &result);              // output Param
```

---

## `sCollision::setCallback` — Callback Struct Layout

Function: `0x50DFB0`

```c
sCollision::setCallback(
    int result_struct,       // output buffer to fill (≥ 88 bytes)
    uintptr_t func1_narrow,  // narrowphase test function
    uintptr_t func2_bounds,  // broadphase bounds function
    uintptr_t func3_store,   // hit-commit (store) function
    undefined4 param_4,      // ignored by setCallback; overwritten by findIntersection
    undefined4 filter,       // geometry group filter mask
    byte param_6);           // flags byte
```

**Callback struct layout (88+ bytes):**

| Offset | Size | Field | Notes |
|--------|------|-------|-------|
| +0x00 | 64 | `MtMatrix` | initialized to `MtMatrix::Identity` |
| +0x40 (64) | 4 | `func1_narrow` | narrowphase test (passed via ECX) |
| +0x44 (68) | 4 | `func2_bounds` | broadphase AABB compute |
| +0x48 (72) | 4 | `func3_store` | hit-result commit callback |
| +0x4C (76) | 4 | `result_buf_ptr` | set by `findIntersection` → points to its local `LineInfo` var |
| +0x50 (80) | 4 | `filter` | geometry group mask |
| +0x54 (84) | 1 | `flags` | byte |

`findIntersection` writes the local result buffer address into `callback_struct + 76`
immediately before the BVH traversal. All three callbacks receive this pointer;
`func3_store` commits the final hit data there.

---

## Query Param Block (`sCollision::Param`) — Layout

Two interpretations depending on how the struct is used:

### As query input (passed as arg2 to `findIntersection`)

The pointer passed is **`&param + 0x10`** — i.e., 16 bytes into the full Param struct.
Equivalently, the raw block passed as arg2 has:

| Offset from arg2 | Field | Typical value | Notes |
|-----------------|-------|---------------|-------|
| +0x00 | `type_mask` | 127 (0x7F) | bitmask of geometry kinds (see below) |
| +0x04 | `group_filter` | e.g. `0x20000000` | geometry group membership mask |
| +0x08..+0x17 | (reserved) | 0 | |
| +0x18 | `handle_exclude[0]` | −1 | sCollision handle to exclude (−1=none) |
| +0x1C | `handle_exclude[1]` | −1 | |
| +0x20 | (reserved) | 0 | |
| +0x24 | `max_results` | 10 | cap on intersection count |
| +0x28 | `flags` | 65537 / 1 / 0 | query mode flags |

From `findIntersection`, `arg2 + 0` is the type, `arg2 + 4` is the filter.
`arg2 + 24/28` are interpreted by findIntersection as float coordinates for the
per-query 2D anchor point (XZ plane origin — used in some context not fully resolved).

### As query output (5th arg to `findIntersection`)

The full `sCollision::Param` struct receives hit data at offsets +0x00..+0x0F after
the call returns. The exact output fields depend on which `collStore_*` callback was
used; see the LineInfo section below.

---

## Shape Data (arg3 to `findIntersection`)

A pointer to the shape's geometric data. Layout depends on which callback triple is used:

### LineSeg (line segment / ray)
```
float[8] shape:
  [0..2]  p0.xyz    — first endpoint (e.g. top of capsule sweep)
  [3]     padding
  [4..6]  p1.xyz    — second endpoint (e.g. bottom)
  [7]     padding
```
Used with: `collNarrow_LineSeg`, `collBounds_LineSeg`, `collStore_LineInfo`

### Sphere
```
float[4] shape:
  [0..2]  center.xyz
  [3]     radius
```
Used with: `collNarrow_SphereA/B`, `collBounds_Sphere`

### Capsule
```
float[8] shape:
  [0..2]  p0.xyz    — first cap center
  [3]     radius
  [4..6]  p1.xyz    — second cap center
  [7]     radius (same or different)
```
Used with: `collNarrow_Capsule`, `collBounds_CapsulePair`

### BoxSweep (`findIntersection_BoxSweep`)
Two points (param_3 and param_4) — the box is centered between them with
half-extents = (param_3 − param_4) × 0.5.
Used with: `collNarrow_BoxSweep`, `collBounds_BoxHalfExt`, `collStore_Qword16`

### Multi-OBB (`sub_94EF30`)
Takes a full world-space OBB matrix (via `sub_940A10`). Tested against compound-shape
bounds. Results are sorted by distance.
Used with: `collNarrow_MultiOBB`, `collBounds_Compound4`, `collStore_NopB`

---

## Named Callback Triples

Full inventory of all named `collNarrow_*`, `collBounds_*`, `collStore_*` functions:

### Narrowphase (func1 at callback_struct+64)

| Function | Address | Shape |
|----------|---------|-------|
| `collNarrow_LineSeg` | `0x955970` | Ray/line segment |
| `collNarrow_LineFirstHit` | `0x9498C0` | Ray — stops at first hit (no multi-result) |
| `collNarrow_SphereA` | `0x9496A0` | Sphere variant A |
| `collNarrow_SphereB` | `0x94A810` | Sphere variant B |
| `collNarrow_Capsule` | `0x94B7E0` | Capsule |
| `collNarrow_DynCapsuleA` | `0x94F430` | Dynamic capsule (animated bone) variant A |
| `collNarrow_DynCapsuleB` | `0x94F8B0` | Dynamic capsule variant B |
| `collNarrow_CapsuleOBBAdapt` | `0x94FAE0` | Capsule vs OBB (adaptive) |
| `collNarrow_CapsuleEdge4` | `0x94FC10` | Capsule vs 4-edge polygon |
| `collNarrow_MultiOBB` | `0x94ECD0` | Multiple OBBs |
| `collNarrow_OBBSimple` | `0x94F360` | Single OBB |
| `collNarrow_BoxSweep` | `0x95BCF0` | AABB sweep |
| `collNarrow_FootprintLine` | `0x9486C0` | Footprint ground contact line |

### Broadphase bounds (func2 at callback_struct+68)

| Function | Address | Computes |
|----------|---------|---------|
| `collBounds_LineSeg` | `0x9532C0` | AABB of line segment |
| `collBounds_LineSegA` | `0x948980` | LineSeg AABB variant A |
| `collBounds_LineSegB` | `0x949A10` | LineSeg AABB variant B |
| `collBounds_Sphere` | `0x94A8C0` | Sphere AABB |
| `collBounds_CapsulePair` | `0x94B830` | Capsule-pair AABB |
| `collBounds_TwoCapsule` | `0x953FB0` | Two-capsule (swept?) AABB |
| `collBounds_OBBAvg` | `0x950BD0` | OBB averaged AABB |
| `collBounds_DualMatrix` | `0x951880` | Two-matrix (bone-animated) AABB |
| `collBounds_Compound4` | `0x94D2D0` | Compound 4-shape AABB |
| `collBounds_BoxHalfExt` | `0x95BF00` | Half-extents box AABB |

### Hit-commit / store (func3 at callback_struct+72)

| Function | Address | Stores |
|----------|---------|--------|
| `collStore_LineInfo` | `0x955940` | Copies narrowphase result → `LineInfo.member_0x40` |
| `collStore_AABBFields` | `0x94C4E0` | Writes AABB fields into result struct |
| `collStore_TriDeref` | `0x953230` | Dereferences triangle data, stores vertex info |
| `collStore_Qword2` | `0x9498A0` | Stores 8-byte (64-bit) result |
| `collStore_Qword16` | `0x95CB80` | Stores 16-byte (128-bit) result (BoxSweep) |
| `collStore_NopA` | `0x949670` | No-op — first-hit detection only |
| `collStore_NopB` | `0x94EC50` | No-op variant B (MultiOBB detection only) |

---

## Result Data from `findIntersection`

### Return value

```c
int hit = sCollision::findIntersection(...);   // treat as bool: non-zero = any hit
```

The return value is the OR-accumulation of all per-Sbc results from `query_all_sbcs`.
Zero means no geometry was penetrated. Non-zero means at least one hit was found and
the output Param (5th arg) is valid.

---

### Closest-hit selection mechanism

`findIntersection` initialises `ContactPacket + 96` to `FLT_MAX` before the BVH
traversal. Every narrowphase callback (`collNarrow_*`) is entered for a candidate leaf
and begins with:

```c
if (t > *(float*)(contact_packet + 96)) return 0;   // farther than current best — skip
```

If the new intersection parameter `t` is smaller (nearer), the callback overwrites
`contact_packet + 96` with `t` and commits the result into the output Param. This
means **only the single nearest hit survives** when the query uses `collNarrow_LineSeg`.

---

### Primary result — `sCollision::hit_result_t*` (5th arg)

The output struct (`sCollision::hit_result_t`, 132 bytes) is passed as the 5th arg to
`findIntersection`. It is a **pure output struct** — separate from the query input block
(`sCollision::query_block_t`, 60 bytes) which is arg2. Callers allocate them independently.

`collNarrow_LineSeg` (0x955970) populates it via `v36 = *(ContactPacket + 108)`:

**Complete `sCollision::hit_result_t` field table:**

| Offset | Dec | Type | Field | Notes |
|--------|-----|------|-------|-------|
| +0x00 | 0 | float | `tri_meta_0` | `LineInfo.member_0x0.x` — triangle metadata |
| +0x04 | 4 | int | `tri_meta_1` | `LineInfo.member_0x0.padding` |
| +0x08 | 8 | float | `tri_plane_n_y` | `LineInfo.member_0x10.normal.y` — raw (pre-normalised) plane normal Y |
| +0x0C | 12 | float | `tri_plane_n_z` | `LineInfo.member_0x10.normal.z` |
| +0x10 | 16 | float | `tri_plane_d` | `LineInfo.member_0x10.dist` — raw plane D |
| +0x14 | 20 | — | `_gap14[12]` | unknown / padding |
| +0x20 | 32 | `MtVector3` | `tri_v0` | hit triangle vertex 0, world-space (bone-transform applied) |
| +0x30 | 48 | `MtVector3` | `tri_v1` | hit triangle vertex 1, world-space |
| +0x40 | 64 | `MtVector3` | `tri_v2` | hit triangle vertex 2, world-space |
| +0x50 | 80 | `MtVector4` | `surface_plane` | xyz = outward unit normal, w = plane_D (normalised) |
| +0x60 | 96 | `MtVector3` | `hit_point` | world-space hit position |
| +0x70 | 112 | `MtVector3` | `neg_ray_dir` | negated ray direction (unit) |
| +0x80 | 128 | float | `distance` | parametric t along ray (0.0=start, 1.0=end) |

**Triangle vertices (`tri_v0/v1/v2`):** When the hit Part is bone-animated
(`LineInfo.member_0x20.p0.x` byte ≠ 0), each vertex is transformed from geometry-local
space to world space via the Part's bone matrix columns (`member_0x40.p0/p1`,
`member_0x20.p1`). For static geometry the values are used directly.

Confirmed by `cUtil::checkHeight`: reads `hit_result.hit_point.xyz` (+0x60..+0x68) as ground position.

---

### Canonical read pattern

```c
sCollision::hit_result_t result;    // pure output — 5th arg to findIntersection
sCollision::query_block_t query;    // separate — 2nd arg (query input)

if (sCollision::findIntersection(sDevil4CollisionPtr, &query, shape, nullptr, &result, callback_struct)) {
    MtVector3 hit_pos  = result.hit_point.xyz;      // +0x60..+0x68
    MtVector4 plane    = result.surface_plane;       // +0x50: normal(xyz) + plane_D(w)
    float     dist     = result.distance;            // +0x80
    // triangle vertices in world space:
    MtVector3 v0 = result.tri_v0.xyz;               // +0x20
    MtVector3 v1 = result.tri_v1.xyz;               // +0x30
    MtVector3 v2 = result.tri_v2.xyz;               // +0x40
}
```

---

### Role of `collStore_LineInfo` and the `LineInfo` buffer

`collStore_LineInfo` (0x955940) operates on a **`LineInfo` struct allocated on
`findIntersection`'s own stack** — not on the caller's Param. It simply commits:

```c
LineInfo.member_0x40.p0 = LineInfo.member_0x20.p0;   // hit position snapshot
LineInfo.member_0x40.p1 = LineInfo.member_0x20.p1;   // hit normal snapshot
```

`findIntersection` points `callback_struct + 76` at this local `LineInfo` before the
traversal; `collNarrow_LineSeg` writes intermediate results into `.member_0x20`, and
`collStore_LineInfo` promotes them to `.member_0x40`. **This buffer is gone when
`findIntersection` returns.** Callers must not try to read it post-return.

The primary, caller-accessible result is always the `sCollision::Param*` (5th arg)
table above — populated by `collNarrow_LineSeg` directly via the ContactPacket +108
pointer, independently of `collStore_LineInfo`.

---

### `collBounds_LineSeg` role

`collBounds_LineSeg` (0x9532C0) is the **broadphase** callback, not a result producer:
- Inverts the Sbc's world matrix (full 4×4)
- Transforms both ray endpoints into local space
- Outputs a local-space AABB to the context buffer at offsets +64..+91
- Returns 0 — result is only consumed by `checkAttr` for BVH traversal gating

---

## Group Filter Mask Values

The `group_filter` in the query param block and `setCallback` selects which Sbc groups
to include. Each bit corresponds to a geometry kind registered in the world.

Observed values from caller sites:

| Hex value | Meaning | Used by |
|-----------|---------|---------|
| `0x20000000` | Camera/wall geometry | `cCameraPlayer::checkHit`, camera line-of-sight |
| `0x10000000` | Stage floor / ground | `uPlayer::checkStingerJump`, ledge detection |
| `0x20200` (`0x200 | 0x20000`) | Script + scripted stage geometry | `uPlayer::updateSctClsnInfo` |
| `0x131584` | Combined flags (position detection) | `uPlayer::updateSctClsnInfo` |
| caller-supplied | — | `cUtil::checkHeight` passes caller's filter through |

The filter is stored in the callback struct at `+0x50` and compared in `query_all_sbcs`
against `Sbc.mGroupMask` (+24 in the Sbc). Any Sbc whose group mask has no common bits
with the filter is skipped entirely.

---

## Type Mask Values

The `type_mask` (first field of the query block, i.e. `arg2[0]`) selects which geometry
node types within an Sbc are tested. 127 (0x7F = bits 0–6) is the universal "all types"
value and is used by virtually every caller. Specific values:

| Value | Meaning |
|-------|---------|
| 127 (0x7F) | All geometry types |
| other | Subset of geometry types (not mapped in detail) |

If the query block's type field is 0, `findIntersection` substitutes
`sDevil4Collision->mDefaultType` (the singleton's default).

---

## Representative Caller Patterns

### Vertical position / ground detection

`uPlayer::updateSctClsnInfo` (0x7A8A60) — checks what's directly above and below the player:

```c
// Shape: vertical line segment ±100 units around player Y
shape[0..2] = player.x, player.y + 100, player.z;   // top
shape[4..6] = player.x, player.y - 100, player.z;   // bottom

query_block[0] = 127;        // all types
query_block[1] = 0x20200;    // script+stage geometry
query_block[6] = -1;         // no handle exclusion
query_block[7] = -1;
query_block[9] = 10;         // up to 10 hits

sCollision::setCallback(result, collNarrow_LineSeg, collBounds_LineSeg, collStore_LineInfo, 0, 0x20200, 0);
hit = sCollision::findIntersection(sDevil4CollisionPtr, query_block, shape, nullptr, &player.sct_clsn, result);
// player.sct_clsn stored at uPlayer + 8208
```

### Ground height query

`cUtil::checkHeight` (0x45E790) — issues TWO queries (up and down) then returns the closer hit point:
- Query 1: upward line → checks ceiling
- Query 2: downward line → checks floor
- Returns the hit `MtVector3` position (and optionally the hit normal)

Both use `collNarrow_LineSeg + collBounds_LineSeg + collStore_LineInfo` with the caller-supplied filter.

### Ledge / wall detection

`uPlayer::checkStingerJump` (0x804020):
- Issues TWO separate line-segment queries (toward and away from the wall)
- Uses filter `0x10000000` (stage floor only)
- Returns `true` if the forward query hits and the reverse query does NOT — confirms a ledge edge

### Camera line-of-sight

`cCameraPlayer::checkHit` (0x41D730) uses THREE different query types:
1. `sCollision::findIntersection_LineSeg` (0x95B320) — basic wall LOS with `both_sides=0`
2. `sCollision::findIntersection_LineSeg` — LOS check with `both_sides=1` (test from opposite direction)
3. `sCollision::findIntersection_BoxSweep` (0x95CBE0) — swept box for camera clearance
4. `sub_94EF30` (0x94EF30) — Multi-OBB query for finding the exact push vector

Camera filter: `0x20000000` throughout.

### IK foot placement

`cLegIkCtrl::update` (0x7B0B50):
- Vertical line segment cast downward from foot bone world position
- Filter = stage geometry (`0x10000000`)
- Result Y used to set the IK target ground height

---

## `findIntersection_LineSeg` — Full Signature

```c
// 0x95B320
int __userpurge sCollision::findIntersection_LineSeg@<eax>(
    int a1@<eax>,                   // query param block (same layout as above)
    sDevil4Collision *param_2,      // singleton (sDevil4CollisionPtr)
    undefined4 param_3,             // shape endpoint data (line segment float[8])
    auto_structs::TriangleInfo *param_4,  // optional TriangleInfo (usually nullptr)
    auto_structs::sCollision::Param *a5); // output result
```

Internally:
```c
sCollision::setCallback(result, collNarrow_LineSeg, collBounds_LineSeg, collStore_LineInfo, 0, *(a1 + 4), 0);
return sCollision::findIntersection(param_2, a1, param_3, param_4, a5, result);
```

The filter is automatically pulled from `a1 + 4` (the group_filter field of the caller's query block).

---

## `findIntersection_BoxSweep` — What It Does

```c
// 0x95CBE0 — used by camera for wall push
int __stdcall sCollision::findIntersection_BoxSweep(
    undefined4 param_2,      // sDevil4CollisionPtr
    float *param_3,          // in/out: first point (modified to resolved position)
    float *param_4,          // in/out: second point
    undefined4 param_5,      // additional param (filter or flags)
    undefined4 *a5);         // config block (16 DWORDs)
```

- Does NOT call `findIntersection` — calls `sub_95CE50` and `sub_95CE00` directly
- Makes TWO sweep passes (different filters from `a5[1]` and `a5[0]`)
- Each pass uses `collNarrow_BoxSweep + collBounds_BoxHalfExt + collStore_Qword16`
- Modifies `param_3` in-place if a collision is found (pushes the point out of geometry)
- Follows up with `sub_95CE00` for a spherical refinement step

---

## `sub_94EF30` — Multi-OBB Query

```c
// 0x94EF30 — used by camera for OBB wall detection
int __fastcall sub_94EF30(
    undefined4 a1,           // OBB matrix / transform
    sDevil4Collision *a2,    // singleton
    undefined4 param_2,      // output result buffer ptr
    undefined4 param_3,      // query params
    undefined4 param_4,      // filter
    int a6);                 // 0=one-sided, non-zero=two-sided
```

- Calls `sCollision::count_unique_resources` (bail if empty)
- Calls `sub_940F10` and `sub_940A10` to set up OBB world matrices
- Uses `collNarrow_MultiOBB + collBounds_Compound4 + collStore_NopB`
- Bubble-sorts up to `v38` results by distance
- Applies matrix transform (SSE) to each hit point
- Writes results to `param_2` as an array of (normal, hit_point) pairs

---

## Global Pointer

```c
sDevil4Collision *sDevil4CollisionPtr;   // global at some address (used directly in all callers)
```

All callers load this from the same global. It IS the `sCollision` singleton (same object
as `sCollision::mpInstance`).

---

## Key Addresses Summary

| Symbol | Address |
|--------|---------|
| `sCollision::findIntersection` | `0x95B370` |
| `sCollision::findIntersection_LineSeg` | `0x95B320` |
| `sCollision::findIntersection_BoxSweep` | `0x95CBE0` |
| `sub_94EF30` (Multi-OBB query) | `0x94EF30` |
| `sCollision::setCallback` | `0x50DFB0` |
| `sCollision::collNarrow_LineSeg` | `0x955970` |
| `sCollision::collBounds_LineSeg` | `0x9532C0` |
| `sCollision::collStore_LineInfo` | `0x955940` |
| `sCollision::collNarrow_LineFirstHit` | `0x9498C0` |
| `sCollision::collNarrow_SphereA` | `0x9496A0` |
| `sCollision::collNarrow_SphereB` | `0x94A810` |
| `sCollision::collBounds_Sphere` | `0x94A8C0` |
| `sCollision::collNarrow_Capsule` | `0x94B7E0` |
| `sCollision::collBounds_CapsulePair` | `0x94B830` |
| `sCollision::collNarrow_DynCapsuleA` | `0x94F430` |
| `sCollision::collNarrow_DynCapsuleB` | `0x94F8B0` |
| `sCollision::collNarrow_CapsuleOBBAdapt` | `0x94FAE0` |
| `sCollision::collNarrow_CapsuleEdge4` | `0x94FC10` |
| `sCollision::collNarrow_MultiOBB` | `0x94ECD0` |
| `sCollision::collNarrow_OBBSimple` | `0x94F360` |
| `sCollision::collNarrow_BoxSweep` | `0x95BCF0` |
| `sCollision::collNarrow_FootprintLine` | `0x9486C0` |
| `sCollision::collBounds_LineSegA` | `0x948980` |
| `sCollision::collBounds_LineSegB` | `0x949A10` |
| `sCollision::collBounds_TwoCapsule` | `0x953FB0` |
| `sCollision::collBounds_OBBAvg` | `0x950BD0` |
| `sCollision::collBounds_DualMatrix` | `0x951880` |
| `sCollision::collBounds_Compound4` | `0x94D2D0` |
| `sCollision::collBounds_BoxHalfExt` | `0x95BF00` |
| `sCollision::collStore_AABBFields` | `0x94C4E0` |
| `sCollision::collStore_TriDeref` | `0x953230` |
| `sCollision::collStore_Qword2` | `0x9498A0` |
| `sCollision::collStore_Qword16` | `0x95CB80` |
| `sCollision::collStore_NopA` | `0x949670` |
| `sCollision::collStore_NopB` | `0x94EC50` |
