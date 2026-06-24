# cMaterialStandard

MT Framework **standard surface material** for the DX9 build (`DevilMayCry4_DX9.exe`).
Equivalent to `nDraw::MaterialStd` in the Special Edition / newer-engine build, but the
DX9 layout is its own thing — see [SE cross-reference](#se-cross-reference).

## Identity

| Item | Value |
|------|-------|
| DTI global | `cMaterialStandard::DTI` @ `0xEAE1E4` |
| Name string | `"cMaterialStandard"` @ `0xC08804` |
| Instance vtable | `cMaterialStandard::vftable` @ `0xC08934` |
| Alloc size | **256 bytes** (0x100) — from DTI init *and* allocator |
| DTI init | `cMaterialStandard::DTI::init` @ `0xB7D230` |
| Constructor | `cMaterialStandard::cMaterialStandard` @ `0xA628C0` |
| `newInstance` | `0xA62890` (alloc 256 / align 16 → ctor) |

### Inheritance

Primary DTI chain (verified via DTI `+0x10` parent links):

```
MtObject  ->  cMaterial  ->  cMaterialStandard
```

- `cMaterial::DTI` (`0xEAE1C4`) parent = `MtObject::DTI` (`0xE5C5A8`).
- `cMaterialStandard::DTI` parent = `cMaterial::DTI`, parent_idx 0.

The destructor's final vtable write is `cTrans::vftable_0`, so **`cTrans` is a
secondary base / embedded sub-object** in the C++ layout (multiple inheritance),
distinct from the single-inheritance DTI chain above. `cMaterial` itself begins
`cMaterial::cMaterial` by writing `cMaterial::vftable` and is 0x60 bytes.

## cMaterial base layout (96 bytes)

The embedded base (`cMaterialStandard.base`). Mapped from `cMaterial::cMaterial`
(`0xA61640`), `cMaterial::buildRenderState` (`0xA61D00`), `decodeStateKey` (`0xA61DD0`),
and the population in `uModel::setMaterials` (`0x9E7410`). DX9 has its own layout — the
SE `nDraw::Material` bitfield names (mTechnique/mDrawPass/mFogEnable/…) are concept-only
and do **not** map onto these offsets.

| Off | Field | Init | Evidence / role |
|-----|-------|------|-----------------|
| 0x00 | `vftable` | `cMaterial::vftable` | ctor |
| 0x04 | `mFlags` (packed) | mode=1, byte1=8, bits via `\|0x58000000` | byte0 = blend/draw mode (1/2/4/8/16); byte1 = lighting/blend submode; byte2 from rModel; bits24–27 = format/shadow/CRC-driven flags. Drives `buildRenderState`. |
| 0x08 | `mRefCount` | 1 | `InterlockedDecrement(*(mat+8))` on swap in setMaterials → cResource-style refcount |
| 0x0C | `mTechniqueID` | −1 | selects shader technique descriptor in `decodeStateKey` (`sShader+ID*4+0x4838`) |
| 0x10 | `mStateKey` | via `decodeStateKey(0)` | packed permutation key; unpacked into `mStateSelectors` |
| 0x14 | `mRenderState0` | by buildRenderState | packed D3D9 RS word (`0x01220122`, `0x02A202xx`) |
| 0x18 | `mRenderState1` | by buildRenderState | packed D3D9 RS word (`0x27D0xxxx`) |
| 0x1C | `mpBaseTex` (`cResource*`) | 0 | base/diffuse texture (rModel rec `+0x18`); release/addRef on swap — an **11th** texture slot beyond cMaterialStandard's 10 |
| 0x20 | `mAlpha` (float) | 1.0f | opacity scalar (role inferred from init; no read traced yet) |
| 0x24 | `dword24` | — | |
| 0x28 | `gap28[8]` | — | |
| 0x30 | `mDiffuseColor` (MtColorF) | (1,1,1,1) | ctor; setMaterials writes RGB=1 + A from rModel rec `+0x3C` |
| 0x40 | `mColor2` (MtColorF) | = mDiffuseColor | ctor copies 0x30 → 0x40 |
| 0x50 | `field_50` (byte) | — | |
| 0x51 | `mStateSelectors[15]` | by decodeStateKey | per-component selector bytes (count from technique descriptor) |

### cMaterial::buildRenderState (0xA61D00)

Translates `mFlags` (+0x04) into the two packed render-state words `mRenderState0`
(+0x14) / `mRenderState1` (+0x18). `switch (mFlags & 0xFF)` on the blend/draw mode:
modes 1/2 set `mRenderState0 = 0x01220122` and an opaque/blend base in `mRenderState1`;
modes 4/8 pick an alpha-test variant `0x02A202{25,65,…}` for `mRenderState0` selected by
`(mFlags >> 8) & 7`. `mFlags` bit 26 (`>>26 & 2`) toggles a state bit. Called by the ctor
and on every `mFlags` change in `setMaterials`.

### mFlags (cMaterial +0x04) bit map

Enumerated from the writes in `uModel::setMaterials` (disasm `0x9E7B40`–`0x9E7D2F`) and
the reads in `buildRenderState`. Source is the rModel material record's first dword,
`rec.word0 = *(rModelMatRecord)`, plus the record byte at `+0x94`.

| Bits | Field | Source |
|------|-------|--------|
| 0–7 (byte0) | **blend/draw mode** | `(rec.word0 >> 2) & 0xFFF` mapped via jumptable → {1→0x10, 8→0x02, 0x10→0x01, 0x20→0x04, 0x40→0x08}. Switch key in `buildRenderState`. |
| 8–15 (byte1) | **lighting / alpha-test submode** | `rec[+0x94]` byte; read by `buildRenderState` as `(mFlags >> 8) & 7` to pick the `0x02A202xx` variant |
| 16–23 (byte2) | **flags2** | `(rec.word0 >> 14) & 0xFF` |
| 24 | alpha-test category A | set (clearing 25,26) when computed `mRenderState0 == 0x02A20225` |
| 25 | alpha-test category B | set (clearing 24,26) when `mRenderState0 == 0x02A20265` |
| 26 | RS toggle | read by `buildRenderState` as `(mFlags >> 26) & 2` → OR'd into the render-state word |
| 27 | **two-sided / flag** | `rec.word0` bit 0 → copied to mFlags bit 27 |
| 28,30 | ctor presets | ctor seeds byte3 with `0x58` (bits 27,28,30) before setMaterials overwrites 24–27 |

### mFlags68 (cMaterialStandard +0x68) bit map

A second flags/selector word on the derived class (separate from `mFlags`). Drives a
parallax/detail LOD bias computed against the environment texture's mip count.

| Bits | Field | Source |
|------|-------|--------|
| 0 | flag | `rec.word0 & 1` |
| 1–3 (mask 0xE) | **detail/parallax level** | `(rec.word0 >> 21) & 7`; used as `(mFlags68 >> 1) & 7`, added to `((envTex.fmt >> 20) & 0xF) - 6`, clamped ≥0, stored as float at `+0x60` |
| 4 (mask 0x10) | flag | `(rec.word0 >> 30) & 1` |

## Instance vtable (10 slots @ 0xC08934)

Older/smaller interface than SE's 22-slot `MaterialStd_vtbl`. Slots 10+ are unrelated
string data, not vtable entries.

| Slot | Off | Target | Role |
|------|-----|--------|------|
| 0 | +0x00 | `0xA62A80` `cMaterialStandard::dtor` | destructor; releases 10 textures |
| 1 | +0x04 | `0x8FC2F0` | `return 0;` stub |
| 2 | +0x08 | `0x521BF0` | `return 1;` stub (isEnable-style) |
| 3 | +0x0C | `0xA63B60` `cMaterialStandard::createProperty` | editor property registration |
| 4 | +0x10 | `0xA626E0` `cMaterialStandard::getDTI` | returns `&cMaterialStandard::DTI` |
| 5 | +0x14 | `0xA62BC0` `cMaterialStandard::setDrawState` | sets draw/pass state from type byte (+0x55) |
| 6 | +0x18 | `0xA62C30` `cMaterialStandard::beginDraw` | uploads params+textures to shader constants |
| 7 | +0x1C | `0xA63890` `cMaterialStandard::duplicate` | clone (copy + addRef textures) |
| 8 | +0x20 | `0x410360` | **shared stub, mislabeled** — see caveat |
| 9 | +0x24 | `0xA62890` `cMaterialStandard::newInstance` | allocate + construct |

> **Slot 8 caveat:** IDA names `0x410360` as `sMediator::sMediator`, but disassembly
> shows a tiny shared stub (`test arg&1; mov [this], sDevil4Pad::vftable; optional
> free; ret`) aliased into many class vtables. It is **not** sMediator's constructor.
> Treat it as a shared base no-op/scalar-deleting stub.

## Field layout (256 bytes)

`base` is the embedded `cMaterial` (0x00–0x5F). Material-specific fields begin at 0x60.
Float/vec field names were **traced** from the per-property accessor stubs referenced by
`createProperty` (not assumed from registration order). Texture offsets were traced from
the dtor releases, the `duplicate` addRefs, and the texture-property registrar handlers.

| Off | Field | Source / notes |
|-----|-------|----------------|
| 0x00 | `cMaterial base` | embedded base (vtable at +0x00) |
| 0x60 | `mDetailLodBias` (float) | ctor = 0; setMaterials computes from `mFlags68` bits 1-3 + env-tex mip |
| 0x64 | `mBaseBlendFactor` (float) | prop "BaseBlendFactor" |
| 0x68 | `mFlags68` (uint bitfield) | ctor masks `&0x1F \| 1`; see [mFlags68 bit map](#mflags68-cmaterialstandard-0x68-bit-map) |
| 0x70 | `mLightMapFactor` X/Y/Z | prop "LightMapFactor"; ctor X/Y/Z = 1.0f |
| 0x7C | `dword7C` (float) | ctor = 0 |
| 0x80 | `mDetailPower` (float) | prop "DetailPower" |
| 0x84 | `mDetailWrap` (float) | prop "DetailWrap" |
| 0x88 | `dword88` | ctor = 0 |
| 0x8C | `mAmbientOccBias` (float) | prop "AmbientOccBias"; ctor = **0.5f** |
| 0x90 | `mFresnelFactor` (float) | prop "FresnelFactor" |
| 0x94 | `mFresnelBias` (float) | prop "FresnelBias" |
| 0x98 | `mSpecularPow` (float) | prop "SpecularPow" |
| 0x9C | `mEnvMapPower` (float) | prop "EnvMapPower" |
| 0xA0 | `mParallaxFactor` X/Y (vec2) | prop "ParallaxFactor" |
| 0xA8 | `mNormalMapFlip` (float) | prop "NormalMapFlip"; ctor = **1.0f** |
| 0xAC | `dwordAC` | ctor = 0 |
| 0xB0 | `mUVOffset0` X/Y (vec2) | prop "UVOffset0" |
| 0xC0 | `mUVOffset1` X/Y (vec2) | prop "UVOffset1" |
| 0xC8 | `mUVOffset2` X/Y (vec2) | prop "UVOffset2" |
| 0xD0–0xF4 | **texture-resource block** | 10× `cResource*` |
| 0xF8, 0xFC | `dwordF8`, `dwordFC` | untouched by any analyzed function; padding to 256 |

> Earlier the IDB typed 0xB0 and 0xC0 as `MtMath::MtVector4`; the accessors prove they
> are 2-float UV offsets (vec2), so they were re-typed as paired floats.

### Texture-resource block (0xD0–0xF4)

10 `cResource*` slots. Released individually in the dtor and `addRef`'d in `duplicate`.
The property registrars bind texture maps here, but a single editor property spans
multiple handler offsets, so a strict per-map naming was **not** asserted. Confirmed:

- 0xE8 = **Environment map** (only single-offset texture handler).
- The other 9 slots are Bump/normal, Specular, and Lighting/light-map variants.

## decodeStateKey / sub_A61DD0 (0xA61DD0)

`cMaterialStandard::decodeStateKey(packed@<eax>, mat)` — `__userpurge`, callee-pops 4
(`retn 4`). Mixed-radix unpack of a compact material/shader-permutation key into the
per-feature selector bytes the renderer indexes.

1. Stores the packed 32-bit key at `cMaterial+0x10` (`base.gap10`).
2. Selects a **shader technique descriptor** using the material's technique ID at
   `cMaterial+0x0C` (`base.dwordC`):
   `desc = *(sShader::mpInstance + dwordC*4 + 0x4838)`.
3. Reads component count `N = desc[+0x10][+0x04]`; the per-component records are a
   12-byte-stride array at `desc[+0x10][+0x14]`.
4. Loops `i = N-1 .. 0`, positional/mixed-radix decode:
   - `radix = record[12*i + 4] & 0xFFFFFF` (low 24 bits = that component's range)
   - `cMaterial[0x51 + i] = (byte)(packed / radix)`
   - `packed %= radix` (remainder carries to the next lower component)
   - returns final remainder.

Net effect: expands one packed key into a run of byte selectors at `cMaterial+0x51…`,
where each component's radix comes from the technique descriptor chosen by `+0x0C`.

**Callers (confirm the role):**
- `cMaterialStandard::cMaterialStandard` @ `0xA628DE`: `decodeStateKey(0, this)` —
  zero-init the selectors against the default technique.
- `uModel::setMaterials` @ `0x9E7CD2`: `decodeStateKey(rModelMatRecord[+0xC], mat)` —
  decode the real packed key loaded from the model's material record.
- `cMaterialStandard::beginDraw` @ `0xA6387B` (tail call): `decodeStateKey(this[+0x10], this)`
  — re-decode the stored key at draw time.

This also clarifies two base fields: `cMaterial+0x0C` is the **technique/material ID**
(default `-1`, set by `setMaterials`) and `cMaterial+0x10` holds the **packed state key**.

## beginDraw (0xA62C30)

The render-time workhorse. For the active shader context (`param_2`) it conditionally
writes each material parameter into the shader constant register table
(`param_2[2725]` indexed by `dword_E555xx` register-index globals), only when the value
changed, then sets dirty bit `0x20000000` in `param_2[2729]`. Uploads include the color
vec4s, specular/fresnel/parallax scalars, a fog-enable flag (writes 1.0f when
`sCamera` viewport fog alpha > 0 and material flag bit set), UV-scroll matrices (when
type byte +0x55 == 6, e.g. a special pass), and the 10 texture handles. Honors
`sShader::mpInstance` global enable toggles at +26829/+26830.

## Defaults set by constructor (0xA628C0)

- `0.5f` (`0x3F000000`) → `mAmbientOccBias` (0x8C)
- `1.0f` (`0x3F800000`) → `mNormalMapFlip` (0xA8), `mLightMapFactor` X/Y/Z (0x70/74/78)
- everything else zeroed; `mFlags68` initialized to `(x & ~0x1F) | 1`

## Source: rModelMaterial record (160 bytes)

`cMaterialStandard` instances are built by `uModel::setMaterials` (`0x9E7410`) from an
array of fixed **160-byte material records** inside the model resource
(`rModel.member_0x78`, count `rModel.mMaterialNum`). The record layout matches the
**MT Framework MOD v153 material** block (cross-referenced against the community Kaitai
spec `albam_unloaded/engines/mtfw/structs/mod-153.ksy`); every offset below was also
verified against the `setMaterials` disassembly. Defined in the IDB as `rModelMaterial`.

| Off | Field (.ksy name) | Type | Consumed by setMaterials → material |
|-----|-------------------|------|-------------------------------------|
| 0x00 | `mWord0` | u32 bitfield | `fog_enable:1, zwrite:1, attr:12, num:8, envmap_bias:5, vtype:3` → drives `cMaterial.mFlags` (attr→blend mode, num→byte2, fog_enable→bit27) and `mFlags68` (vtype, envmap_bias) |
| 0x04 | `mFuncBits` | u32 bitfield | `func_skin/lighting/normalmap/specular/lightmap/multitexture` (4 bits each); `& 0x3C00` picks additionalmap routing |
| 0x08 | `mHTechnique` | u32 | htechnique |
| 0x0C | `mPipeline` | u32 | **→ `decodeStateKey`** (selects the shader technique descriptor) |
| 0x10 | `mPVDeclBase` | u32 | vertex-decl base (see vertex-format note below) |
| 0x14 | `mPVDecl` | u32 | vertex-decl (see vertex-format note below) |
| 0x18 | `mBaseMap` | u32 tex id | → `cMaterial.mpBaseTex` (+0x1C) |
| 0x1C | `mNormalMap` | u32 tex id | → `mpTex_D0` |
| 0x20 | `mMaskMap` | u32 tex id | → `mpTex_D4` |
| 0x24 | `mLightMap` | u32 tex id | → `mpTex_DC` |
| 0x28 | `mShadowMap` | u32 tex id | → `mpTex_D8` |
| 0x2C | `mAdditionalMap` | u32 tex id | → `mpTex_F4`, or `mpTex_EC` when `(mFuncBits & 0x3C00) == 0x800` |
| 0x30 | `mEnvMap` | u32 tex id | → `mpTex_E8` (**Environment** — independently confirmed earlier) |
| 0x34 | `mHeightMap` | u32 tex id | → `mpTex_EC` |
| 0x38 | `mGlossMap` | u32 tex id | → `mpTex_F0` |
| 0x3C | `mTransparency` | f32 | → `cMaterial.mDiffuseColor.w` (+0x3C) |
| 0x40 | `mFresnelFactor[4]` | f32×4 | → FresnelFactor (0x90), FresnelBias (0x94), SpecularPow (0x98) |
| 0x50 | `mLightMapFactor[4]` | f32×4 | → `mLightMapFactor` (0x70/74/78) |
| 0x60 | `mDetailFactor[4]` | f32×4 | → DetailPower (0x80), DetailWrap (0x84), AmbientOccBias (0x8C from `[+0x6C]`) |
| 0x70 | `mTransmitFactor[4]` | f32×4 | → material +0x70..0x7C |
| 0x80 | `mParallaxFactor[4]` | f32×4 | → ParallaxFactor (0xA0/A4); `[+0x88]` sign → NormalMapFlip (0xA8) |
| 0x90 | `mBlendState` | u32 | `0x02A202xx` render-state tag → sets `mFlags` alpha-test bits 24/25 |
| 0x94 | `mAlphaRef` | u32 | low byte → `cMaterial.mFlags` byte1 |
| 0x98 | `mReserved2[0]` | u32 | reserved |
| 0x9C | `mReserved2[1]` | u32 | read as the `mpTex_E0` source in setMaterials |

Total **0xA0 = 160 bytes** — matches the `160 * i` stride in `setMaterials` and the
`.ksy` `size_ = 160`.

> **Naming caveat:** the field *names* (basemap, glossmap, vtype, …) come from the
> community `.ksy` spec, not from DX9 symbols. The **offsets and the data flow** are
> verified against the binary; the names are adopted as plausible labels. The `.ksy`
> author also flags the vertex-format (`vtype`) enumeration as guesswork — so `vtype`'s
> exact value→format meaning is **not** treated as authoritative here. What the binary
> *does* show: `vtype` (`mWord0` bits 21–23) feeds the `mFlags68` detail/parallax
> LOD-bias path, and `mPVDeclBase`/`mPVDecl` (0x10/0x14) are the vertex-declaration ids.
> The vertex-format decode is now done — see [vertex_format.md](vertex_format.md).
> `mPVDecl`/`mPVDeclBase` (record +0x14/+0x10) are pointers to packed u32 element-code
> arrays consumed by `cTrans::VertexDecl::create` / `::build`.

## SE cross-reference

SE (`DevilMayCry4SpecialEdition.exe`, leaked PDB, port 13338) calls this class
`nDraw::MaterialStd` with variants `MaterialStdDM`, `MaterialStdPN`, `MaterialStdEst`.
The SE struct is **160 bytes** and uses D3D11-style state objects
(`BlendState`/`RasterizerState`/`DepthStencilState`), so its layout does **not** map
1:1 onto the DX9 fixed-function 256-byte layout. SE is useful for the method-name
vocabulary only (setBaseColor, getBaseMap, beginDraw/endDraw, setDrawState, the
`set*Animation` family). The separate `cMaterialHandler` (288 B in DX9, 336 B in SE) is
a higher-level wrapper with toggles like `setTransparencyEnable`, `setZWriteEnable`,
`setSpecularEnable`, `setUVEnable` — not the same class.

## Usage lead (not exhaustively chased)

`cMaterialStandard::DTI` is referenced by `uModel::transDevilTrigger` (`0x9F3060`),
i.e. materials are swapped/recolored during Devil Trigger transformation. Also
referenced by `sub_5283E0`. Left as leads per scope.

## Annotations applied to the IDB

- Renamed vtable functions: `dtor`, `newInstance`, `setDrawState`, `beginDraw`,
  `duplicate`, `createProperty` (all under `cMaterialStandard::`).
- Redeclared `cMaterialStandard` struct (256 B) with traced field names.
- Added explanatory comments on the 5 renamed funcs + the slot-8 stub caveat.
- Renamed `cMaterial::buildRenderState` (`0xA61D00`), `cMaterialStandard::decodeStateKey`
  (`0xA61DD0`); redeclared `cMaterial` (96 B) with named fields.
- Defined `rModelMaterial` (160 B) struct from the MOD v153 layout + setMaterials trace;
  commented the record access in `setMaterials`.
