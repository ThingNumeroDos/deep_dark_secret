# sCollision / sCollisionGame — Collision System Findings

## Overview

The collision system has two layers:

- **`sCollision`** (physics/geometry layer): BVH-based broadphase + narrowphase geometry tests, resource management, Sbc (shape-bound container) objects. Lives in the 0x940xxx–0x95Fxxx range.
- **`sCollisionGame`** (gameplay layer): per-frame attack/hurt box hit detection, group filtering, damage dispatch. Lives in the 0x47Cxxx–0x47Dxxx range.

The two are connected: `sCollisionGame::checkGroup_` drives into `sCollision`'s BVH and narrowphase, while `sCollisionGame::checkAttackObj` applies gameplay rules (ignore lists, actor identity, VsAttr masks) before issuing geometry queries.

---

## Key Types

### `sDevil4Collision` / sCollision singleton

The type IDA labelled `sDevil4Collision` is the sCollision singleton (DMC4-specific name for the engine's collision singleton). Key field layout confirmed from code:

| Offset | Field | Notes |
|--------|-------|-------|
| +4 | `CRITICAL_SECTION` | threading guard |
| +48 | `mNodeCount` | registered live Node count |
| +168 | `mSbcArray.mLength` | total Sbc count (capacity) |
| +176 | `mSbcArray.mpArray` | `sCollision::Sbc*[]` |
| +0xBC | `mThreadResultOfs[]` | per-thread result offset table (used in `moving_part_aabb_test`) |
| +0x44 | `mGroupFilter[]` | per-thread group filter DWORDs |
| +0x64 | `mLastHitPart[]` | per-thread last-hit part index |

Node registration: `sCollision::registResource` (0x946750), allocates 76-byte `sCollision::Node` objects.  
Node array: `sCollision+176` (mpArray field).

---

### `sCollision::Node` (76 bytes)

Live registration entry for a dynamic collision object.

| Offset | Type | Field |
|--------|------|-------|
| +0 | ptr | vtable (`vtable_sCollision_Node`) |
| +4 | int | ref_count |
| +8 | ptr | registered collider object (the uActor or component) |
| +20 | byte | active flag (1 = active) |
| +21 | byte | enabled flag (1 = enabled) |
| +24 | int | group_id (−1 = none) |
| +28 | byte | dirty flag |
| +32 | ptr | `off_C05E20` (type descriptor?) |
| +52 | ptr | `off_E14378` |
| +72 | DWORD | handle = `slot_index | 0xFFFF0000` |

`sCollision::registResource` (0x946750) returns this handle. Uses `CRITICAL_SECTION` at `sCollision+4`.

---

### `sCollision::Sbc`

Shape-Bound Container — wraps a `rCollision` resource with per-frame state.

Confirmed fields from `query_all_sbcs` and `check_moving_parts`:

| Offset | Field | Notes |
|--------|-------|-------|
| +8 | `mpResource` | `rCollision*` — the geometry/BVH resource |
| +16 | `mMoveXNum` | count of moving parts on X axis |
| +20 | `mMoveYNum` | |
| +24 | `mMoveZNum` | |
| +24 | `mGroupMask` | DWORD group membership mask |
| +28 | `mChannelBit` | byte — `1LL << mChannelBit` = channel filter |
| +36 | `mMovingPartsCount` | count entries in mMovingPartsArray |
| +44 | `mMovingPartsArray` | ptr to `sCollision::Sbc::Parts*[]` |
| +`PartsNum` offset | `PartsNum` | total parts count |
| `PartsArray` | ptr | `sCollision::Sbc::Parts*[]` — all parts |

World AABB of static geometry: 6 floats at `rCollision+120` (`v13[30..35]`).

---

### `sCollision::Sbc::Parts`

Per-part state for a dynamic (moving) collision shape.

| Offset | Field | Notes |
|--------|-------|-------|
| +4 | `mActive` | byte (0=inactive, skip entirely) |
| +5 | `mEnable` | byte (soft-disable: checked in checkAttr leaf) |
| +8 | `mCoord` | ptr to current 4×4 world matrix (MtMatrix) |
| +80 | `mCoordOld` | ptr to previous-frame 4×4 world matrix |
| +147 | `mMatResetSet` | byte — 0=static-style (needs mode==2), 1=moving-style (needs mode==1) |

---

### `rCollision` Resource

Resource file format for static/pre-built collision geometry.

| Field | Notes |
|-------|-------|
| `mpNode[]` | BVH node array (binary tree, see BVH node layout below) |
| `mpPartsInfo[]` | `rCollision::SbcInfo[]` — per-part AABB table |
| +88, +92 | Two DWORD identity keys used for deduplication in `count_unique_resources` |
| +120..+143 | World AABB of entire geometry (6 floats: minXYZ, maxXYZ) |
| +148 | Offset into mpPartsInfo (base for `mpPartsInfo[parts_idx]` in bvh_recurse: `+148 + 96*idx`) |

#### BVH Node Layout (~76 bytes per node)

Each node stores 2 child AABBs in 16-byte-aligned `MtVector4` pairs:

```
+0..+15   Child 0 AABB min  (x,y,z,_padding)  — MtVector4
+16..+31  Child 0 AABB max  (x,y,z,_padding)  — MtVector4
+32..+47  Child 1 AABB min  (x,y,z,_padding)  — MtVector4
+48..+63  Child 1 AABB max  (x,y,z,_padding)  — MtVector4
+64       Flags byte: bit6 = child0 is leaf, bit7 = child1 is leaf
+65       (reserved / padding)
+66..+67  Child 0 index (uint16) — node index if non-leaf, parts index if leaf
+68..+69  Child 1 index (uint16)
+70..+75  (padding to align)
```

---

### `rCollision::SbcInfo`

Per-part AABB entry in the rCollision resource (read by `moving_part_aabb_test`):

| Field | Notes |
|-------|-------|
| `vMaxThis` | MtVector3 — AABB max of this part |
| `vMinThis` | MtVector3 — AABB min of this part |

---

### `sCollision::ReqPacket` (partial)

The in-flight collision query descriptor passed through the traversal.

| Offset | Field | Notes |
|--------|-------|-------|
| `hit_pos.vectors[0]` | query AABB min (x,y,z) | |
| `hit_pos.vectors[1]` | query AABB max (x,y,z) | |
| `hit_pos.vectors[2]` | target part AABB min (filled by bvh_recurse from node) | |
| `hit_pos.vectors[3]` | target part AABB max | |
| `pfuncMain` | ptr | points into the ContactPacket (used as callback dispatch key) |

---

### Contact Packet (filled by `sCollision::fill_contact_packet`)

Stack-allocated struct built immediately before each narrowphase call:

| Offset | Content |
|--------|---------|
| +0 | `pSbc*` |
| +4 | param_3 (query sub-field) |
| +8 | param_4 (parts index) |
| +12 | param_5 |
| +20 | param_6 |
| +24, +28 | 0 (result accumulators) |
| +32 | enable byte |
| +33 | mat_reset byte |
| +48..+108 | target 4×4 world matrix (16 floats from `mCoord`) |
| +112..+172 | source 4×4 world matrix (16 floats from `mCoordOld`) |

---

### `uCollisionMgr` (gameplay-layer collision manager per actor)

Constructor at `uCollisionMgr::uCollisionMgr` (0x50B080). Inherits a unit base (`cUnit` / `MtObject`).

Key fields:

| Offset | Field | Notes |
|--------|-------|-------|
| +0 | vtable `uCollisionMgr::vftable` @ 0xBC78E0 | |
| (base) | `cUnit` fields | prev/next unit ptrs, delta_time |
| +25 | `mHitFlag` (byte) | set to 1 when a hit is detected this frame |
| +216 | actor ptr | used for `uActor::damagePreMessage` routing |
| +220 | `mpReportActor` | the owning actor — used for self-collision exclusion |
| `mpModel` | ptr | model ptr used in ignore list checks |
| `mppIgnoreModel[16]` | ignore model list | models this mgr never collides with |
| `mIgnoreModelNum` | count | |
| `mppCollisionGroup[31]` | 31 collision group slots | |
| `mCollisionGroupNum` | count | active groups |
| `mClearReq` | clear request flag | |
| `mMode` | byte | |
| `mPushType` | byte | |
| `mPushCap` | capsule params | p0=(50,0,0), p1=(150,0,1.0f) |
| `mDevilTriggerMode` | float | init 1.0f |
| `mCollisionMgrID` | int | −1 = unregistered |

#### VsAttr Defaults (combat interaction matrix)

Initialized in constructor to encode the full combat type table:

| Field | Default hex | Meaning |
|-------|-------------|---------|
| `mVsAttrPlAtk` | 0x11111100 | Player attack vs… |
| `mVsAttrPsAtk` | 0x11111100 | Player shot vs… |
| `mVsAttrEmAtk` | 0x11111111 | Enemy attack vs… |
| `mVsAttrEsAtk` | 0x11111111 | Enemy shot vs… |
| `mVsAttrEm2Atk` | 0x11111111 | Enemy2 attack vs… |
| `mVsAttrEs2Atk` | 0x11111111 | Enemy2 shot vs… |
| `mVsAttrPlDmg` | 0x44444400 | Player hurtbox |
| `mVsAttrPsDmg` | 0x44444400 | |
| `mVsAttrPlGrb` | 0x22 | Player grab |
| `mVsAttrPsGrb` | 0x22 | |
| `mVsAttrSetAtk` | 0x11 | Set-piece attack |
| `mVsAttrStgAtk` | 0x11 | Stage collision attack |
| `mVsAttrEmDmg` | 0x44444444 | Enemy hurtbox |
| (many more…) | | Push, grab, friendly-fire variants per type |

Attack kind → bitmask table (from `checkAttackObj`):
```
kind 0 → bit  0  (0x00000001)
kind 1 → bit  4  (0x00000010)
kind 2 → bit  8  (0x00000100)
kind 3 → bit 12  (0x00001000)
kind 4 → bit 16  (0x00010000)
kind 5 → bit 20  (0x00100000)
kind 6 → bit 24  (0x01000000)
kind 7 → bit 28  (0x10000000)
```

Each attack type maps to a nibble in the 32-bit `mVsAttr` field.

---

### `cCollisionGroup`

Per-shape group object. Key fields observed in `checkAttackObj`:

| Field | Notes |
|-------|-------|
| `mpCollisionMgr` | ptr to owning `uCollisionMgr` |
| `mpNext[1]` | next in linked list (2-slot next array — slot 0 = same-type list?) |
| `mClear` | bool — this group is being cleared |
| `mClearReq` | DWORD — clear request token (matched against other group's for paired clear) |
| `mKind` | byte — attack shape kind (0–7, indexes into kind→bit table above) |
| `mVsAttr` | DWORD — bitmask of damage types this group accepts |

---

## Full Collision Pipeline

```
sCollision::findIntersection(a1)           [0x95B370]
  │
  ├─ count_unique_resources(a1)            [0x948580]  — deduplicate active rCollision geometries
  ├─ init_query_packet(...)                [0x940710]  — build MtAABB query descriptor
  │
  └─ query_all_sbcs(a1, query_aabb, ...)  [0x95E350]  — outer loop
       │
       │  For each Sbc in mSbcArray:
       │    • filter: group mask (Sbc+24) & query group
       │    • filter: channel bit (1LL << Sbc+28)
       │    • skip if no geometry (Sbc+8 = nullptr)
       │    • skip if AABB miss AND no moving parts
       │
       ├─ if byte_E559BA (optimized mode):
       │    ├─ enumSomeContacts(...)       [0x95EDF0]  — iterative BVH with explicit stack
       │    └─ check_moving_parts(...)     [0x95F050]  — moving parts path
       │         └─ moving_part_aabb_test  [0x95E5E0]  — SbcInfo AABB lookup
       │               └─ check_part_narrow [0x95F0C0] — per-part narrowphase
       │
       └─ else (non-optimized):
            └─ bvh_recurse(...)           [0x95EBA0]  — recursive BVH descent
                 └─ (leaf node hits)

  ┌─ Common leaf path ──────────────────────────────────────────────
  │   fill_contact_packet(...)            [0x940270]  — populate ContactPacket w/ matrices
  │   → call shape callback at param+68                — geometry test (capsule/sphere/etc.)
  │   → AABB overlap check
  │   → checkAttr(...)                   [0x95F4C0]   — attr/triangle filter + hit callback
  └─────────────────────────────────────────────────────────────────
```

---

## `enumSomeContacts` vs `bvh_recurse`

| | `enumSomeContacts` | `bvh_recurse` |
|-|-------------------|--------------|
| Style | Iterative (explicit work stack) | Recursive |
| Guard | `byte_E559BA` must be non-zero | fallback when flag is zero |
| Part filter | checks `mActive` AND `mEnable` on leaf | uses `bit6/7` in node flags byte |
| Moving parts | handled separately by `check_moving_parts` | inlined (checks mActive on leaf directly) |

`byte_E559BA` at `0xE559BA` is a runtime mode flag — likely set during scene init. When 0 the legacy recursive traversal runs.

---

## `sCollision::checkAttr` Internals (0x95F4C0)

Leaf-level filter applied after AABB and before the hit callback:

1. Reads parts info base: `v7[36]` (= collision manager + 144), stride-80 array  
2. Outer work stack loop (starts with initial child index from caller):  
   - Inner loop: 2 iterations per node (both BVH children)  
   - Per child: AABB vs `ReqPacket->hit_pos` (min/max vectors)  
   - Group mask check: `child_flags & dword_E16B78[4*i]`  
   - **On match**: populate `a2[4/6/7]` (hit indices), check `param_4+80 & 0x3FFFFF00` vs `node+8` group id, invoke callback at `param_4+64`  
   - **On sub-tree child** (v17 != 0, not a leaf match): push index onto work stack  
3. Continue until work stack empty  
4. Returns OR-accumulation of all callback results (non-zero = hit)

---

## Gameplay Layer (`sCollisionGame`)

### `sCollisionGame::checkAttackObj` (0x47C300)

Called once per frame per attacker. Walks the linked list of `cCollisionGroup` objects for the victim.

**Filter chain (any match → skip this pair):**
1. Same group pointer (self)
2. Same owning `uCollisionMgr`
3. Attacker's `mpReportActor` == victim's `mpReportActor` (same actor, self-collision)
4. Attacker actor in victim's ignore list (`mppIgnoreModel[]`)
5. Victim actor in attacker's ignore list
6. Either side has `mClearReq` set, and they match each other
7. `local_20[mKind] & mVsAttr == 0` (attack type not accepted)

**On match:**
1. `sCollisionGame::checkGroup_` (0x47D9A0) — SIMD geometry test
2. If hit: `uCollisionMgr+25 = 1` (mHitFlag), route to `uActor::damagePreMessage`

### `sCollisionGame::checkGroup_` (0x47D9A0)

Heavy SSE/XMM function (~61 KB decompile). Performs the actual hitbox shape tests — likely capsule-vs-capsule, sphere-vs-capsule etc. Not fully decompiled.

---

## Key Addresses

| Symbol | Address |
|--------|---------|
| `sCollision::findIntersection` | `0x95B370` |
| `sCollision::registResource` | `0x946750` |
| `sCollision::query_all_sbcs` | `0x95E350` |
| `sCollision::enumSomeContacts` | `0x95EDF0` |
| `sCollision::bvh_recurse` | `0x95EBA0` |
| `sCollision::check_moving_parts` | `0x95F050` |
| `sCollision::moving_part_aabb_test` | `0x95E5E0` |
| `sCollision::check_part_narrow` | `0x95F0C0` |
| `sCollision::checkAttr` | `0x95F4C0` |
| `sCollision::fill_contact_packet` | `0x940270` |
| `sCollision::init_query_packet` | `0x940710` |
| `sCollision::count_unique_resources` | `0x948580` |
| `sCollisionGame::checkAttackObj` | `0x47C300` |
| `sCollisionGame::checkGroup_` | `0x47D9A0` |
| `uCollisionMgr::uCollisionMgr` | `0x50B080` |
| `uCollisionMgr::init` | `0x50BAA0` |
| `uCollisionMgr::move` | `0x50CC40` |
| `uCollisionMgr::vftable` | `0xBC78E0` |
| `MtDTI_uCollisionMgr` | `0xE58698` |
| `byte_E559BA` | `0xE559BA` (BVH mode flag: 0=recursive, 1=iterative) |
| `dword_E16B78` | `0xE16B78` (group mask table used in checkAttr) |

---

## Multiplayer Implications

- `sCollision` is a singleton — all collision passes through one global BVH. Adding a second player does not require structural changes here (the BVH is shared world geometry, and per-actor `sCollision::Sbc` objects are registered independently).
- `sCollisionGame::checkAttackObj` reads `sMediator::mpPlayer` indirectly through `mpReportActor` — the self-collision filter compares report actors. With two players, this already works if each player registers its own `uCollisionMgr` with its own `mpReportActor`.
- `uCollisionMgr` is the real per-player surface. Each player already has its own instance. The gameplay VsAttr defaults are symmetric (PlAtk can hit EmDmg; EmAtk can hit PlDmg) so N players do not break the combat interaction matrix.
- The **ignore list** (`mppIgnoreModel[16]`) caps at 16 models — sufficient for single-player friendlies, but could overflow in co-op if team members + their sub-objects all need ignoring.
