# `sCollision::collNarrow_LineSeg` — return struct analysis

**Function:** `0x955970` (0x7D2 bytes)
**Role:** narrowphase ray/line-segment vs triangle test, installed into `callback_struct_t.func_narrow` (+0x40), invoked per-triangle by `query_all_sbcs`.

## Summary

The function returns a plain `int` (0 = miss, 1 = hit). There is no returned struct
pointer — there are **two output structs written through parameters**:

1. `sCollision::LineInfo *info` (arg 2) — the primary in/out record.
2. `sCollision__LineResult *info->pResult` (+0x6C) — an optional 132-byte extended record.

## Corrections applied to the IDB

### 1. Parameter order was swapped

Previous signature had `(sCollision::LineInfo *param_2, int a2)`, but the body uses
`param_2` as the triangle source (`getTriangle`, `tri->mCoord`, `tri->mpSbc`) and `a2`
as the LineInfo. Corrected to:

```c
int __cdecl sCollision::collNarrow_LineSeg(TriangleInfo *tri, sCollision::LineInfo *info)
```

This matches `sCollision::collStore_LineInfo` (`0x955940`), which already had the
correct `(TriangleInfo*, sCollision::LineInfo*)` order.

### 2. `LineInfo::pTriangle` → `pResult`

The field at +0x6C is **not** a triangle pointer. `sCollision::init_query_packet`
(`0x940721`) assigns it from `ScrCollisionCore`'s `hitOut` argument — the caller's
output buffer. In `cUtil::checkGround` that is `&ray_start`, read back afterwards
as the hit position.

Retyped `sCollision::LineInfo` to 116 bytes with explicit `_pad69[3]`. Without the
padding IDA packs the `both_sides` bool and shifts `pResult` to +0x6A (struct size
114) — the overlay gotcha; always re-inspect after declaring.

### 3. New type `sCollision__LineResult` (132 bytes)

| Offset | Field | Notes |
|--------|-------|-------|
| +0x00 | `mpSbc` | **pointers** copied from `TriangleInfo` — identity of what was hit |
| +0x04 | `member_0xc_copy` | |
| +0x08 | `pPartsInfo` | |
| +0x0C | `pTriangle` | |
| +0x10 | `pVertex` | |
| +0x20 | `triNormalWorld` | triangle plane, post-transform |
| +0x30 | `triVert1World` | |
| +0x40 | `triVert2World` | |
| +0x50 | `hitNormalWorld` | hit normal |
| +0x5C | `hitPlaneDistWorld` | `-(N·P)` |
| +0x60 | `hitPosWorld` | hit position |
| +0x70 | `sweepDirNeg` | negated normalized sweep dir |
| +0x80 | `hitDistance` | `\|dir\|² × t` |

**Note:** +0x00..+0x14 are five pointers, not geometry. An earlier reading of the
Hex-Rays output as `hit_pos`/`hit_plane` floats was wrong — the retype exposed them
as `tri->mpSbc`, `tri->pPartsInfo`, `tri->pTriangle`, `tri->pVertex`.

### Size verified at 132 bytes (0x84)

Disassembly of the `pResult`-guarded block (`0x955FB8`–`0x956117`) shows **22 stores,
all through `ebx`** (loaded from `info->pResult` at `0x955F3A`), with maximum
displacement `[ebx+80h]` (4-byte `movss`) → 0x84 = 132 bytes. Every displacement
matches a declared field:

```
+0x04 +0x08 +0x0C +0x10          pointers from TriangleInfo
+0x20 +0x24 +0x28                triPlaneNormal
+0x30 +0x34 +0x38                triPlaneVec1
+0x40 +0x44 +0x48                triPlaneVec2
+0x50 +0x58  (movq, 8-byte)      hitNormal + hitPlaneDist
+0x60 +0x64 +0x68                hitPos
+0x70 +0x74 +0x78                sweepDirNeg
+0x80                            hitDistance
```

### Measuring buffer size from decompiler lvars is unreliable

Scanning `ScrCollisionCore` callers for the `hitOut` slot appeared to show sizes of
0x50 / 0x60 / 0x64 / 0x98, suggesting the struct could be no larger than 0x50 and that
132 bytes would overflow the caller's stack. **That was an artifact.** Hex-Rays splits
a large untyped stack buffer into multiple independent lvars, so the "gap to next lvar"
is the gap to the *interior* of the same buffer, not its end.

Ground truth in `cUtil::checkGround`: `ray_start` at frame 0x0E4, apparent gap 0x50 —
but the following lvars are pieces of the same buffer:

| Frame off | lvar | Buffer offset | Field |
|---|---|---|---|
| 0x134–0x140 | `local_a0`, `local_9c`, `local_98`, `v25` | +0x50…+0x5C | `hitNormal`, `hitPlaneDist` |
| 0x144–0x14C | `x_2`, `y_1`, `z_2` | +0x60…+0x68 | `hitPos` |

`checkGround` reads `x_2/y_1/z_2` back as the hit position, proving they are one buffer.
The next genuine local is `ray_end` at 0x174, leaving 0x90 for the 0x84 struct — no
overrun. Callers declare the buffer as `MtVector3` / `MtVector3[3]` / `[4]` / `[9]`;
all are stubs that understate the real size.

## LineInfo field roles confirmed

From `init_query_packet` + the narrowphase body:

| Offset | Field | Direction |
|--------|-------|-----------|
| +0x00 | `hit_pos` | out |
| +0x10 | `hit_plane` | out (normal xyz + dist) |
| +0x20 | `mLineSegment` | in — the sweep, from `ls` |
| +0x40 | `mBasis` | in — read as the query segment here; `collStore_LineInfo` saves `mLineSegment` into it |
| +0x60 | `nearestT` | in/out — init `FLT_MAX`; farther hits rejected at `0x955C59` |
| +0x64 | `attributes` | out — OR'd with `getAdjustContactType`; **this is `ScrCollisionCore`'s return value** |
| +0x68 | `both_sides` | in — when 0, backface hits (`v18 > 0`) rejected |
| +0x6C | `pResult` | in — optional output buffer |
| +0x70 | `pParam` | in — `hitCallback` filter at `[+12]`/this `[+8]`/data `[+16]` |

## Scope check on the +0x6C rename

Scanned all 13 `collNarrow_*` callbacks for pointer loads at +0x6C/+0x70.
**Only `collNarrow_LineSeg` dereferences them.** The other twelve read +0x60/+0x64/+0x68
as three consecutive floats (a vector), meaning they operate on a *different* struct
that merely overlaps the address range — so renaming the `LineInfo` field is safe and
affects no other shape.

## All narrowphase/store pairings (every possible output shape)

Extracted from all 138 `sCollision::ScrCollisionBeforeFunc` call sites across 123
functions (decompiler arg extraction; 0 failures). 12 unique narrow/store pairings:

| Narrow callback | Store callback | Sites |
|---|---|---|
| `collNarrow_LineSeg` | `collStore_LineInfo` | 107 |
| `collNarrow_CapsuleEdge4` | `collStore_TriDeref` | 8 |
| `collNarrow_Capsule` | `collStore_AABBFields` | 4 |
| `collNarrow_DynCapsuleA` | `collStore_Qword16` | 4 |
| `collNarrow_FootprintLine` | `collStore_NopA` | 3 |
| `collNarrow_BoxSweep` | `collStore_Qword16` | 3 |
| `collNarrow_SphereB` | `collStore_Qword2` | 2 |
| `collNarrow_SphereA` | `collStore_Qword2` | 1 |
| `collNarrow_LineFirstHit` | `collStore_NopA` | 1 |
| `collNarrow_MultiOBB` | `collStore_NopB` | 1 |
| `collNarrow_DynCapsuleB` | `collStore_Qword16` | 1 |
| `collNarrow_CapsuleOBBAdapt` | `collStore_TriDeref` | 1 |
| `collNarrow_OBBSimple` | `collStore_Qword16` | 1 |

Only `sCollision__LineResult` (the LineSeg shape) has been fully typed. The
`Qword16` / `Qword2` shapes write 16 and 8 bytes respectively; the `Nop*` stores
write nothing. Those remain untyped.

**+0x6C/+0x70 are LineSeg-specific.** Scanning all 13 `collNarrow_*` callbacks for
pointer loads at those displacements: only `collNarrow_LineSeg` dereferences them
(`mov eax,[esi+70h]` at `0x955C2A`, `mov ebx,[esi+6Ch]` at `0x955F3A`). The other
twelve read +0x60/+0x64/+0x68 as three consecutive floats — a vector in a *different*
struct that merely overlaps the address range. Renaming the `LineInfo` field is
therefore safe and affects no other shape.

## Output-space branch

`tri->mMove` (at `0x955C5F`) selects the space. When set, results are transformed
through `tri->mCoord` (4x4; `vectors[0..2]` basis, `vectors[3]` translation) into
world space. When clear, local values pass through unchanged. This is why
`LineResult` carries both a triangle-space plane (+0x20..+0x38) and world-space
normal/position (+0x50..+0x68).

## Early-out order

backface (`v18 > 0` when `!both_sides`) → degenerate denominator (`|v18| < 1e-4`) →
`t < 0` → `t > 1` → `sub_95B490` point-in-triangle → `pParam->hitCallback` filter →
`nearestT` gate.
