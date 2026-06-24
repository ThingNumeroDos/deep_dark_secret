# sPrim — Primitive / 2D-3D scene drawing singleton

Cross-referenced from the **PS3 debug build** (`Devil4.self`, port 13338) which carries a
leaked-PDB-symbolized `sPrim` (ground truth for field *names*), validated against the
**DX9** constructor (`sPrim::sPrim` @ `0xA340E0`) for the actual DX9 *offsets*.

> ⚠️ Offsets and sizes differ between DX9 and the PS3 build. PS3 supplies names only;
> every offset below is taken from the DX9 constructor disassembly, not copied from PS3.

## Constructors

| Build | Address | Signature |
|-------|---------|-----------|
| DX9   | `0xA340E0` | `sPrim* __stdcall sPrim::sPrim(sPrim* this)` (no tag_size arg; uses fixed `mNumOfTags=0x10000`) |
| PS3   | `0x29E3A0` | `void sPrim::sPrim(sPrim* this, u32 tag_size)` |

## DX9 constructor field map (evidence-backed)

Header (shared with PS3 through ~0x54; DX9 inserts extra fields afterward):

| DX9 off | Field | Type | Ctor evidence |
|--------|-------|------|---------------|
| 0x00 | vftable (cSystem → sPrim) | void* | `this->vftable = &sPrim::vftable` |
| 0x04 | mCS (CRITICAL_SECTION) | — | `InitializeCriticalSection` |
| ...  | mThreadSafe | bool | `this->mThreadSafe = 0` |
| 0x70 | mSceneContext[32] | SCENECONTEXT[32] | scene-context init loop (n31=31; stride 0x3C dwords = 0xF0=240B) |
| 0x1E74 | mpPrim[8] | sPrim::Prim*[8] | alloc loop, 8 prims × 0x60, fills Prim vftable/mViewVec/etc. (PS3 has 6) |
| 0x1E94 | mpTag | u8* | alloc 0x80000 bytes |
| 0x1E98 | mNumOfTags | uint | `= 0x10000` |
| 0x1E9C | mpUnifiedTag0 | u8* | alloc 8*mNumOfTags |
| 0x1EA0 | mpUnifiedTag1 | u8* | alloc 8*mNumOfTags |
| 0x1EA4 | mUnifiedTagNum | uint | `= 0` |
| 0x1EA8 | mhTechnique | uint | technique handle for "tXfPrimStandard" |

Counters / params (header region):

| DX9 off | Field | Type | Value |
|--------|-------|------|-------|
| 0x20 | mPrimNum | uint | 0 |
| 0x24 | mDrawPrimitiveNum | uint | 0 |
| 0x28 | mDrawSplitNum | uint | 0 |
| 0x2C | mDepthSplitNum | uint | (not set in ctor) |
| 0x30 | mStateChangeNum | uint | 0 |
| 0x34 | mTextureChangeNum | uint | 0 |
| 0x38 | mNearStart | float | 256.0 |
| 0x3C | mNearEnd | float | 512.0 |
| 0x40 | mFarStart | float | 1024.0 |
| 0x44 | mFarEnd | float | 2048.0 |
| 0x48 | mReductionDist | uint | 2000 |
| 0x4C | mVolumeScale | float | 10.0 |
| 0x50 | mParallaxScale | float | 1.0 |
| 0x54 | mParallaxMinLoop | uint | 4 |
| 0x58 | mParallaxMaxLoop | uint | 16 |
| 0x5C | mParallaxFadeStart | float | ::mParallaxFadeStart |
| 0x60 | mParallaxFadeEnd | float | 1600.0 |
| 0x64 | mDynamicReductionControl | bool | 1 |
| 0x68 | mVolumeEnable | bool | 1 |
| 0x6C | mParallaxEnable | bool | 1 |

> Parallax block (0x50–0x60, mParallax*), virtual-screen, and mVolumeEnable/mParallaxEnable
> are **DX9-only** — absent from the PS3 layout. DX9's SCENECONTEXT is 240B (PS3: 208B).

Shader-parameter handles (DX9 stores `uint` param indices; PS3 uses `XFHANDLE`):

| DX9 off | Field | PS3 name | Shader param string |
|--------|-------|----------|---------------------|
| 0x4EB8 | mVirtualScrW | — | `= 1280` |
| 0x4EBC | mVirtualScrH | — | `= 720` |
| 0x4EC0 | mScreenLayout | — (DX9-only) | `= 0`; see resolution below |
| 0x4EC4 | mTrans (bool) | mTrans | `= 1`; see resolution below |
| 0x4EC8 | mpVertexDecl | mpVertexDecl | cTrans::VertexDecl::create |
| 0x4ECC | mhViewZ | mhViewZ | "ViewZ" |
| 0x4ED0 | mhInvViewportSize | mhInvViewportSize | "InvViewportSize" |
| 0x4ED4 | mhInvTextureSize | mhInvTextureSize | "InvTextureSize" |
| 0x4ED8 | mhZofsTrans | mhZofsTrans | "ZofsTrans" |
| 0x4EDC | mhDepthBlend | mhDepthBlend | "DepthBlend" |
| 0x4EE0 | mhVolumeDepth | mhVolumeDepth | "gXfVolumeDepth" |
| 0x4EE4 | mhParallaxFactor | — (DX9-only) | "ParallaxFactor" |
| 0x4EE8 | mhParallaxFade | — (DX9-only) | "ParallaxFade" |
| 0x4EEC | mhSceneTexture | mhSceneTexture | "XfPrimSceneSampler" |
| 0x4EF0 | mhPrimType0 | mhPrimType0 | "gXfPrimType0" |
| 0x4EF4 | mhPrimType1 | mhPrimType1 | "gXfPrimType1" |
| 0x4EF8 | mhPrimType2 | mhPrimType2 | "gXfPrimType2" |
| 0x4EFC | mhPrimDepthBlend | mhPrimDepthBlend | "gXfPrimDepthBlend" |
| 0x4F00 | mhBaseTexture0 | mhBaseTexture0 | "XfPrimBasePointSampler" |
| 0x4F04 | mhBaseTexture1 | mhBaseTexture1 | "XfPrimBaseLinearSampler" |
| 0x4F08 | mhNormalTexture1 | mhNormalTexture1 | "XfPrimNormalLinearSampler" |
| 0x4F0C | mhMaskTexture1 | mhMaskTexture1 | "XfPrimMaskLinearSampler" |
| 0x4F10 | mhDepthTexture | mhDepthTexture | "XfPrimDepthPointSampler" |

Tail (after 0x4F10) sets sampler-state bits on the shader instance, then `addEnumItem("EffectQuality")`.
DX9 struct ends at 0x4F20 (20256 B). The PS3 RSX vertex/index-buffer block (mpVertexBuffer/
mpIndexBuffer/mVBStackIndex/etc.) is **PS3-only** and has no DX9 counterpart.

## Resolution of 0x4EC0 / 0x4EC4 (previously unknown)

These two have no PS3 equivalent at the same offset, so they were resolved from DX9 evidence —
including the game's **own property-registration table** in `sub_A37BE0`, which registers each
field by its real string name:

- **0x4EC0 `mScreenLayout`** (uint) — registered as `"mScreenLayout"` (type 6) at `0xA37EA0`.
  Gates virtual-screen sizing: in the text-draw path `sub_49A990` @ `0x49AACE`,
  `if (mScreenLayout) use mVirtualScrW; else use sRender real width`. Ctor sets 0;
  `sDevil4Main::sDevil4Main` @ `0x8AE343` then sets it to **2**.
- **0x4EC4 `mTrans`** (bool, read as byte) — registered as `"mTrans"` (type 3) at `0xA384D5`;
  **same name as PS3 `mTrans`** (PS3 @ 0x4A9D). Read as a byte boolean in the threaded prim-draw
  dispatcher `sub_A35280` @ `0xA3528F` (`if (sPrim->mTrans) { … sMain::executeJob … }`) — gates
  the multi-job split of primitive drawing. Ctor sets 1.

## sPrim::Prim (96 B, name source = PS3 `sPrim::Prim`, same size both builds)

| Off | Field | Type | Note |
|----|-------|------|------|
| 0x00 | mtObjectVftable | uint | MtObject vftable; ctor writes `&sPrim::Prim::vftable` |
| 0x04 | mTagSize | uint | ctor `= 0` |
| 0x08 | mTagNum | uint | ctor `= 0` |
| 0x0C | mpTag | void* (PS3: Tag*) | ctor `= 0`; Tag union is PS3-only |
| 0x10 | mpTrans | cTrans* | |
| 0x14 | _pad14[12] | — | alignment before 16B-aligned mViewVec (unnamed in PS3 too) |
| 0x20 | mViewVec | MtVector4 | ctor copies `local_b0` |
| 0x30 | mTexHandle | uint | |
| 0x34 | mDisp_lv | uint | (DX9 had `mDisp_lvl`) |
| 0x38 | mSubPriority | uint | |
| 0x3C | mPrimPacketBorder | uint | (was byte in DX9; PS3 = u32) |
| 0x40 | mCommandPacketMergin | uint | newly named from PS3 (was placeholder) |
| 0x44 | mMetaData | METADATA_HEAD | ctor `= 0` |
| 0x4C | mModelMaterial | uint | ctor `= 0` |
| 0x50 | mpModel | rModel* | ctor `= -1` (init to invalid) |
| 0x54 | member_0x54 | uint | ctor `= 0`; **no PS3 name** (PS3 tail 0x54–0x5F unnamed) |
| 0x58 | _pad58[8] | — | trailing pad to 96 B |
