# EFL → Blender import — implementation plan

Status: **plan only, nothing implemented.** Written 2026-10-05. It builds on `RE/uEffectVFR_findings.md`,
`RE/efl_generator_struct.md`, `RE/particle_type_structs.md` and `RE/particle_move_param.md`. All offsets here
are **DX9** offsets taken from DX9 code unless marked otherwise. Do not borrow SE offsets: the two builds diverge
(see the SE cross-check notes in `particle_type_structs.md`).

---

## 1. Goal and scope

Read DMC4 DX9 `.efl` effect lists into an engine-independent data model. Then:
1. dump that model as JSON for inspection and diffing;
2. regenerate `RE/efl.bt` (010 Editor) from the same layout definitions;
3. import it into Blender, in two levels:
   - **Static** (M1): every generator becomes an Empty with all parameters attached. PrimModel particles become real
     meshes, and particles get materials with texture references.
   - **Dynamic** (M2): Geometry Nodes simulations that approximately replay emission, motion and lifetime.

**Non-goals for now:** exact runtime fidelity (the game simulates on the CPU with its own RNG table), export back to
`.efl` (kept possible by design, see §9), and effects that only exist as post-processing (Filter, LensFlare, Hit).

---

## 2. Architecture

```
efl/                         pure Python 3.10+, no Blender / no third-party deps
  schema.py                  single source of truth: every struct, field, offset, type, evidence tier
  binio.py                   little-endian reader/writer helpers, MtRangeF/MtRangeU16/MtColor/MtVector types
  container.py               header + 16-byte record table + block slicing
  blocks/                    generator.py, particle.py (common chain + per-type), life.py, move.py, keyframe.py
  model.py                   dataclasses: EffectList, Generator, ParticleParam, LifeParam, MoveParam, Keyframe
  parse.py                   bytes -> model (unknown regions preserved as raw bytes)
  write.py                   model -> bytes (round-trip; see §9)
  export_json.py             model -> JSON (with evidence tier per field)
  gen_bt.py                  schema -> RE/efl.bt
  tools/arc.py               MT Framework .arc extractor (sample acquisition)
  tests/                     corpus round-trip + invariants (§7)

io_import_efl/               Blender add-on (thin layer over efl/)
  __init__.py                bl_info, operator, import options
  build_static.py            collection, empties, custom props, materials
  primmodel_mesh.py          Ring/Sphere/Grid mesh builders (port of the DX9 builders)
  nodes/                     Geometry Nodes groups for the dynamic import (built in code, versioned)
  build_dynamic.py           wires generators to the node groups, keyframes -> F-curves
  coords.py                  axis/unit/quaternion conversion
```

Rules:
- **One schema drives everything.** `schema.py` describes each struct as rows of
  `(offset, name, type, evidence, note)`. The parser, the JSON exporter, the 010 template generator and the docs all
  read from it, so a correction is made once.
- **Evidence tiers are carried through:** `dx9` (verified in DX9 code), `se` (name from the SE PDB, DX9 layout
  agrees), `prior` (inherited name, unverified) and `unknown` (raw bytes). JSON and Blender custom properties keep the
  tier so nobody mistakes a guess for a fact.
- **Unknown bytes are never dropped.** Every block keeps its full byte span. Typed fields are views onto it, and gaps
  are stored as raw bytes, so round-tripping is exact even before the format is fully understood.

---

## 3. Format specification (current knowledge)

### 3.1 File header — DX9-verified (`rEffectList::load`)

| Off | Type | Field | Notes |
|---|---|---|---|
| 0x00 | char[4] | magic | `'EFL\0'` (dword `0x004C4645`) |
| 0x04 | u32 | version | must equal `0x20070801`, otherwise the load fails |
| 0x08 | u32 | contentSize | passed to the content allocator (`sub_A3DC50`); the copy length is `rEffectList+0x68` |
| 0x0C | u32 | EffectListNum | number of 16-byte records |
| 0x10 | u32 | unitGenRecord | packed `(off<<8)\|type` → child/unit generator block (`rEffectList.GeneratorType`) |
| 0x14 | u32 | unitMoveRecord | packed `(off<<8)\|type` → child/unit move block (`mGeneratorMoveType`) |
| 0x18 | f32 | mBaseFPS | base frame rate of all frame counts in the file |
| 0x1C | u32 | ? | unread by `load` |
| 0x20 | — | content | copied verbatim to `ContentPtr`; **all offsets below are relative to file+0x20** |

### 3.2 Record table — DX9-verified (`create_resource_infos`, `createGenerator`)

`EffectListNum` records of 16 bytes at content+0. Each is four dwords, `dword = (offset << 8) | typeByte`, and an
offset of 0 means the slot is absent:

| Slot | Block | Type byte | Consumer |
|---|---|---|---|
| 0 | `EFL_GENERATOR` | (to verify: group/generator selector) | `initGenerator`, `createGeneratorResources` |
| 1 | particle param | **particle type** (0–17, enum below) | `initGeneratorParam`, `create_particle_resources` |
| 2 | life param | life type | `initGenerator` (layout not yet reversed) |
| 3 | move param | **move type** (0–6) | `create_move_resources`, the move dispatchers |

- Filtering: `createGenerator` keeps a record when `(mGroupFlag & rec[0]) && (mpParamBlock & rec[1])`. **To verify**
  exactly which bits are tested; this matters for the importer's "group" option.
- Block lengths aren't stored. Infer each one as the distance to the next block offset in the file and cross-check
  it against the schema size (§7).

**Particle types** (writer-verified):

| Value | Type | Value | Type | Value | Type |
|---|---|---|---|---|---|
| 0 | Billboard | 6 | PrimModel | 12 | PolygonStrip |
| 1 | Polyline | 7 | LensFlare | 13 | Texline (alt) |
| 2 | Polygon | 8 | MassBillboard | 14 | Line (alt) |
| 3 | Texline | 9 | Filter | 15 | PolygonStrip (alt) |
| 4 | Line | 10 | Light | 16 | LiteBillboard |
| 5 | Model | 11 | Hit | 17 | SizeBillboard |

**Move types:** 0 None, 1 Add, 2 Mul, 3 PathStrip, 4 PathChain, 5 PathKeyframe, 6 PathLine.

### 3.3 `EFL_GENERATOR` (0x1E4) — slot 0

| Off | Type | Field | Tier |
|---|---|---|---|
| 0x0B | u8 | RandomNoNum | dx9 (read) |
| 0x10 | ?[8] | RandomNo | dx9 |
| 0x30 | MtFloat3 | Pos | dx9 (`moveUnitGenerator` → `setQuatParentOfs`) |
| 0x3C | s32 | ParentNo (joint index) | dx9 |
| 0x40 | MtVector4 | Quat | dx9 |
| ~0x74–0x77 | MtRangeU16 | WaitFrame | dx9-read; **pin the exact start** (the docs give both 0x74 and 0x76) |
| 0x7C / 0x94 / 0xAC | — | Scale / Range / SetNum | prior (unverified) |
| 0xB0 | MtRangeU16 | LoopNum | dx9 |
| 0xB4 | MtRangeU16 | SetFrame | dx9 |
| 0xB8 | u16 | SetInterval | dx9 |
| 0xBC | f32 | SetFrameDist | dx9 |
| 0xC0 | MtRangeF | (particle-scale range → Gen.mParticleScaleBase) | dx9 |
| 0xC8 | u8 | RangeType (spawn shape switch) | dx9 offset, se name |
| 0xC9 / 0xCA / 0xCB | u8 | RangeDirType / RangeOptionFlags / uknRangeFlag | dx9 offset |
| 0xCC / 0xCD / 0xCE | u8/u8/s16 | RangeStripType / Flag / PartsNo | dx9 offset |
| 0xD0 | char[64] | RangeStripPath (`.efs`) | dx9 |
| 0x110 | MtRangeF[4] | spawn-range ranges ([0] = {0x110, 0x114}) | dx9 |
| 0x130 | u32 | RangeDivideNum | dx9 |
| 0x13C / 0x13E / 0x13F | u8 | mVibReqType / mVibReqArg0 / mVibReqArg1 | dx9 |
| 0x140 | char[64] | ExtVibrationPath (`.vib`) | dx9 |
| 0x180 | char[64] | SoundRequestPath (`.srq`) | dx9 |
| 0x1C0 / 0x1C2 / 0x1C4 | u16/u16/u32 | VibReqNo / VibOptionFlag / VibPriority | dx9 |
| 0x1C8 / 0x1CA | u16/u16 | SeReqNo / SeOptionFlag | dx9 |
| 0x1CC | s32 | self-relative sub-block (matrix source, gated by Gen.mStatus & 0x10) | dx9 |
| 0x1D0–0x1DC | s32×4 | Keyframe{Scale,SetNum,Range,Ofs}ParamOffset (self-relative) | prior names, dx9 reads |
| 0x1E0 | s32 | ? | unknown |

### 3.4 Particle param — slot 1

The base chain is DX9-verified after the 2026-10-05 fix and SE-cross-checked.

`EFL_PARTICLE_COMMON` (0x14): 0x00 TransMode u8 · 0x01 EntryType u8 · 0x02 CullingFlag u16 (bit 0 = culling draw
variant, bit 0x40 = culling block present) · 0x04 ParticleOptionFlag · 0x08 LightGroupFlag · 0x0C zOfs ·
0x10 FixOtDepth u16.

`EFL_PARTICLE_DRAW_COMMON` (0x50):

| Off | Field | Off | Field |
|---|---|---|---|
| 0x14 | PrimMaterialFlags | 0x40 | ColorFlag u8 |
| 0x18 | Intensity MtRangeF | 0x41 | bit0 KeyframePatSpeedParamFlag |
| 0x20 | Scale MtRangeF | 0x42 | KeyframeColorParamOffset u16 |
| 0x28 | ScaleAdd MtRangeF | 0x44 | KeyframePatNoParamOffset u16 |
| 0x30 | KeyframeIntensityParamOffset s32 | 0x46 | **CullingParamOffset** u16 (→ culling block) |
| 0x34 | KeyframeScaleParamOffset s32 | 0x48 | colors MtColor[2] |
| 0x38 / 0x3C | s32 ? | | |

`EFL_PARTICLE_PRIM_COMMON` (0x170):

| Off | Field | Off | Field |
|---|---|---|---|
| 0x50 | AnimFlag u16 | 0x5C | PatNoMax |
| 0x52 / 0x53 | SeqNoMin / SeqNoRange u8 | 0x60 | PatCenter MtPoint |
| 0x54 / 0x56 | PatNoMin / PatNoRange u16 | 0x68 / 0x6C | TextureInvW / H |
| 0x58 | PatSpeed f32 | 0x70 / 0xB0 / 0xF0 | BaseMapPath / NormalMapPath / MaskMapPath char[64] |
| | | 0x130 | AnimPath char[64] (`.ean`) |

**Per-type tails, from 0x170:**

| Type | Status |
|---|---|
| Billboard (0x1A0) | Angle 0x170, AngleAdd 0x178, AspectRatio 0x180, AspectRatioAdd 0x188 (dx9 offsets, prior names) |
| Polygon (0x1E0) | Rot 0x170, RotAdd 0x188, … (prior) |
| Polyline (0x1E0) | LineType 0x170, LineOfsNum 0x171, ColorPlace* 0x172–0x173, PlaceColor 0x178, HeadSize 0x180, … (prior names, dx9 offsets) |
| **PrimModel (≥0x25C)** | see §3.5 |
| Model (5) | ModelPath char[64] **@0x50** (resource loader). Type has a different base, **not** PRIM_COMMON; rest untyped |
| LensFlare (7), MassBillboard (8) | resource paths at 0xA0 / 0x60 (loader); rest untyped |
| Line, Texline, PolygonStrip, SizeBillboard, LiteBillboard, Light, Hit, Filter | untyped beyond the shared base → RE task R4 |

### 3.5 PrimModel tail (0x170–0x25B) — DX9-verified, SE-cross-checked

| Off | Field | Notes |
|---|---|---|
| 0x170 | PrimFlags u32 | nibbles: [0–3] PrimModelType (0 Ring, 1 TexRing, 2 Sphere, 3 TexSphere, 4 Grid, 5 TexGrid) · [4–7] Axis · [8–11] RotOrder · [12–15] DirAxisType · [16–19] ColorPlaceType · [20–23] ? (SE padding) · [24–27] ModelBillboardType · [28–31] NormAttenuateFlag (bit 29 = one-sided) |
| 0x174 | HoriColorPlaceNo u16 | gradient split |
| 0x176 | u16 | SE: RotResetFlag / ModelBillboardOrder / LookAt; ProjectionType @0x177 (no DX9 reader yet) |
| 0x178 / 0x17C | PlaceColor1 / 2 | MtColor |
| 0x180–0x18E | RotDivNum, RotTexDivNum, RotDrawStart, RotDrawEnd, HoriDivNum, HoriTexDivNum, HoriDrawStart, HoriDrawEnd | u16 each |
| 0x190 | ModelScale MtRangeF[3] | → mScaleVec |
| 0x1A8 | ModelScaleAdd [3] | → mScaleVecVel |
| 0x1C0 | Rot [3] | → mRot |
| 0x1D8 | RotAdd [3] | → mRotVel |
| 0x1F0 | Radius [2] | → shape.x / .y |
| 0x200 | RadiusAdd [2] | → shapeVel |
| 0x210 | Height [2] | → shape.z / .w |
| 0x220 | HeightAdd [2] | → shapeVel |
| 0x230 / 0x234 / 0x238 | NormAttenuateAngleStart / End, NormAttenuateCurve (MtEaseCurve) | |
| 0x240–0x258 | Keyframe{PlaceColor,Rot,ModelScale,Radius0,Radius1,Height0,Height1}ParamOffset | s32, self-relative |

The shape vector means `(r0, r1, h0, h1)` for Ring, `(R, –, H, offset)` for Sphere and `(w0, w1, d0, d1)` for Grid.

### 3.6 Life param — slot 2

**Not reversed.** The old template guessed `fadein[2], transition[2], fadeout[2]` (s16 pairs) plus
`KeepHoldFlag:1 / KeyframeKeepFrameParamOffset:15 / KeepHoldFrame:16`. Treat that as a hypothesis → RE task R2.

### 3.7 Move param — slot 3 (mapped 2026-10-05)

The full tables are in `RE/particle_move_param.md` → "On-disk move param". Summary:

| Type | Layout |
|---|---|
| `EFL_MOVE_COMMON` (0x10) | `MoveOptionFlag`, `ForceType`, `RotAxisOrder`, `CollParamOffset` (u16 → collision block), `ForceRate` |
| `EFL_MOVE_BASE` (0x40) | `Rot[3]`, `Speed`, `Gravity`, keyframe offsets (Rot / Speed / FallSpeed) |
| Add (0x48) | `Acceleration` @0x40 |
| Mul (0x48) | `SpeedCoef` @0x40 |
| Path common (0x70) | `ReleaseType` / `OptionFlag` / `KeyframeReleaseFrameParamOffset`, `ReleaseFrame`, `Acceleration`; 0x50–0x6F (`Path3DScale*`, `PathLengthScale`) unconfirmed in DX9 |
| Strip (0xC0) | `Distance`, `PathStripType` / `Flag` / `PartsNo`, `PathCurveDivideNum`, `PathStripPath` (`.efs`) |
| Chain (0x110) | `Distance`, `ChainPosNum`, `EFL_PARAM_CHAIN` @0x80 |
| Keyframe (0x74) | `KeyframeOfsParamOffset` |
| Line (0x7C) | `Distance`, `PathLength` |
| `EFL_PARAM_COLLISION` (≥0xB0) | `CollFlag`, `CollCancelFrame`, `CollRadiusAdd`, `CollRadius`, bounce/finish params, modes and callback flags, `BounceNum`, `BounceRate`, `BounceEffectPath` @0x30, `FinishEffectPath` @0x70 |

Blender mapping notes:
- `CollRadiusAdd` means the collision radius grows each frame (clamped at `CollRadius` s+r).
- Bounce count = `BounceNumBase + rand % (BounceNumRange+1)`.
- The bounce and finish effects are other `.efl` files, so the importer can resolve them as linked collections.

### 3.7a Enums (SE PDB, imported into the DX9 IDB 2026-10-05)

49 effect enums were imported from the SE PDB as DX9 types (`rEffectList::*`, `rEffectStrip::*`, `rEffectAnim::ANIM_FLAG`,
`cParticle::*`, `cParticleManager::*`). Twelve DX9 struct fields carry them where DX9 masks/compares were verified (table
in `particle_move_param.md`). For the parser: use these enums for display and Blender enum properties, but treat
values outside the verified bits as raw.

Useful for the importer:
- `LIFE_TYPE` (NONE, FRAME_ALPHA/COLOR, KEYFRAME_*, HIDEFRAME_*, CURVEFRAME_*) and `cParticle::PTCL_LIFE_RNO_TBL`
  (HIDE/APPEAR/KEEP/VANISH/FINISH) are the starting point for **R2 (life block)**.
- `PARTICLE_OPTION_FLAG` covers blend and depth flags (DEPTH_BLEND, NO_ZTEST, NO_FOG, BACKFACE_CULLING, BOTHFACE_DRAW…),
  which map to Blender material settings.

### 3.8 Self-relative blocks

| Block | How it's reached | Status |
|---|---|---|
| Keyframe block | `param + s32/u16 offset`, offset 0 = none | header dword: bit 30 = flag (loop?), bits 27–29 = interpolation type, low bits = count (**to verify**); data from +4. Readers: `calcKeyframeF32/Vector/Color`, `calcKeyframeFixAngleVector3`, `getKeyframeTimer` → RE task R1 |
| Culling block | `DRAW_COMMON+0x46` | +0 flags (`>>8` / `>>12` = `calcDir` modes), +4 dir vec3, +0x10–0x1C near/far ranges, +0x2C sort param (SE: `EFL_PARAM_CULLING`) |

---

## 4. Outstanding RE work (ordered by import value)

| ID | Task | Entry points (DX9) | Unblocks |
|---|---|---|---|
| R0 | Pin record type-byte semantics and the group filter bits | `createGenerator` 0x96A770, `matchGeneratorFilter` 0x9DD560 | correct per-group import |
| R1 | **Keyframe block format** (header bits, key layout per value type, timer modes) | `calcKeyframeF32`, `calcKeyframeVector`, `calcKeyframeColor`, `getKeyframeTimer`, `getKeyFrameSmthOffset` | F-curves (M2) |
| R2 | **Life block** layout and the life-type enum | `initGenerator` 0x96ACA0 (slot-2 reader), Generator `mLifeType` @0xC2, `mLifeWorkOffset` | alpha/scale over age |
| ~~R3~~ | **Done 2026-10-05.** Move param tails + collision block mapped (§3.7). Flag/type fields now carry DX9-verified SE enums. `EFL_PARAM_CHAIN` header verified. Path3DScale block and SE tail extras have no DX9 reader (treat as raw). Residual: collision nibble pair (attach/relation?) | — | motion (M2) |
| R4 | Remaining particle-type tails | `initParticle<Type>` per type; renderers already named | non-PrimModel geometry |
| R5 | Spawn-range shapes (`RangeType` cases) | `sub_999640`, `uEffectVFR::Funcx90` | emitter shapes |
| R6 | Child/unit generator records (header 0x10/0x14) | `initChildGenerator` 0x96BB70, `moveUnitGenerator` 0x96FF00 | unit effects |
| R7 | WaitFrame exact offset; Tier-2 generator fields (Scale/Range/SetNum) | `uknGenBehaviorFunc1`, `initGeneratorParam` | emission schedule |
| R8 | Coordinate conventions (Y-up? handedness, unit scale, quaternion order) | any known model + effect pair in game; `calcParticleMatrix` | correct placement |

Do the RE in IDA first. Then add schema rows with `evidence='dx9'` and a note naming the function/address that proves
each one.

---

## 5. Milestones

### M0 — Samples and corpus

1. `tools/arc.py`: an MT Framework `.arc` extractor. The expected layout (**verify against a real file**) is
   `'ARC\0'`, version u16, file count u16, then entries of `char path[64]`, `u32 typeHash`, `u32 compSize`,
   `u32 size|flags`, `u32 offset`, with zlib data.
2. Extract every `.efl`, plus the `.efs`, `.ean`, `.tex` and `.mod` they reference, into `corpus/` while keeping the
   archive paths.
3. Produce corpus stats: file count, records per file, histograms of type bytes per slot, version values.

**Exit:** a corpus of real files, with every header passing the magic/version check.

### M1a — Parser core and round-trip

1. `container.py`: the header, the record table, block discovery (all unique offsets → spans), and slicing.
2. `schema.py` covering everything in §3. Unknown spans are kept raw.
3. `write.py`: rebuild bytes from the model with no edits.
4. `export_json.py`: model → JSON, including per-field evidence tiers.

**Exit:** `parse → write` is byte-identical for 100% of the corpus, and the §7 invariants hold.

### M1b — 010 template regeneration

`gen_bt.py`: schema → `RE/efl.bt` (header, record table, per-slot dispatch on the type byte, the common chain,
per-type tails, and self-relative blocks followed via `FSeek`). Replace the hand-written template.

**Exit:** the template opens every corpus file without errors, and its field values match the JSON dump.

### M1c — Blender static import

1. **Operator** `import_scene.efl`. Options: unit scale, axis conversion, FPS handling (use the file's `mBaseFPS` or
   rescale to the scene), group filter, texture search roots, "dynamic" toggle (off in M1).
2. **Collection** per file, with header fields as custom properties.
3. **Generators:** one Empty per record (`Gen_<index>_<ParticleType>_<MoveType>`):
   - location ← `Pos`, rotation ← `Quat` (quaternion mode);
   - all schema fields go into custom properties grouped by block (`gen.*`, `ptcl.*`, `move.*`), including tiers;
   - `MtRangeF` is stored as `[s, r]` with a note on the semantics (`s + rand × r`).
4. **`ParentNo`:** if an armature is selected when importing, bone-parent the Empty to joint `ParentNo` (**the
   joint-index → bone-name map needs the `.mod` skeleton**). Otherwise store it as a property.
5. **PrimModel meshes** (`primmodel_mesh.py`). Port the six builders:

   | Builder | Shape |
   |---|---|
   | `buildPrimModelRing` 0x9CD670, `TexRing` 0x9CEFC0 | angle step 2π/N, centred offset N/2, two rings (r0,h0)/(r1,h1), M stacks lerped (`lerp_cell_corners`), quads |
   | `buildPrimModelSphere` 0x9D11C0, `TexSphere` 0x9D4250 | latitude π/M, longitude 2π/N, pole triangle fans, band quads |
   | `buildPrimModelGrid` 0x9D83C0, `TexGrid` 0x9D8C70 | trapezoid between edges (w0,d0)/(w1,d1) |

   All six honour the draw ranges (`*DrawStart/End`), the axis nibble (`>>4`), UV repeat (`*TexDivNum`) on the Tex
   variants, and the edge-alpha flag (`ParticleOptionFlag & 0x80000`, written as a vertex attribute). Build one mesh
   per generator from the **base** values (`s`) of each range, and store the ranges as properties.
6. **Materials:**
   - one per particle param; Image Texture nodes for Base/Normal/Mask when the files resolve (`.tex` → DDS/PNG
     conversion is a separate tool, or a user-supplied folder);
   - blend mode from `TransMode` (mapping table to be pinned down; additive = Emission + Transparent);
   - colour from `colors[0..1]` and `PlaceColor` → Color Ramp along a mesh attribute (`ColorPlaceType`);
   - `.ean` flipbook: frame grid from `TextureInvW/H` and `PatNo*`, a Mapping-node offset driven by
     `frame × PatSpeed`. This needs the `.ean` sequence table (`rEffectAnim`: table at +0x68, 32-byte entries,
     pattern count at +4), which is a small RE task alongside R4.
   - Rim fade (`NormAttenuate*`) → Layer Weight → alpha. Culling variant (`CullingFlag` bit 0) → Camera Data
     distance → alpha.
7. **Strip sidecars:** `RangeStripPath` / move `.efs` → Curve objects (format: `rEffectStrip`, still to be
   reversed; builders `sub_B256D0` / `sub_B26060`).

**Exit:** every corpus file imports without errors, PrimModel effects look plausible next to in-game captures, and
every field is visible as a custom property.

### M2 — Dynamic import (Geometry Nodes simulation)

One shared node-group library, created from code with a version stamp and reused across imports:

| Node group | Inputs | Implements |
|---|---|---|
| `EFL_Emit` | WaitFrame, SetFrame, LoopNum, SetNum, SetInterval, RandomNo seed | emission schedule (port of the `updateSingleGenerator` / `uknGenBehaviorFunc1` state machine, incl. the loop reseed `base + rand % (range+1)`) |
| `EFL_SpawnShape` | RangeType, ranges, RangeDivideNum | point/sphere/box/cylinder/strip distribution (after R5) |
| `EFL_Range` | s, r, seed | per-point `s + rand × r` |
| `EFL_Move_None/Add/Mul` | speed, accel, gravity, fall speed, rate | velocity integration per step (Add: `v += a`; Mul: `v *= rate`; both: `fall += gravity`) |
| `EFL_Move_Path*` | curve, distance, reach frame, sub-mode | Sample Curve by age; clamp (Line) vs wrap (Strip) |
| `EFL_Life` | life block (after R2) | age → alpha/scale curves |
| `EFL_Instance_*` | particle type | Billboard (camera-aligned quad), PrimModel (instanced M1c mesh with per-instance shape/scale/rot velocities), Model (linked object), Polyline/Line/Texline (trail curves → Curve to Mesh) |

- Keyframe blocks (after R1) → F-curves on the matching node-group inputs, or on per-particle curves sampled by age.
  `MtEaseCurve` → F-curve easing.
- RNG: the game uses a 4096-entry table (`sDevil4Effect::mpInstance + 0x20 / +0x4020`) indexed by a running counter.
  Optionally dump the table from a live process to get deterministic, game-matching randomness. Otherwise use Blender's
  hash-based Random Value node and accept the divergence.

**Exit:** a chosen set of reference effects (1–2 per particle/move type) visually matches in-game footage in timing
and shape.

### M3 — Optional

- **Export** (Blender → `.efl`): only for edited parameters on imported effects. Write through the raw-preserving
  model, so unknown bytes survive.
- **Live validation:** x64dbg (sandbox skill) breakpoint after `initGenerator` / `initParticle*` to compare runtime
  Generator/Particle values with what the parser predicts.

---

## 6. Blender conventions (decide in R8, then freeze in `coords.py`)

- **Axis:** MT Framework content is assumed Y-up. The Blender mapping is likely `(x, y, z) → (x, -z, y)`. **Verify**
  with an effect attached to a known joint.
- **Units:** game units → metres via a user scale option. The default is to be decided from a known model height.
- **Quaternion:** the file stores `MtVector4 (x, y, z, w)`; Blender expects `(w, x, y, z)`.
- **Frames:** keep EFL frame counts as-is in properties. Map to scene time by `scene_fps / mBaseFPS`.
- **Naming:** collection `EFL_<file>`; objects `Gen_<i>_<Ptcl>_<Move>`; property keys mirror schema names.

---

## 7. Validation and tests

1. **Round-trip** (M1a gate): byte-identical rewrite for the entire corpus.
2. **Structural invariants**, checked for every file:
   - block offsets fall inside the content and are 4-aligned;
   - blocks don't overlap (unless shared on purpose; record which ones are);
   - inferred block size ≥ the schema size for the slot's type byte;
   - self-relative offsets land inside their parent block's span;
   - char[64] paths are NUL-terminated printable ASCII with the expected extension;
   - enums are in range (particle 0–17, move 0–6, PrimModelType 0–5);
   - floats are finite.
3. **Field-usage coverage:** for each schema field, the percentage of corpus records where it is non-zero. Fields that
   are always zero are candidates for "unused"; varying unknown spans are RE priorities.
4. **Cross-check with the IDB:** each `dx9` schema row carries the function/address that proves it, and a
   script can re-verify the offsets against the live IDB after future struct edits.
5. **Visual references:** capture 10–20 in-game effects (screenshots or video) for M1c/M2 sign-off.

---

## 8. Risks

| Risk | Mitigation |
|---|---|
| No samples yet; the `.arc` layout is unverified | M0 first; build the extractor against a real archive before anything else |
| Keyframe/life formats are harder than expected | M1 doesn't depend on them; ship static import first |
| Coordinate/unit conventions wrong | Isolated in `coords.py`; validate with R8 before mass import |
| SE names leak into DX9 offsets | Schema evidence tiers; never copy SE offsets (the tail and other places differ) |
| Exact visual parity impossible (runtime RNG, sort/blend specifics) | Treat M2 as an approximation; optional RNG-table dump |
| Shared/overlapping blocks between records | Discovered by the §7 invariants; the model keeps blocks by offset and records reference them |
| Blender API churn (Geometry Nodes) | Build node groups from code with a version stamp; target one Blender LTS |

---

## 9. Design for later export

- The model holds each block as `(offset, raw bytes)` plus typed views, and edits write back into the raw bytes.
- Record/block topology (shared offsets, ordering, padding) is preserved exactly. Adding new generators means
  appending blocks and rewriting the table and header counts (`EffectListNum`, `contentSize`).
- No sidecar (`.efs`/`.ean`/`.tex`) writing is planned.
