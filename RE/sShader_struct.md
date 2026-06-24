# sShader — shader/effect manager singleton

Cross-referenced from the **PS3 debug build** (leaked-PDB symbols = ground-truth names) and
validated against the **DX9** constructor + accessor functions for the actual DX9 offsets.

> ⚠️ Layouts diverge: DX9 `sShader` = **26912 B** (alloc in `sDevil4Main::sDevil4Main` @ `0x8AE235`),
> PS3 = **23744 B**. DX9 has 4× larger envelope arrays (512 vs 128 entries) and 512-slot ParameterDesc/
> TechniqueDesc (PS3 also 512). Names from PS3; every offset below is from DX9 disassembly.

## Constructors / singleton

| | Address | Note |
|--|---------|------|
| DX9 ctor | `0x8FC9B0` | `sShader* __stdcall sShader::sShader(sShader*)` |
| singleton | `sShader::mpInstance` @ `0xE55700` | typed `sShader*` |

## Accessor functions (params retyped to sShader*)

The singleton flows into accessors only as a stack arg; these were retyped so field names propagate:

| Address | Name | sShader* arg |
|---------|------|--------------|
| `0x8FE1E0` | `sShader::getParameterFromName(this, id, type, reg_count)` | `this` (171 call sites) |
| `0x8FE130` | `sShader::getTechniqueFromName(this@<eax>, id)` | `this` |
| `0x8FEC80` | `sShader::allocEnvelope(size@<eax>, this)` | `this` (scans `mEnvelope[]` for free bits) |
| `0x8FE4A0` | `sub_8FE4A0(cTrans*@<esi>, pShader, float*)` | `pShader` (per-draw constant upload) |

(146 other functions read `sShader::mpInstance` directly and already resolve via the typed global.)

## Key accessors that pin the layout

- `getParameterFromName` `sub_8FE1E0`: reads `mParameterNum` @ `+0x6038`, scans `mParameterDesc[].mID`
  starting `+0x840` (= ParameterDesc base 0x838 + mID@8) stride 20. Returns the index (the param's runtime ID slot).
- `getTechniqueFromName` `sub_8FE130`: reads `mTechniqueNum` @ `+0x603C`, scans `mTechniqueDesc[].mID`
  @ `+0x3040` stride 12; writes `mpTechnique[]` @ `+0x4838`.

## DX9 layout (validated)

| Offset | Field | Type | Evidence |
|--------|-------|------|----------|
| 0x0000 | cSystem base | cSystem (32B) | vftable `off_C03498`, CRITICAL_SECTION |
| 0x0024 | mpEnvelopeTex[4] | void*[4] | PS3 name |
| 0x0034 | mEnvelopeFlag[510] | u32[510] | header gap to 0x82C (DX9-enlarged; exact count approx) |
| 0x082C | mpRenderTargetTex | void* | ctor `*(this+2092)=v15` (created render target) |
| 0x0830 | mDrawCounter | long | `InterlockedIncrement` target in `sub_8FE4A0` (was mis-read as padding; the accessor-retype pass surfaced it) |
| 0x0834 | mpEnvelopeScratchTex | void* | ctor `[ebx+834h]` optional envelope texture |
| 0x0838 | mParameterDesc[512] | ParameterDesc[512] | init loop stride 20; base confirmed by accessor |
| 0x3038 | mTechniqueDesc[512] | TechniqueDesc[512] | init loop stride 12; base confirmed by accessor |
| 0x4838 | mpTechnique[512] | void*[512] | getTechniqueFromName write base |
| 0x5038 | mSamplerState[256] | u8[4096] (16B×256) | boundary chains from arrays above |
| 0x6038 | mParameterNum | u32 | getParameterFromName counter |
| 0x603C | mTechniqueNum | u32 | getTechniqueFromName counter |
| 0x6040 | mSamplerStateNum | u32 | PS3 order |
| 0x6044 | mParameterChange | u32 | PS3 order |
| 0x6048 | mTechniqueChange | u32 | PS3 order |
| 0x604C | mTextureChange | u32 | PS3 order |
| 0x6050 | mBufferChange | u32 | PS3 order |
| 0x6054 | mDebugView | s32 | ctor `= -1` (matches PS3 s32 init) |
| 0x6058 | mpShaderArchive | void* | ctor `sResource::create(..,"system\shader")` |
| 0x605C | mEnvelope[512] | u32[512] | ctor memset 0x800 |
| 0x685C | mpEnvelopeBase | u8* | PS3 name |
| 0x6860 | mEnvelopePitch | u32 | PS3 name |
| 0x6868 | mpSysTexture[6] | void*[6] | ctor: NullWhite/NullBlack/NullNormal/DefaultCube/font/XfPCFNoise |
| 0x6880 | mpVertexDecl[17] | void*[17] | ctor: 17 `cTrans::VertexDecl::create` results (PS3 had 12) |
| 0x68C6..0x68CB | mDisableBaseMap..mDisableEnvMap | bool×6 | PS3 names |
| 0x68CD | mNormalMapping | bool | property reg "NormalMapping" type 3 (BOOL) |
| 0x68CE | mSpecular | bool | property reg "Specular" type 3 |
| 0x68CF | mDepthTexture | bool | property reg "DepthTexture" type 3 |
| 0x68E0 | mShadowQuality | u32 | property reg "ShadowQuality" type 6 (U32) |
| 0x68EC | mTextureDetail | u32 | property reg "TextureDetail" type 6 |
| 0x6910 | mTestParam | MtVector4 | PS3 name; ctor stores vec |

Property registrations also create app enum items (callbacks): "TextureFilter", "MotionBlurQuality",
"Lighting", "FilterQuality", "FurQuality" (function-backed, not direct fields).

### Unresolved (left as placeholders)
- `mEnvelopeFlag` exact element count (510 fills the header gap; DX9 envelope system is 4× PS3's).
- `_field68D0..68DC`, `_flag68CC/68E4/68E5`, `_field68F0..6900` — set in ctor but no PS3 name / property reg.
- DX9 lacks `MT_CTSTR`/`XFUNIQUE`/`cTrans::PARAM_DATA`/`SAMPLERSTATE` named types → modelled as
  `const char*` / `uint` / raw bytes.

## Nested types (defined in DX9)

`sShader::ParameterDesc` (20B): `mtObjectVftable, mName(char*), mID(u32), mType(u8), mRegCount(u8),
mStateHandle(u8), mReserved(u8), mDefault(u32)`.
`sShader::TechniqueDesc` (12B): `mtObjectVftable, mName(char*), mID(u32)`.

See [`sShader_name_hash.md`](sShader_name_hash.md) + [`sShader_hash_ids.json`](sShader_hash_ids.json)
for the `mID` (XFUNIQUE) values of all 487 parameter/technique names.
