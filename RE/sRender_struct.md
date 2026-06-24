# sRender — renderer / present singleton

Cross-referenced from the **PS3 debug build** (leaked-PDB symbols = ground-truth names) and
validated against the **DX9** constructor / init / destructor for the actual DX9 offsets.

> ⚠️ **Heavy GCM↔D3D9 divergence.** DX9 `sRender` = **117264 B**, PS3 = **110704 B**.
> The PS3 build is RSX/GCM (PlayStation graphics hardware); the DX9 build is Direct3D 9.
> The PS3 layout's lower-half (blend-state mirror @0x15260+, `mTile`/`TileArea`, `mTiledStateList`/
> `TILED_STATE[256]`, `mFence`, `mpVramBuffer`, `ZcullArea`, `CellGcmSurface`, GCM contexts) is
> **PS3-exclusive** and does **not** exist in DX9, which holds D3D9 device/swapchain/caps state instead.
> Only the engine-portable upper region (flags, gamma, trans array, passes, temp textures, screen
> textures, element table) maps name-for-name. Every DX9 offset below is anchored on a DX9
> ctor write, `initDevice` write, or destructor access — **never** copied from PS3 offsets.

## Constructors / singleton

| | Address | Note |
|--|---------|------|
| DX9 ctor | `0x8EF930` | `sRender::sRender(this, displayFlags, memBudget, a4)` |
| DX9 device init | `0x8EF2E0` | `sRender::initDevice(this@<eax>, displayFlags)` — `Direct3DCreate9` + `CreateDevice` |
| DX9 dtor | `0x8F05C0` | `sRender::~sRender(this)` |
| singleton | `sRender::mpInstance` @ `0xE552D8` | typed `sRender*` |

`displayFlags` (ctor arg2 / `param_3`): bit0=640×480, bit1=1280×720, bit2=1920×1080, bit3=HDR/SLI.
`memBudget` (arg3 / `param_4`): command-buffer size = `(memBudget >> 1) - 0x80000`.

## Nested types (defined in DX9)

`sRender::Pass` (**140 B** — PS3 is 132 B): `mtObjectVftable, mEnable(bool), mName(char*),
mFillMode(u32), mVSGPR(u32), mCounter[16], mCommand, mMesh, mMaterial, mVShader, mPShader,
mVSConstant, mPSConstant, mDrawState, mBlendState, mSamplerState, mPolygon, mPrimitive, mClear,
mResolve`. DX9 widens `mCounter` from PS3's `[14]` to `[16]` (accounts for the +8 B); ctor sets
`mVSGPR=64`, `mFillMode=2`, `mEnable=1`, zeroes the 14 command-handle dwords (0x54..0x88).

`sRender::TempTexture` (**16 B**, matches PS3): `mtObjectVftable, mPoolName(char*), mName(char*),
mpTexture`.

### The 12 render passes (`mPasses[12]`, names from `off_E16B40`)
`BEGIN, ZPASS, SOLID, NUKI, OCCLUSION, OVERLAP, TRANSPARENT, EFFECT, TRANSPARENT_NZ, FILTER,
SCREEN, END`. (PS3 had 11 passes; DX9 adds one.)

## DX9 layout (validated)

| Offset | Field | Type | Evidence |
|--------|-------|------|----------|
| 0x0000 | __vftable | void* | ctor `off_C01AA8` (cSystem base) |
| 0x0004 | mCS | MtCriticalSection (24B) | ctor `InitializeCriticalSection(+4)` |
| 0x001C | mInit | bool | ctor =0 then =1 (note: coincides w/ cSystem tail; DX9 cSystem=28B used here) |
| 0x0020 | mDeviceLost | bool | ctor =0 (PS3 `mDeviceLost`) |
| 0x0021 | mDisableRendering | bool | ctor =1 / `initDevice` = DISPLAY cfg |
| 0x0022 | mParallelTrans | bool | ctor =0 |
| 0x0023 | mParallelRendering | bool | ctor =1 |
| 0x0025 | mParallelRenderingActive | bool | ctor =1 |
| 0x0026 | mStoreFrame | bool | ctor =0 |
| 0x0028 | mPersRate | f32 | ctor =0.5f (`0x3F000000`) — matches PS3 0x28 exactly |
| 0x0030 | mDynamicTransEnable | u32 | ctor =1 |
| 0x0034 | mpDevice | IDirect3DDevice9* | `initDevice` `CreateDevice→a2+52`; dtor `Release(this+13)` |
| 0x0038 | mpD3D | IDirect3D9* | `initDevice` `Direct3DCreate9→a2+56`; dtor `Release(this+14)` |
| 0x003C | mPresentRect | MtRect (16B) | ctor zeroes 0x3C..0x48 |
| 0x0050 | mWidth | u32 | ctor =1280; `initDevice` GetClientRect/mode select |
| 0x0054 | mHeight | u32 | ctor =720 |
| 0x0058 | mThreadHandle | HANDLE | `CreateThread`; dtor `WaitForSingleObject(this+22)` |
| 0x005C | mThreadID | u32 | thread-id out param |
| 0x0060 | mRenderEvent | HANDLE | `CreateEventA` #1; dtor `SetEvent(this+24)` |
| 0x0064 | mSyncEvent | HANDLE | `CreateEventA` #2; dtor `ResetEvent(this+25)` |
| 0x0068 | mGammaR | MtEaseCurve (p1,p2) | ctor pair `dword_E14618/E1461C` (≈0.333/0.667) |
| 0x0070 | mGammaG | MtEaseCurve | ctor pair |
| 0x0078 | mGammaB | MtEaseCurve | ctor pair |
| 0x0080 | mUpdateGamma | bool | ctor =1 (PS3 0x78) |
| 0x0081 | mDynamicTrans | bool | ctor =1 |
| 0x0082 | mElementDeleted | bool | ctor =1 |
| 0x0088 | mGammaMin | f32 | ctor =0 (PS3 `mGammaMin`) |
| 0x008C | mGammaMax | f32 | (PS3 `mGammaMax`) |
| 0x0090 | mTransArray | cTrans[8] | ctor loop: 8× `cTrans::cTrans`, stride 11024 (PS3 had 6) |
| 0x15910 | mWbFlag | u32 | PS3 name (command write-buffer flag) |
| 0x1591C | mpBuffer[2] | u8*[2] | double-buffered command memory |
| 0x15924 | mpCommand[2] | void*[2] | command (TAG) pointers |
| 0x1592C | mCommandBufSize | int | ctor `=(memBudget>>1)-0x80000` |
| 0x15930 | mCommandNum0/1 | u32×2 | |
| 0x1593C | mpVB0/mpIB0/mVBParam/mIBSize | int×4 | vertex/index buffer params |
| 0x15950 | mPasses | sRender::Pass[12] | ctor loop stride 140; names from `off_E16B40` |
| 0x15FE0 | mTempTextures | sRender::TempTexture[256] | ctor loop stride 16 |
| 0x16FE0 | mTempTextureNum | u32 | ctor =0 |
| 0x16FE4 | mpTempBuffer / mTempBufSize | u8*, u32 | PS3 order |
| 0x16FEC | mpScreenTexture … mpCacheFrameTexture | void*×5 | PS3 order (0x16FEC–0x16FFC) |
| 0x17000 | mPresentInterval/mPresentThreshold | u32×2 | PS3 order |
| 0x17008 | mpBackBuffer/mpMiddleBuffer/mpFrontBuffer/mpDepthStencilBuffer | void*×4 | PS3 order |
| 0x17020 | mHDRMode | int | ctor `=(displayFlags>>3)&1` |
| 0x1703C | mQualityControl / mQuality | u32×2 | ctor =2 / =4 (PS3 `mQualityControl`/`mQuality`) |
| 0x17060 | mRenderCounter | s64 | ctor =0 (PS3 `mRenderCounter`) |
| 0x17068 | mRenderTime | s64 | (PS3 `mRenderTime`) |
| 0x17088 | mElementNum | u32 | PS3 `mElementNum` |
| 0x1708C | mpElement | void*[4096] | PS3 `mpElement[4096]` (`cTrans::Element*`); dtor walks it |
| 0x1B08C | mElementCritSec | MtCriticalSection | dtor `DeleteCriticalSection`; PS3 `mCSElement` |
| 0x1B0A8 | _unk1B0A8[5900] | bytes | **D3D9-specific** caps/window/adapter block (see initDevice) |
| 0x1C7B4 | mResolutionList | int | ctor addEnumItem "Resolution" → `this+116660` |
| 0x1C9BC | mRefreshRateData | int | ctor addEnumItem "RefreshRate" |

## D3D9-specific fields (from `initDevice` @ 0x8EF2E0, offsets relative to `this`)

These have **no** PS3/GCM analog — they hold D3D9 device, caps, and display-mode state. They live
inside the `_unk1B0A8` / mode-table region and are left as byte blocks in the struct (referenced by
absolute offset in `initDevice`):

| Offset | Meaning |
|--------|---------|
| +94192/94196 | chosen display-mode width/height |
| +94200/94204 | desktop metrics (`SM_CXSCREEN`/`SM_CYSCREEN`) |
| +94240 | MSAA / multisample type (clamped <4) |
| +111024 | back-buffer surface |
| +111028/111030 | vertex / pixel shader version caps (require ≥ 3.0) |
| +111060 | device behavior/state flags (`\|= 0x14`) |
| +111076 | back-buffer color surface |
| +111128/111132 | adapter ordinal / device type |
| +111144 | `mpShaderLog` (`shaderlog.slg`, loaded by `sub_8F15D0`) |
| +111148.. | display-mode table (stride 84) indexed by `sub_8F30E0` |
| +116660 | resolution enum list (passed to `addEnumItem`) |

## Display options (registered via `sApp::addEnumItem` in the ctor)

`RenderingThread, FPS, SLI, MSAA (AA + filter), EffectDetail, Resolution, RefreshRate, FullScreen,
VSYNC, AdjustAspect` — each backed by a getter/setter callback pair (e.g. VSYNC → `sub_8EEA50`/`sub_8EEA60`).

### Unresolved (left as placeholders)
- `_unk2C, _unk4C, _flag24/84/86` header bytes — written but no PS3 name / no accessor yet.
- `0x17018–0x1705C` mid-block (`_unk17*`) — D3D9 present/quality state, partially named
  (`mHDRMode`, `mQualityControl`, `mQuality`); the rest unproven.
- `_unk1B0A8[5900]`, `_unk1C7B8[516]`, `_unk1C9C0[80]` — D3D9 caps + display-mode tables;
  individual fields reachable only through `initDevice`'s absolute offsets (tabulated above).
