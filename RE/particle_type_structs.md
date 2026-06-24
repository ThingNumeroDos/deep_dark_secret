# uEffectVFR Particle — Per-Type Node Struct Layouts

Reverse-engineering report on the per-particle node ("`uEffectVFR::Particle`") struct as interpreted by each render type. Scope: the common subset — **Billboard (0), SizeBillboard (17), Polyline (1/12), Polygon (2), Line (4/14), Model (5)** — plus the second pass — **Texline (3/13), PrimModel (6), LensFlare (7), MassBillboard (8), Filter (9), Light (10), Hit (11), PolygonStrip (15)** — and the final type **LiteBillboard (16)**. **All 18 render types (0–17) are now reversed.**

Each type is derived from BOTH its `initParticle<Type>` (spawn-time writes) AND the per-particle move sub its `moveParticleLoop_*` delegates to (per-frame writes), mapped by **absolute offset** (`0x40*n + member` from the decompiler's mislabeled `_EDI[n].field` expressions — the names are wrong, the offsets are right).

---

## Node model (shared)

The particle node is **not** a fixed 64-byte struct. `uEffectVFR::Generator::openParticle` (0x9DF2D0) `memset`s `pGen->mParticleSize` bytes (a runtime word at `Generator+0x14`, configured per render type at generator setup). So **each render type has its own node size and body layout**, sharing only a common header.

### Base header (`uEffectVFR::Particle`, first 0x40 bytes — shared by all types)

| Offset | Type | Name | Notes |
|--------|------|------|-------|
| +0x00 | `Particle*` | mpPrev | doubly-linked list prev (stock/move list) |
| +0x04 | `Particle*` | mpNext | list next |
| +0x08 | `u16` | mSetNo | set/slot number (preserved across openParticle memset) |
| +0x0A | `u8` | mAlive | 1=alive; cleared to 0 to retire (move sub sets `i+10`=0) |
| +0x0B | `u8` | mParity | double-buffer toggle (`v7`); flipped every frame in the move-loop |
| +0x0C | `u32` | mAge | frame counter, incremented each tick |
| +0x10 | `u32` | mSerial | = generator mSetParticleTotal / mSetFrameTotal at spawn |
| +0x14 | `u16` | mStatus | **base** status/flags word (channel-enable bits set by init) |
| +0x18 | `float` | mScale | base scale |
| +0x1C | `float` | mParam1c | (type-dependent; billboard writes a keyframe scalar) |
| +0x20 | `MtVector3[2]` | mPos | base position pair (rarely used directly by render types) |

**Status flag bits** (`mStatus`, +0x14, and the per-slot status at +0x54): set by `init` to mark which keyframe/animation channels are active, consumed by the move sub. Observed: `0x01`=scale-anim, `0x04`=intensity-channel, `0x08`=src-color channel, `0x20`=primary-keyframe, `0x40`=life-color channel, `0x1000`=extra-scale channel, `0x2000`=tail/extra channel.

**IDB sync (2026-06-03):** the base-header field names above are now committed to the `uEffectVFR::Particle` IDB type (was: `mpPrev/mpNext` + a run of `member_0x*`). The allocator `uEffectVFR::Generator::init` (0x9DECD0) was re-read this session and independently corroborates the skeleton — it stamps the +0x8 word (`mSetNo`, free-list sequence index) and zero-inits the +0xA byte (`mAlive`=0 for stock nodes) while threading every node through `mpPrev/mpNext`. The spawn/per-frame fields (`mParity`@0xB, `mAge`@0xC, `mSerial`@0x10, `mParam1c`@0x1C) keep their move-sub-derived names. Also retyped the Generator's four list head/tail pointers (`mpMoveTop/BotParticle`, `mpStockTop/BotParticle`) from `uint` → `uEffectVFR::Particle*`. Base size held at exactly 0x40 so the 15 embedding subclasses did not shift.

### Double-buffering (current/previous frame)

Several animated scalar channels are **double-buffered** by `mParity` (+0x0B, toggled each frame in the move-loop). The move sub reads the previous frame's value via `4*(parity^1)+off` and writes the current via `4*parity+off` — i.e. a **stride of 4 (a float pair)** at specific channel offsets, NOT a wholesale block split. (Correction: the `_EDI[1]`/`_EDI[2]` 0x40/0x80 blocks in the init are **not** two mirror slots — they hold different categories of data (block A = color/material, block B = intensity/size); the actual mirror pairs are the float-pairs at e.g. base+0x18/+0x1c, +0x58/+0x5c style channels selected by `4*parity`.) Exact paired offsets are noted per type below.

---

## Type 0 — Billboard  (`initParticleBillboard` 0x977E50 + move `sub_98E000`)

`mParticleType == 0`. The baseline render type; all other billboard variants extend this shape. Node body spans ~0xA8 bytes (plus slot-1 mirror).

| Offset | Type | Field (inferred) | Set by | Notes |
|--------|------|------------------|--------|-------|
| +0x18 | float | mScale | init | base scale (= scale2 * generator mParticleScale) |
| +0x1C | float | mParam1c | init | keyframe scale scalar |
| +0x40 | u32 | mColorA0 | init | render/material color block A (links slot repurposed) |
| +0x44 | u32 | mColorA1 | init | |
| +0x48 | u32 | mLifeColor | init | from calcLifeColor |
| +0x4C | u32 | mLifeColor2 | init | |
| +0x54 | u16 | mSlotStatus | init/move | per-slot channel-enable flags (mirror of base mStatus) |
| +0x58 | float | mSlotScale | init | |
| +0x5C | float | mSlot1c | init | |
| +0x60 | float | mIntensityVel | init/move | intensity velocity (channel 0x04) |
| +0x64 | float | mWScaleY | init | world-scale Y applied to size |
| +0x68 | float | mScale2 | init | sampled base scale |
| +0x70 | u16+u16 | mAnimFlag / mRandTexIdx | init | packed: anim flag (low), random texture frame index (high) |
| +0x74 | u16+u16 | mTexFrame / mTexFrameMax | init | current/max texture frame |
| +0x78 | float | mKeyframeScale | init | |
| +0x7C | float | mIntensity | init | |
| +0x80 | u32 | mPrimMaterial | init | primitive material id (from calcPrimMaterial) |
| +0x84 | u32 | mPrimMaterial2 | init | |
| +0x88 | u32 | mSrcColor | init/move | source color (channel 0x08 = calcKeyframeColor) |
| +0x90 | float | mIntensity2 | init/move | intensity (clamped 0..127; channel 0x04) |
| +0x98 | float | mScaleVel | init | scale velocity (channel 0x01) |
| +0x9C | float | mTimer | init/move | |
| +0xA0 | float | mScaleVel2 | init/move | (channel 0x2000 tail) |
| +0xA4 | float | mFadeVel | init/move | fade/intensity velocity (channel 0x1000, clamped 0..15.9375) |

Move sub (`sub_98E000`) per frame: advances texture frame, evaluates active keyframe channels (status bits), integrates the velocity channels into the current double-buffer slot (`4*parity + {0x18,0x48,...}`), retires the particle (`mAlive=0`) when a channel signals end-of-life, and on `Generator.mFlags & 0xF00` calls the owner vtable[+0xA8] (slot 42) world-transform hook.

---

**IDA struct:** `uEffectVFR::PtclBillboard` (declared, size 0xA8). Applied to `initParticleBillboard` (0x977E60) and verified — the decompile resolves cleanly to named fields. Several fields are double-buffer mirrors (e.g. `mColorCur`/`mColorCur2`, `mLifeColor`/`mLifeColor2`, `mIntensity`/`mIntensityMirror`).

> **Address note:** `initParticleBillboard` is at **0x977E60**; 0x977E50 is the *preceding* function `sub_9774B0` (a rotation/quaternion transform helper shared by the move subs). Don't confuse them.

---

## Type 17 — SizeBillboard  (`initParticleSizeBillboard` 0x97F4E0)  — IDA struct `uEffectVFR::PtclSizeBillboard` (0xF4)

`mParticleType == 17`. Billboard variant with **two independent size channels** (width & height) that scale separately and can each be keyframe-animated. Confirmed = SE `cParticleGeneratorSizeBillboard`. Largest billboard node (~0xF0 bytes). Verified by applying the struct to the init and re-decompiling.

Layout (key fields; declared as `uEffectVFR::PtclSizeBillboard`):

| Offset | Field | Notes |
|--------|-------|-------|
| +0x00 | base | shared header |
| +0x40 | mColorCur | current color |
| +0x50 | mTimer | |
| +0x54 | mSlotStatus | per-slot flags |
| +0x58 | mSlotScale | |
| +0x60..0x7F | velocity dir triple + mirror (`_gap60`) | `p_velX` direction written here, double-buffered |
| +0x80 | mPrimMaterial / +0x84 mPrimMaterial2 | |
| +0x88 | mSrcColor | |
| +0x90 | mIntensity / +0x94 mIntensityMirror | |
| +0x9C | mScaleVel | channel 0x01 |
| +0xA0 | mScaleSampled / +0xA4 mScaleSampled2 | |
| +0xA8 | mAnimFlag / +0xAA mRandTexIdx | |
| +0xAC | mTexFrame / +0xAE mTexFrameMax | |
| +0xB0 | mTexFrame2 / +0xB2 mTexFrame2Max | second texture-anim channel |
| +0xB4 | mKeyframeScale | |
| +0xBC | mSizeW | **width** channel base |
| +0xC4 | mSizeWVel | width velocity |
| +0xC8 | mSizeColor / +0xCC mSizeColorMirror | |
| +0xD0 | mSizeH | **height** channel base |
| +0xD8 | mSizeHVel | height velocity (status 0x1000/0x4000) |
| +0xE0 | mSizeChanA / +0xE4 mSizeChanB / +0xE8 mSizeChanC / +0xEC mSizeChanD | extra per-size sub-channels (vector keyframe); `+0xEE` word holds mPtclFlagBase |

vs Billboard: same base render/color/intensity skeleton, but adds the width (`mSizeW*`) and height (`mSizeH*`) channel groups at +0xBC..+0xEC, each with its own keyframe descriptor (`mpParticleParam+118/+119`) and status bits, plus a 2nd texture-anim channel. Final per-frame hook uses owner vtable **+0xA8** (slot 42) — the **same** hook as plain Billboard (an earlier draft wrongly listed this as +0x168 / "+0x42 vs Billboard"; both types call the identical slot-42 / +0xA8 hook).

---

## Type 4/14 — Line  (`initParticleLine` 0x97A990, move `sub_98F5D0`)  — IDA struct `uEffectVFR::PtclLine` (0x80)

`mParticleType == 4` or `14`. A camera-facing line/quad strip. Smallest of the geometry types. **Fully named and verified** (all init fields bind cleanly).

| Offset | Field | Notes |
|--------|-------|-------|
| +0x00 | base | shared header (mScale @0x18 is the current scale; double-buffered via `2*parity`) |
| +0x40 | mColorCur / +0x44 mColorCur2 | current vertex color (double-buffer pair) |
| +0x48 | mLifeColor / +0x4C mLifeColorMirror | life-curve color |
| +0x50.._gap50 (0x10) | prim-attribute (+0x58) + intensity-scale pair (+0x50/+0x54) | |
| +0x60 | mSrcColor / +0x64 mSrcColorMirror | source color (channel 0x08) |
| +0x68 | mSrcColorAlt / +0x6C mSrcColorAltMirror | 2nd src color (channel 0x10) |
| +0x70 | mIntensity / +0x74 mIntensityB | intensity (clamped 0..127; channel 0x04) |
| +0x78 | mScaleVel | scale velocity (channel 0x01 / 0x40) |

Tail: a 6-way size/UV dispatch on `mpParticleParam+80` (`sub_9803F0/980620/980C40/980EC0/981050/981530`) — shared with Polyline.

---

## Type 1/12 — Polyline  (`initParticlePolyline` 0x9786C0, move `sub_98E3E0`)  — IDA struct `uEffectVFR::PtclPolyline` (0x100)

`mParticleType == 1` or `12`. A multi-segment ribbon. Node body uses three 0x40 blocks (`base` + render + strip-state). **Size & block structure verified**; per-field naming of the dense render block deferred (heavy double-buffering — see method note).

| Offset | Block | Notes |
|--------|-------|-------|
| +0x00 | base | header; also writes `pos2X/Y/Z/posW` base-region fields |
| +0x40..0x53 | base-region pos writes (`_gap40`) | |
| +0x54..0xBF | render/color/scale block (`_ext54`, raw `pad_54[N]`) | color + life-color + src-color channels, scale/intensity pairs, anim-flag/tex words near +0x54..+0x5C; double-buffered |
| +0xC0..0xFF | strip-dispatch + culling state (`_gapC0`) | per-segment + the 6-way size/UV dispatch output |

---

## Type 2 — Polygon  (`initParticlePolygon` 0x9792F0, move `sub_98EAA0`)  — IDA struct `uEffectVFR::PtclPolygon` (0xF4)

`mParticleType == 2`. A textured quad. The **largest** geometry node (~0xF0). **Size & gross structure verified; a few fields confidently named.** Per-field naming of the 0x8C..0xFF channel block deferred — it's the densest double-buffered region (color/intensity/scale/size keyframe channels + mirrors + a vector keyframe), and confident boundaries aren't supportable from the init alone.

| Offset | Field | Notes |
|--------|-------|-------|
| +0x00 | base | header |
| +0x40..0x7F | render block A (`_gap40`) | raw `LifeRate+64..`: color/scale/pos, double-buffered |
| +0x80 | mPrimMaterial / +0x84 mPrimMaterial2 | calcPrimMaterial output |
| +0x88 | mAnimFlag (low) / +0x8A mRandTexIdx (high) | packed anim-flag + random-texture index |
| +0x8C..0xFF | dense channel block (`_gap8c`) | tex-frame words, intensity/scale/size keyframe channels + mirrors, vector keyframe (`LifeRate+140..238`). Not yet per-field named. |

---

## Type 5 — Model  (`initParticleModel` **0x97AF80**, move `sub_98F9C0`)  — IDA struct `uEffectVFR::PtclModel` (0x140)

`mParticleType == 5`. A full 3D model instance per particle — the largest node overall (~0x140), with four 0x40 blocks. Carries model-specific **anim-frame** and **UV-scroll** channels the sprite types lack. **Size & block structure verified; the model-specific tail fields named.**

| Offset | Field | Notes |
|--------|-------|-------|
| +0x00 | base | header |
| +0x40..0x7F | transform/scale block (`_gap40`) | i[1] — per-instance matrix rows / scale |
| +0x80..0xBF | color/intensity block (`_gap80`) | i[2] |
| +0xC0 | mSrcColor / +0xC4 mSrcColorB | src color + prim-attribute |
| +0xC8 | mIntensity | intensity/color channel (status 0x08) |
| +0xCC | mParamCc | keyframe-color scalar |
| +0xD0..0xDB | gap | intensity-vel + **the per-frame anim counter the move sub advances at i[3].mScale = 0xD8** (left gapped; init doesn't write it directly) |
| +0xDC | mScaleD | scale-distance / LOD param (status 0x3000) |
| +0xE0 | mScaleVel | scale velocity channel (status 0x01/0x40) |
| +0xE4/+0xE8/+0xEC | mDirX/Y/Z | dir/offset vector (keyframe-vector, status 0x80) |
| +0xF0/+0xF4/+0xF8 | mUVChanX/Y/Z | uv/rotation channel (keyframe-vector, status 0x200) |
| +0xFC..0x13F | i[4] block (`_gapfc`) | anim-flag bits @+0xFC (masked `0xFFFFFFF`; rotation/scroll enable bits 0x10000000/0x20000000/0x40000000/0x80000000), uv-scroll scalars @+0x100/+0x104/+0x108 (status 0x4000/0x8000), mPtclFlagBase @+0x108 |

> **Note:** the move sub `sub_98F9C0` advances a model anim-frame counter at `i[3].mScale` = **0xD8** (wrapped/clamped per status 0x2000/0x1000) — that field lives in the `_gapd0` gap because the init doesn't seed it directly. An earlier draft mislabeled 0xE0 as "mAnimFrame"; 0xE0 is the scale-velocity channel. Corrected.

---

## Type 3/13 — Texline  (init 0x97A0B0, move sub_98F0C0)  — IDA struct `uEffectVFR::PtclTexline` (0x98)

`mParticleType == 3` or `13`. A textured line/ribbon. The init renders via the **`uEffectVFR::tclData` view** (`pParticle->pad_54[N]` = absolute `0x54+N`), and shares Polyline/Line's 6-way size/UV dispatch tail (`sub_9803F0/980620/980C40/980EC0/981050/981530`). Base-region pos fields named; the 0x54..0x97 render block gapped (`_render54`) — densest double-buffered region (color/material/intensity/scale keyframe channels + mirrors). **Size + base-region structure verified; per-field naming of the render block deferred.**

| Offset | Field | Notes |
|--------|-------|-------|
| +0x00 | base | header (base.mStatus channel bits OR'd) |
| +0x40 | mPosW | base-region posW (prim attr from sub_980340) |
| +0x44 | mPosWMirror | tclData pad_44 (posW copy / prim attr 2) |
| +0x48 | mPos2X | secondary pos / prim attr |
| +0x4C | mPos2Y | |
| +0x50 | mPos2Z | base scale sample |
| +0x54..0x97 | `_render54` (gap) | scale@0x54, scale mirrors @0x58/0x5C, packed anim-flag @0x60, tex-frame cur/max @0x64/0x66, keyframe scale @0x68/0x6C, calcPrimMaterial @0x70/0x74, src color @0x78/0x7C, intensity (0..127, status 0x04) @0x88, scale velocity (status 0x01/0x40) @0x90 |

---

## Type 6 — PrimModel  (init 0x97BE70, move sub_990310)  — IDA struct `uEffectVFR::PtclPrimModel` (0x144)

`mParticleType == 6`. A primitive-model instance — the PrimModel analog of Model (type 5): a transform matrix block, anim/tex words, color/intensity/scale keyframe channels, a dir keyframe-vector, and UV-scroll scalars. Largest node after Model. **Size & gross structure verified; the clear scalar/color channels named, the dense double-buffered regions gapped.**

| Offset | Field | Notes |
|--------|-------|-------|
| +0x00 | base | header |
| +0x40 | mMatRow0[4] / +0x50 mMatRow1[4] | transform block A (calcParticleMatrix source/scale) |
| +0x60..0x9F | `_gap60` / mAnimFlag@0xA0 / `_gapA4` | velocity/scale-vel + dir/UV float blocks (double-buffered); packed anim flag @0xA0 |
| +0xC0 | mTexAnimWord | LOWORD=anim flag+param, HIWORD=random tex index |
| +0xC4 | mTexFrameWord | LOWORD=cur frame, HIWORD=max frame |
| +0xC8..0xDF | keyframe scale floats (mKeyScaleZ/Pad/0/1, mScaleCur/Mir, `_gapE0`) | |
| +0xF0 | mPrimMaterial / +0xF4 mPrimMaterial2 | calcPrimMaterial output |
| +0xF8 | mSrcColor (status 0x08) / +0xFC mSrcColor2 (status 0x10) | calcKeyframeColor / calcSrcColor |
| +0x100 | mKeyColorScalar / +0x104 mKeyColorScalar2 | |
| +0x108 | mIntensity | clamped 0..127 (status 0x04) |
| +0x110 | mScaleVel | scale velocity (status 0x01/0x40) |
| +0x118..0x13F | `_gap118` | dir keyframe-vector (status 0x80/0x200) + uv-scroll scalars (status 0x1000..0x8000), double-buffered |
| +0x140 | mPtclFlagBase | packed particle flag base |

---

## Type 7 — LensFlare  (init 0x97D2A0, move sub_990B70)  — IDA struct `uEffectVFR::PtclLensFlare` (0xB0)

`mParticleType == 7`. A lens-flare emitter: spawns a **per-flare sprite array** in the generator's `mPosWorkOffset` work buffer (NOT in the node), while the node holds the shared color/intensity/scale/dir state and a transformed base-direction block. Init takes only 4 args; **`a4` is the prim attribute** (stored at +0x80/+0x84). **Size verified; shared channels named, the dir/transform block gapped.**

| Offset | Field | Notes |
|--------|-------|-------|
| +0x00 | base | header |
| +0x40..0x7F | `_dir40` (gap) | sprite base-direction / world-transform block (calcDir + mWmat output) |
| +0x80 | mPrimAttr / +0x84 mPrimAttrMirror | prim attribute (a4 param, two copies) |
| +0x88 | mIntensityMir / +0x8C mIntensityMir2 | intensity mirror (of +0x98) |
| +0x90 | mMaterialWord | packed material/blend (mpParticleParam[4]) |
| +0x94 | mPrimAttribute | generator mPrimAttribute |
| +0x98 | mIntensity | clamped 0..127 (status 0x04) |
| +0x9C | mColorScalar | keyframe color/intensity input scalar |
| +0xA0 | mScaleVel | scale velocity (status 0x01/0x40) |
| +0xA4/+0xA8/+0xAC | mDirX/Y/Z | dir keyframe-vector (calcKeyframeVector, status 0x80) |

---

## Type 8 — MassBillboard  (init 0x97D860, move sub_990E50)  — IDA struct `uEffectVFR::PtclMassBillboard` (0x88)

`mParticleType == 8`. A lightweight billboard rendered through the **`uEffectVFR::tclData` view** (`pad_54[N]` = `0x54+N`). Same family as Texline but smaller — no 6-way dispatch; just base color/intensity/scale channels. Final per-frame hook uses owner vtable **+0xA8** (slot 42) with arg-count 1. **Size + base-region structure verified; render block gapped.**

| Offset | Field | Notes |
|--------|-------|-------|
| +0x00 | base | header (base.mStatus channel bits OR'd via pad_14) |
| +0x40 | mPosW | base scale sample (tclData posW) |
| +0x44 | mPrimAttr | prim attribute (sub_980340) / tclData pad_44 |
| +0x48 | mPos2X / +0x4C mPos2Y | secondary pos / prim attr (sub_980340 result) |
| +0x50 | mPos2Z | scaled size (= intensity * mParticleScale) |
| +0x54..0x87 | `_render54` (gap) | scaled size @0x54, scale/intensity mirrors @0x58/0x5C, packed anim-flag @0x60, tex-frame cur/max @0x64/0x66, keyframe-scale sample @0x68/0x6C, src color @0x70, calcKeyframeColor @0x74, intensity (0..127, status 0x04) @0x78, scale velocity (status 0x01/0x40) @0x80, keyframe color scalar @0x84 |

---

## Type 9 — Filter  (init 0x97DE20, move sub_991120 via moveParticleLoop_type9 @ 0x98DD10)  — IDA struct `uEffectVFR::PtclFilter` (0x50)

`mParticleType == 9`. **Trivial** (0x57-byte init; 0x46-byte move). A full-screen filter/post sub-effect: the node just registers a sub-effect via `sub_906130` and caches a self-pointer, a global, and the spawn scale. The per-frame move sub `sub_991120` only re-checks lifetime (`sub_995CF0`/`sub_998BD0`), re-runs `sub_9061C0` on close reading +0x40/+0x44, double-buffers the gen ptr into +0x48/+0x4C, and clears `base.mAlive` on retire — **confirming the node never exceeds 0x4F, so size 0x50 is correct**. The init node param arrives in **`esi`** (register, `__usercall`), not a stack arg. **Fully named & verified (init + move sub).**

| Offset | Field | Notes |
|--------|-------|-------|
| +0x00 | base | header (base.mAlive cleared to 0 on the sub_906130 / lifetime-fail paths) |
| +0x40 | mSelfPtr | self node pointer (back-ref); read by move sub's close path |
| +0x44 | mFilterGlobal | sDevil4Effect global (mpInstance+0x8A14) |
| +0x48 | mScale / +0x4C mScaleMirror | param_3 spawn scale (init); move sub double-buffers a gen ptr via `4*parity + 0x48` |

---

## Type 10 — Light  (init 0x97DE80, move sub_991190)  — IDA struct `uEffectVFR::PtclLight` (0x90)

`mParticleType == 10`. A dynamic-light particle: holds intensity + a two-channel radius/size group, with the per-light footprint written into a generator work buffer (`mPosWorkOffset`, NOT the node) when `mpParticleParam[17] & 0xF00 == 0x100`. Caches a self-pointer + global like Filter. Final hook uses owner vtable +0xA8 (slot 42) arg-count 1. **Fully named & verified** (all init fields bind cleanly).

| Offset | Field | Notes |
|--------|-------|-------|
| +0x00 | base | header |
| +0x40 | mPrimAttr / +0x44 mPrimAttrMirror | prim attribute (sub_980340) |
| +0x48 | mIntensityMir / +0x4C mIntensityMir2 | intensity mirror (of +0x78) |
| +0x50..0x5C | mSizeScaled0..3 | scaled size (radius * mParticleScale) |
| +0x60 | mSelfPtr / +0x64 mLightGlobal / +0x68 mField68 | self back-ref, sDevil4Effect global, zero-init field |
| +0x6C | mScaleVel | scale velocity (status 0x01/0x40) |
| +0x70 | mSrcColor | calcKeyframeColor / calcSrcColor (status 0x08) |
| +0x74 | mColorScalar | keyframe color input scalar |
| +0x78 | mIntensity | clamped 0..127 (status 0x04) |
| +0x7C | mPrimAttr2 | prim attribute (alt) |
| +0x80/+0x84/+0x88/+0x8C | mRadiusW/H/VelW/VelH | light radius/size channels (status 0x1000) |

---

## Type 11 — Hit  (init 0x97E770, move sub_9915E0)  — IDA struct `uEffectVFR::PtclHit` (0x120)

`mParticleType == 11`. A hit/impact billboard. **The init is tiny (0x84 bytes)** — it only seeds the size group (0x40..0x50) from the resource/keyframe header; the **move sub (`sub_9915E0`) drives the full render** (color/intensity/scale + dir keyframe-vector across 0x40..0x11F). Node sized to the move-sub max (0x120). Note the dispatcher passes the **node first** (`initParticleHit(node@ecx, gen@edx)`, `__fastcall`). **Size verified (from move sub); only the init-seeded size group named, render block gapped.**

| Offset | Field | Notes |
|--------|-------|-------|
| +0x00 | base | header (init sets base.mStatus \| 0x1000 when sizeH != 0) |
| +0x40 | mSizeScaledW / +0x44 mSizeScaledWMir | scaled size W (= sizeW * mParticleScale), two copies |
| +0x48 | mSizeW / +0x4C mSizeH | size W / H base (resource/keyframe header) |
| +0x50 | mSizeSum | = sizeW + sizeH |
| +0x54..0x11F | `_render54` (gap) | move-sub-driven: colors (calcKeyframeColor), intensity (clamp 0..127), scale, dir keyframe-vector + mirrors, double-buffered. Per-field naming deferred. |

---

## Type 15 — PolygonStrip  (init 0x97E800, move loop `moveParticleLoopPolygonStrip` 0x99BD10)  — IDA struct `uEffectVFR::PtclPolygonStrip` (0x120)

`mParticleType == 15`. A polygon strip/ribbon — the PolygonStrip analog of Polygon (type 2) / PrimModel (type 6). Carries calcPrimMaterial, dual src-color channels, intensity, scale-velocity, a dir keyframe-vector, and width/height size channels. Its per-frame move is the fixed loop `moveParticleLoopPolygonStrip` (0x99BD10), which calls `moveParticleMoveParam` + `buildPolygonStripEdgeVert` (×2, for the two strip edges) — *not* a vtable-dispatched per-particle sub, so the field layout below is derived **from the init alone**. (The init's `pGen->mpMoveTopParticle + 168` call is the shared **+0xA8 / slot 42** world-transform hook, gated on `mFlags & 0xF00` — the same hook every billboard type uses; it is *not* a move dispatcher. An earlier draft mislabeled it "+0x168".) **Size & gross structure verified; clear color/material/intensity/scale/dir channels named, the double-buffered scale/size regions (0x40..0xBF) gapped.**

| Offset | Field | Notes |
|--------|-------|-------|
| +0x00 | base | header |
| +0x40..0x7F | `_gap40` | base scale/pos region (double-buffered scale @0x70/0x74) |
| +0x80 | mScaledW | scaled size W |
| +0x90/+0x94/+0x98 | mScaledW0/mScaledH/mScaledH1 | scaled size (W/H * scale) |
| +0xA0/+0xB0 | mScaleBroadcastMir / mScaleBroadcast | base-scale/intensity broadcast (NOT a size axis — same pattern as mScaleCur/Mir @0xD8/0xDC) |
| +0xA4/+0xB4 | mSizeHMir / mSizeH | size H render channel + mirror (status 0x1000/0x4000 keyframe) |
| +0xAC | mScaleSampledMir / +0xBC mScaleSampled | sampled scale + mirror |
| +0xC0/+0xC4/+0xC8/+0xCC | mPrimAttr/Next/2/C | sub_980340 prim attribute (+ mirrors) |
| +0xD0/+0xD2 | mAnimFlagWord/mTexIdx | packed anim flag + random tex index |
| +0xD4/+0xD6 | mTexFrameCur/mTexFrameMax | texture frame cur/max |
| +0xD8/+0xDC | mScaleCur/mScaleMir | |
| +0xE0/+0xE4 | mPrimMaterial/mPrimMaterial2 | calcPrimMaterial output |
| +0xF0/+0xF4 | mSrcColor (status 0x08) / mSrcColor2 (status 0x10) | calcKeyframeColor / calcSrcColor |
| +0xF8 | mSrcColorScalar / +0xFC mSrcColor2Pad | |
| +0x100 | mIntensity | clamped 0..127 (status 0x04) |
| +0x104 | mKeyColorScalar / +0x10C mKeyScaleC | |
| +0x108 | mScaleVel | scale velocity (status 0x01/0x40) |
| +0x110 | mDirX (base) / +0x114 mDirXChan / +0x118 mDirY / +0x11C mDirZ | dir keyframe-vector (calcKeyframeVector, status 0x80) |

---

## Type 16 — LiteBillboard  (init `uEffectVFR::initParticleLiteBillboard` 0x9DCB70, move `uEffectVFR::moveParticleLiteBillboard` 0x9DD210)  — IDA struct `uEffectVFR::PtclLiteBillboard` (0x8C)

`mParticleType == 16`. **Confirmed = SE `cParticleGeneratorLiteBillboard`** (via `moveGenerator`'s annotated dispatch). A *lighter* billboard than type 0: same render skeleton (`getAnimFlag` / `calcPrimMaterial` / `calcKeyframeColor` / `calcSrcColor` / `sub_980340` prim-attr / status bits `0x20`/`0x4`/`0x8`/`0x40`/`0x1`) but **fewer channels** — no 2nd-intensity/keyframe pass, no extra-scale/tail channels — so the node is **0x8C** vs full Billboard's 0xA8. Same shape family as MassBillboard (0x88) / Texline.

**Dispatch is virtual, both ways:**
- **Spawn:** `initParticle`'s `switch(mParticleType)` case 16 does *not* call a fixed `initParticle*` — it calls **owner vtable slot 43 (+0xAC)**. The base `uEffectVFR::vftable` points all 12 family vtables at the same impl (`0x9DCB70`; no subclass override), so it always resolves to `initParticleLiteBillboard`.
- **Move:** `moveParticleLoop_type10` (0x98DFA0, the `moveGenerator` case `0x10` loop) iterates the Move list and calls **owner vtable slot 44 (+0xB0)** = `moveParticleLiteBillboard` (0x9DD210) per live particle. (Same virtual-move pattern as PolygonStrip.)

**Verified by applying the struct to the init + re-decompiling** — all `base.*` fields and `mKeyScalar88` collapse cleanly; the dense double-buffered render block renders as raw `_render40[N]` (absolute = `0x40 + N`), and there are **no past-the-end accesses** (confirms 0x8C). Per doc convention the dense block is left gapped.

| Offset | Field | Notes |
|--------|-------|-------|
| +0x00 | base | shared header (status bits OR'd; mScale/mParam1c set at tail; mParity-indexed double-buffer) |
| +0x40/+0x44 | `_render40[0]/[4]` | scaled keyframe value (double-buffer pair) |
| +0x48/+0x4C | `_render40[8]/[12]` | prim-attribute (sub_980340), double-buffered; also the vtable+0xA8 (slot 42) world-transform I/O |
| +0x50/+0x54 | `_render40[16]/[20]` | scale value (pair) / transform output |
| +0x58/+0x5C | `_render40[24]/[28]` | mPrimMaterial / mPrimMaterial2 (calcPrimMaterial) |
| +0x60/+0x62 | `_render40[32]/[34]` | mAnimFlag (low) / mRandTexIdx (high), packed |
| +0x64/+0x66 | `_render40[36]/[38]` | mTexFrame / mTexFrameMax |
| +0x68/+0x6C | `_render40[40]/[44]` | keyframe-scale values |
| +0x70/+0x74 | `_render40[48]/[52]` | mSrcColor / color scalar (calcKeyframeColor / calcSrcColor, status 0x08) |
| +0x78/+0x7C | `_render40[56]/[60]` | mIntensity (clamped 0..127, status 0x04) |
| +0x80/+0x84 | `_render40[64]/[68]` | scale-velocity pair (status 0x01/0x40) |
| +0x88 | mKeyScalar88 | early keyframe scalar (init seeds it before the +0x58/+0x68 region); the field that sets the true node size to 0x8C |

> **Note (size trap):** the size is set by the init write at `0x9dcbfa` (`pParticle->mKeyScalar88` = +0x88), **higher** than the move sub's max touch (+0x84). Scanning only the move sub would under-size the node to 0x88 and truncate this field.

---

## TODO (remaining)

**Done this pass:** Texline (3/13), PrimModel (6), LensFlare (7), MassBillboard (8), Filter (9), Light (10), Hit (11), PolygonStrip (15) — all declared, applied to their inits, `type_inspect`-gated, and re-decompile-verified.

**LiteBillboard (16): DONE (2026-06-03)** — declared `uEffectVFR::PtclLiteBillboard` (0x8C), applied to init + move, re-decompile-verified, both functions named (`initParticleLiteBillboard` / `moveParticleLiteBillboard`). The earlier note "case 16 shares the jumptable target with case 17" was **wrong**: case 16 = LiteBillboard (vtable +0xAC/+0xB0), case 17 = SizeBillboard (`initParticleSizeBillboard`) — distinct. With this, **all 18 render types (0–17) are reversed**; nothing left pending.

### Lesson learned (struct declaration gotcha)
When embedding `uEffectVFR::Particle base` (0x40) as the first member, **do not** also declare overlay members for the 0x00–0x3F region — `base` already owns it, so any such members pile on at 0x40+ and shift every later field. First extension member must start at 0x40; reference base fields as `base.mScale` etc. **Always `type_inspect` the declared struct and check member offsets against intent before applying** — the shift shows up there instantly.

### Method (validated on Billboard + SizeBillboard)
For each type: decompile `initParticle<Type>` + the per-particle move sub its `moveParticleLoop_type*` delegates to → map node writes by **absolute offset** (raw `node+N`, or `0x40*n + member` for `_EDI[n]` chunked views; the decompiler field *names* on `_EDI[n]` are wrong, offsets are right) → `declare_type` a `struct uEffectVFR::Ptcl<Type> { uEffectVFR::Particle base; <ext...> }` → apply to the init's node param → re-decompile to confirm fields collapse cleanly. Node size is runtime (`Generator+0x14 mParticleSize`); struct sized to max offset touched.
