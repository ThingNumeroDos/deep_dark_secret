# uDevil4Model / uModel — Skin Mesh Pipeline

Target: `DevilMayCry4_DX9.exe` (DX9 build, IDB at port 13337).
Names cross-checked against the Special Edition leaked PDB (port 13338) — **offsets differ
between the two builds**, so every offset below was re-derived from DX9 disassembly.

## TL;DR — the one thing that was mis-modelled

`uModel::SkinRemap` (uModel+0x17C, `uint[64]`) is **not** a bone-index remap table, despite
the name. It is an array of **packed shader constant-buffer handles**, one per *skin-mesh
envelope*, allocated out of `sShader`'s bitmap allocator. `SkinRemapNum` (+0x27C) is the
envelope count, copied verbatim from `rModel::mEnvelopeNum`.

The actual bone→matrix indirection lives in `rModel::mEnvelopeInfo[i].mJointMap[k]`, a byte
array inside the resource, not in the `uModel` instance at all.

---

## Class placement

`uDevil4Model` (3744 B) sits between `uModel` and `uActor`:

```
MtObject → cUnit → uCoord → uModel → uDevil4Model → uActor → uPlayer / uEnemy
```

`uDevil4Model` itself owns **no** skin-mesh state. Its constructor (`0x5226F0`) only sets up
render/material/clip concerns: `mWorkRate`, `mFreeze`, camera transparency (`mCameraSphere`,
`mAlphaMin/Max`, `mDistanceMin/Max`), the clip plane pair, `mMaterialType`, `mZWrite`,
`mZThrough`, `mAlphaRef`, and the handler arrays (`mppMaterialHandlerArray`,
`mppJointHandlerArray`, `mppPartsHandlerArray`). It calls `uModel::setBlendNum(this, 1)`.

Everything skinning-related is inherited from `uModel`. So "uDevil4Model skin mesh" is, in
practice, the `uModel` skinning path as reached through a `uDevil4Model` instance.

## Relevant `uModel` fields (DX9 offsets)

| Offset | Field | Notes |
|--------|-------|-------|
| +0x0A0 | `mWmat` | world matrix (from `uCoord`), uploaded every frame |
| +0x0F0 | `mPrevWmat` | previous frame world matrix — motion blur |
| +0x17C | `SkinRemap[64]` | **shader constant handles**, one per envelope; `-1` = unallocated |
| +0x27C | `SkinRemapNum` | envelope count (= `rModel::mEnvelopeNum`) |
| +0x2A8 | `Render.ukn` | refresh countdown, set to 2 by `setModel` |
| +0x2B0 | `mBoundingSphere` | copied from `rModel::mBoundingSphere` |
| +0x2C0 | `mBoundingBox` | drives position dequantisation constants |
| +0x2E0 | `mJointNum` | **stored as a byte** (`this->mJointNum = (uint8)mJointNum`) — caps at 255 |
| +0x2E4 | `mpJoint` | `uModel::Joint*`, stride **144** — animated bone matrices |
| +0x2E8 | `mJointTable` | points into `rModel+0x120`; `&unk_B99EA0` when no model |
| +0xA30 | `mpRModel` | the backing resource |

## `rModel` fields recovered (DX9 offsets — SE differs by +8 from 0x68 on)

Confirmed from `setModel` `0x9E6EB2-0x9E6EB8` and `uploadSkinningConstants` `0x9F80DB`.
These were previously `undefined` bytes in the IDB and are now declared:

| DX9 offset | Field | SE offset | Type |
|-----------|-------|-----------|------|
| +0x60 | `mJointInfo` | +0x68 | `JOINT_INFO*` (stride 24) |
| +0x64 | `mJointNum` | +0x6C | `uint` |
| +0x68 | `mLmat` | +0x70 | `MtMatrix*` — local/bind pose |
| +0x6C | `mImat` | +0x74 | `MtMatrix*` — **inverse bind pose**, stride 64 |
| +0x80 | `mEnvelopeInfo` | +0x84 (`mBoundaryInfo`) | envelope array, stride **0x24** |
| +0x84 | `mEnvelopeNum` | +0x88 (`mEnvelopeNum`) | `uint` |
| +0xF8 | (light group) | — | copied to `uModel::mLightGroup` |
| +0x120 | joint table | +0x110 `mJointTable` | `uint8[256]` |

> SE's PDB labels the +0x80-equivalent slot `mBoundaryInfo`/`BOUNDARY_INFO*` (144 B stride).
> In the DX9 build the array at +0x80 is walked at **stride 0x24 (36 B)** by both `setModel`
> and `uploadSkinningConstants`, and its first dword is consumed as an allocation size in
> bytes. That is an envelope descriptor, not a 144-byte boundary record. Declared locally as
> `rModel_ENVELOPE_INFO { uint mConstantSize; uint mJointCount; uint8 mJointMap[28]; }`.
> The `mJointMap` extent is inferred from the 36-byte stride and the byte-indexed read at
> `0x9F8177`; the exact split of the trailing bytes is not yet pinned down.

## Setup path — `uModel::setModel` (`0x9E6D70`)

1. **Teardown.** Releases the old `rModel`; for each existing `SkinRemap[i]` calls
   `sShader::freeConstantHandle` and writes back `-1`; frees per-blend joint work buffers;
   frees `mpJoint`. Sets `Render.ukn = 2`.
2. **Bind.** Ref-counts the new `rModel` under the `sDevil4Resource` critical section.
3. **Joint array.** Allocates `144 * mJointNum + 16` from `UnitAllocator` (32-byte aligned),
   stores the count in the 16-byte header, and runs the `uModel::Joint` constructor over each
   entry. Per-blend `96 * mJointNum` work buffers are allocated and zeroed.
4. **Envelope handles.** For each of `mEnvelopeNum` envelopes:
   ```
   SkinRemap[i] = sShader::allocConstantHandle(mEnvelopeInfo[i].mConstantSize, sShader::mpInstance)
   ```
   Loop at `0x9E7032`, envelope pointer advanced by `0x24` per iteration (`add esi, 24h`),
   handle pointer by 4 (`add edi, 4`).
5. **Bone init.** Copies `JOINT_INFO` into each `uModel::Joint` (`mNo`, `mParentIndex`,
   `mSymmetryIndex`, `mOffset`, `mLength`), copies the bind matrix into `Joint::mWmat`,
   and converts that matrix to `Joint::mQuat` via the standard branchless
   largest-diagonal-element quaternion extraction (trace > 0 fast path at `0x9E71A9`,
   three-way largest-axis fallback at `0x9E7212`). `mScale` is set to `MtVector3::One`.
6. Copies the bounding sphere and calls `uModel::setMaterials`.

If joint allocation fails the model is released again and no skinning state is built.

## Per-frame path — `uModel::uploadSkinningConstants` (`0x9F7B60`)

The pre-existing header comment on this function was wrong in two ways, now corrected in the
IDB: the branch is on **`mJointNum`**, not a "skinning enabled flag" at +0x2E0, and the bone
loop iterates **envelopes**, not bones.

### Branch

```
mJointNum == 0 → rigid   : uploads only mWmat + mPrevWmat; dequant constants come
                           pre-baked from rModel+0x100 / +0x110
mJointNum != 0 → skinned : full path below
```

### Constants uploaded (each dirty-checked against the bound value first)

| Value | Slot global |
|-------|-------------|
| AABB half-extent × 0.55 | `dword_E556D4` |
| reciprocal half-extent, `w = 1.0` | `dword_E555AC` |
| AABB center | `dword_E5551C` |
| `mWmat` (64 B) | `dword_E55538` |
| `mPrevWmat` (64 B) | `dword_E5552C` |

The 0.55 fudge (vs. a true 0.5) pads the dequantisation box slightly so vertices at the
extremes don't clip. Each upload bump-allocates from the scene context ring at `ctx[2732]`
(16-byte aligned downward) and sets dirty bit `0x20000000` in `ctx[2729]`.

### Bone bake loop

```c
for (i = 0; i < this->SkinRemapNum; i++) {
    dst = sShader::resolveConstantHandle(this->SkinRemap[i]);
    if (!dst) continue;                       // already baked this frame
    env = &mpRModel->mEnvelopeInfo[i];        // stride 0x24
    for (k = 0; k < env->mJointCount; k++) {
        j = env->mJointMap[k];                // byte index, at env+4+k
        dst[k] = to3x4( mpRModel->mImat[j] * this->mpJoint[j].mWmat );
    }
    if (this->Render.ukn) --this->Render.ukn;
}
```

Strides verified in disassembly at `0x9F817C`:
- `lea ecx,[edx+edx*8]; shl ecx,4` → `j * 144` = `sizeof(uModel::Joint)`, `+0x50` reaches `mWmat`
- `shl edx,6` → `j * 64` = `sizeof(MtMatrix)`, indexing `mImat`

**Multiply order:** at `0x9F81AB-0x9F81E4` the first output element dots a *row* of `mImat`
(`edx+0/4/8/0xC`) against a *column* of the bone matrix (`ecx+0x50/0x60/0x70/0x80`, stride
0x10). The inverse bind pose is therefore the **left** operand: the composite maps bind-space
→ world-space, which is the conventional skinning matrix.

Only **3 rows (12 floats)** are stored per bone, written starting at `dst+24`; the shader
supplies the implicit fourth column. The 24-byte header of each block is left untouched.

## Handle encoding — `sShader` bitmap allocator

Renamed in the IDB:

| Address | Name |
|---------|------|
| `0x8FEC80` | `sShader::allocConstantHandle` |
| `0x8FEAA0` | `sShader::resolveConstantHandle` |
| `0x8FEC10` | `sShader::freeConstantHandle` |

**Allocation** — `mEnvelope[512]`, 21 usable bits per word, one bit per float4 register:

```
n21 = (size + 3) >> 2                      // size in float4 registers
if (n21 == 22 && size <= 0x55) n21 = 21    // lets a 0x54-byte block fit one word
scan 512 words for n21 contiguous free bits, set them
handle = (word & 0xFFF) | ((n21 << 12 | (bitpos & 0xFFF)) << 12)
```

| Bits | Meaning |
|------|---------|
| 0–11 | word index (0–511) |
| 12–23 | bit position within word (0–20) |
| 24–31 | `n21` — size in float4 registers |

Returns `-1` on exhaustion; `-1` is the sentinel `setModel` writes into freed `SkinRemap`
slots.

**Resolution** is a test-and-set, which is the mechanism behind the per-envelope skip:

```
word = handle & 0xFFF;  bitpos = (handle >> 12) & 0xFFF
if (dirty[word] & (1 << bitpos)) return 0;   // already uploaded this frame
dirty[word] |= (1 << bitpos)
return store + 192 * bitpos + word * this[26724]
```

The first caller in a frame bakes the matrices; any later pass over the same envelope gets
`0` and skips the work. `Render.ukn` counting down from 2 after `setModel` forces both halves
of the double-buffered constant store to be refilled following a model swap.

**Free** uses a different operand order from alloc — mask is
`((1 << (handle >> 24)) - 1) << (handle >> 12)`, taking size from the high byte. No-op on `-1`.

## Notes / open items

- `rModel_ENVELOPE_INFO.mJointMap`'s exact length within the 36-byte stride is inferred, not
  proven; bytes beyond the joint list may hold other per-envelope data.
- The DX9 `mBoundaryInfo` equivalent (SE +0x84) was not located; the DX9 +0x80 slot is the
  envelope array, so boundary records live elsewhere or are absent in this build.
- `mJointNum` narrowing to a byte at `0x9E7010` means models with >255 joints would silently
  truncate. Not obviously reachable, but worth noting.
- Multiplayer relevance: all skin-mesh state is per-`uModel`-instance (`SkinRemap`, `mpJoint`)
  and the `sShader` allocator is global but handle-based, so N players each get their own
  envelope handles. No `sMediator` coupling was found in this path.
