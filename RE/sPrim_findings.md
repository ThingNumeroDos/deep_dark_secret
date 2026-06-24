# sPrim — Immediate-Mode Overlay Primitive Renderer

## Overview

`sPrim` is a singleton that implements a CPU-driven, depth-sorted line-primitive renderer used for debug/overlay geometry (hitboxes, bounding spheres, capsules, etc.). It accumulates draw calls during the frame and GPU-flushes them in a single overlay pass at frame end.

- Singleton: `sPrim::mpInstance`
- Struct size: **20256 bytes**
- Max simultaneous draw-call slots: **1024** (`0x400`)

---

## Key Types

### `sPrim` (singleton, `0x20` bytes of known header fields)

| Offset | Name | Type | Notes |
|--------|------|------|-------|
| +0x20 | `mPrimNum` | `uint` | total prims submitted this frame |
| +0x24 | `mDrawPrimitiveNum` | `uint` | |
| +0x28 | `mDrawSplitNum` | `uint` | |
| +0x2C | `mDepthSplitNum` | `uint` | |
| +0x30 | `mStateChangeNum` | `uint` | |
| +0x34 | `mTextureChangeNum` | `uint` | |
| +0x38 | `mNearStart` | `float` | |
| +0x3C | `mNearEnd` | `float` | |
| +0x40 | `mFarStart` | `float` | |
| +0x44 | `mFarEnd` | `float` | |
| +0x48 | `mReductionDist` | `uint` | |
| +0x4C | `mVolumeScale` | `float` | |
| +0x50 | `mParallaxScale` | `float` | |
| +0x54 | `mParallaxMinLoop` | `uint` | |
| +0x58 | `mParallaxMaxLoop` | `uint` | |
| +0x5C | `mParallaxFadeStart` | `float` | |
| +0x60 | `mParallaxFadeEnd` | `float` | |
| +0x64 | `mDynamicReductionControl` | `byte` | |
| +0x68 | `mVolumeEnable` | `byte` | |
| +0x6C | `mParallaxEnable` | `byte` | |
| +0x1EB4 | slot header array | stride 12 B | up to 1024 entries; each has 3 DWORDs |
| +0x4EB0 | `member_0x4eb0` | `volatile LONG` | atomic slot counter (`InterlockedIncrement`) |

### `sPrim::Prim` (96 bytes — per-draw-call slot)

| Offset | Name | Type | Notes |
|--------|------|------|-------|
| +0x00 | *(unknown)* | `uint` | |
| +0x04 | *(unknown)* | `uint` | |
| +0x08 | `mTagNum` | `uint` | number of segments submitted so far |
| +0x0C | `mpTag` | `void *` | pointer to depth-sort tag array |
| +0x10 | `mpTrans` | `void *` | owning object pointer (used for ring-buffer access) |
| +0x20 | `mViewVec` | `MtMath::MtVector4` | negated camera-matrix rows [2,6,10,14] — view-space normal for depth sort |
| +0x30 | `mTexHandle` | `uint` | |
| +0x34 | `mDisp_lvl` | `uint` | display level / sort layer; packed into tag word at bit 23 |
| +0x38 | `mSubPriority` | `uint` | written into low byte of tag word |
| +0x3C | `mPrimPacketBorder` | `byte` | ring-buffer capacity limit for this slot |
| +0x44 | `pMetaData` | `sPrim::Prim::METADATA_HEAD` | 8-byte metadata head (copied into high-water region for transparent segments) |
| +0x4C | *(unknown)* | 4 B | appended after metadata head |

Each depth-sort tag entry (at `mpTag[mTagNum]`, stride 8 bytes):
- `[0]`: `(depth_clamped & 0x7FFF) << 8 ^ (flags_byte | (mDisp_lvl << 23))`, then low byte overwritten with `mSubPriority`
- `[1]`: pointer to the 80-byte vertex slot in the ring buffer

---

## Draw Pipeline

### Step 1 — Acquire a slot: `sPrim::getcPrim` (`0xA34EE0`)

```c
sPrim::Prim *prim = sPrim::getcPrim(owner, sPrim::mpInstance, prim_type, layer);
```

**Registers / args:**

| Param | Register | Meaning |
|-------|----------|---------|
| `a1` | `esi` | owning object (`uCoord*` or similar) |
| `param_2` | stack | `sPrim::mpInstance` |
| `param_3` | stack | primitive type (e.g. `6` for line shapes) |
| `a4` | `eax` | render layer / priority bucket |

**What it does:**
- Atomically claims a slot index via `InterlockedIncrement(&mpInstance->member_0x4eb0)`, wrapping at 1024.
- Reads `owner->field[2724]` (camera/view matrix pointer) and stores the negated view-space normal (columns 2, 6, 10, 14) into `prim->mViewVec` — used for per-segment depth computation.
- On first draw per layer, caches the owner's material/texture state into a 240-byte per-layer record at `param_2 + 112 + 240 * layer_index`.
- Returns the opaque `sPrim::Prim*` packet handle.

### Step 2 — Build flags

Each `submitLine` call takes a `uint *flags` pointing to a 2-DWORD header built by the caller:

```c
flags[0] = (prev_flags[0] & 0xFFFF341F) | 0x3400;  // blend/state bits
flags[1] = 16;                                        // vertex stride sentinel
```

`0x3400` encodes the primitive state. If `flags[1] & 0xA0`, the segment additionally writes a 12-byte metadata entry into the ring buffer's high-water region (transparent/overlay blend path).

### Step 3 — Submit segments: `sPrim::submitLine` (`0x45D1F0`)

```c
sPrim::submitLine(prim, start_pos, end_pos, color, flags);
```

**Calling convention:** `__usercall`
- `prim@<ecx>` — the slot from step 1
- `start_pos@<edi>` — `MtMath::MtVector3*`, world-space start vertex
- `end_pos` (stack) — `MtMath::MtVector3*`, world-space end vertex
- `color` (stack) — `uint` ARGB, applied to both endpoints
- `flags` (stack) — `uint*`, the 2-DWORD header from step 2

**What it does:**

1. **Depth sort key** — `depth = dot(start_pos, prim->mViewVec.xyz) * (1/farZ)`, clamped to `[0, 0x7FFF]`. Negative → segment silently dropped (behind camera).
2. **Capacity check** — `(owner[2734] + 16*owner[2731] - owner[2732]) <= prim->mPrimPacketBorder`. If the ring buffer is full, segment is dropped.
3. **Ring buffer advance** — `write_ptr = (owner[2732] & ~0xF) - 80` (claims 80 bytes, strips alignment bits).
4. **Tag entry** — appends to `prim->mpTag[mTagNum++]`: depth word + pointer to the new vertex slot.
5. **Vertex record** (80 bytes at `vertex_slot`):

| Offset | Content |
|--------|---------|
| +0x00 | `(flags[0] & ~0x1F) | 1` — type bits |
| +0x04 | `flags[1]` |
| +0x08 | `2` (line primitive type constant) |
| +0x0C | metadata ptr (or null) |
| +0x10 | `start_pos` XYZ |
| +0x1C | `color` (start endpoint) |
| +0x24 | UV = `0xFFFE` (line sentinel) |
| +0x26 | UV = `256` |
| +0x2F | `0` (padding) |
| +0x30 | `end_pos` XYZ |
| +0x3C | `color` (end endpoint) |
| +0x44 | UV = `0xFFFE` |
| +0x46 | UV = `256` |
| +0x4F | `0` (padding) |

### Step 4 — Frame flush (implicit)

No explicit flush call is needed. `sPrim` accumulates all slots and their tag arrays across the frame, depth-sorts the tags, and GPU-flushes the ring buffer in the overlay pass. The geometry appears in the next presented frame.

---

## Example: `cUtil::drawSphere` (`0x460E60`)

```c
void __usercall cUtil::drawSphere(
    unsigned int layer@<eax>,
    MtMath::MtVector3 *center@<ecx>,
    void *owner,
    float radius,
    unsigned int color);
```

Draws a wireframe sphere as 3 interlocked great-circle arcs (XZ, XY, YZ). Each arc is 16 line segments (step = π/8 ≈ 22.5°). All geometry is computed in world space on the CPU — no GPU transform matrix is applied.

```
prim = getcPrim(owner, mpInstance, 6, layer)

for i in 0..15:                          // 16 steps = full circle
    theta      = i * (π/8)
    theta_next = theta + π/8

    // XZ-plane arc
    submitLine(prim,
        (cx + cos(theta)*r,      cy, cz + sin(theta)*r),
        (cx + cos(theta_next)*r, cy, cz + sin(theta_next)*r),
        color, flags)

    // XY-plane arc
    submitLine(prim,
        (cx + cos(theta)*r,      cy + sin(theta)*r,      cz),
        (cx + cos(theta_next)*r, cy + sin(theta_next)*r, cz),
        color, flags)

    // YZ-plane arc
    submitLine(prim,
        (cx, cy + sin(theta)*r,      cz + cos(theta)*r),
        (cx, cy + sin(theta_next)*r, cz + cos(theta_next)*r),
        color, flags)

// 4 axis-aligned cap segments (±X, ±Y, ±Z poles/equator)
submitLine(prim, (cx, cy-r, cz), (cx, cy+r, cz), color, flags)   // Y spine
submitLine(prim, (cx-r, cy, cz), (cx+r, cy, cz), color, flags)   // X equator
submitLine(prim, (cx, cy, cz-r), (cx, cy, cz+r), color, flags)   // Z equator
// (4th cap segment also present — minor variant)
```

Total: **52 line segments** per sphere.

---

## Known Callers of `sPrim::getcPrim`

| Function | Shape |
|----------|-------|
| `cUtil::drawSphere` (`0x460E60`) | wireframe sphere |
| `cUtil::drawCapsule` (`0x461300`) | wireframe capsule |
| `sub_45B410` | unknown |
| `sub_4964B0` | unknown |
| `sub_4AC0D0` | unknown |
| `sub_4ACFD0` | unknown |
| `sub_4B1610` | unknown |
| `sub_4FB560` | unknown |
| `sub_533020` | unknown |
| `sub_533460` | unknown |
| `sub_533980` | unknown |
| `sub_533EF0` | unknown |
| `sub_5369F0` | unknown |
| `sub_53E930–sub_53ECA0` | (cluster, likely per-shape-type draw helpers) |
| `sub_76B360` | unknown |
| `sub_776180`, `sub_7769A0` | unknown |
| `sub_852620` | unknown |
| `sub_99DE40–sub_99E8B0` | (cluster) |
