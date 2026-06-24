# uMovie::draw — Analysis

**DX9 address:** `0x9101D0` (size 0x597)  
**SE address:** `0xBE4DF0` (size 0x701, full symbols)  
**Prototype:** `void __thiscall uMovie::draw(uMovie *self, cTrans *pdraw)`

---

## Purpose

Renders one decoded video frame into `mpRenderTarget` via a YUV planar blit using a full-screen quad. Called once per frame when a cutscene/movie is playing.

---

## Pipeline (step by step)

| Step | DX9 address | Action |
|------|-------------|--------|
| 1 | `0x9101E3` | Guard: return immediately if `self->mpRenderTarget` (`self+0x48`) is NULL |
| 2 | `0x9101F9–0x910214` | Enter/leave CriticalSection; decrement `local_2e4` to obtain subscene index |
| 3 | `0x910226` | `cTrans::beginSubScene(subSceneIdx, pdraw, 1, "Movie", param)` |
| 4 | `0x91022E–0x91025E` | Read render-target texture dimensions → fill `viewport[4]` (w, h, 0, 0); call `cTrans::setupScene` |
| 5 | `0x91027B–0x910287` | Mask render-state flags in `pdraw` context (depth-state field) |
| 6 | `0x910291–0x9102BB` | `cTrans::applyRenderTarget(RT, depth, 0, 0, 0, -1, -1)` — bind RT as D3D render target |
| 7 | `0x9102CD` | **State check:** if `mpMovie` (`self+0x40`) == NULL **or** `mStatus` (`self+0x20`) != 4 → clear branch |
| 7a | `0x9106ED–0x910757` | Clear branch: if `mStatus` ∉ {5, 6} emit a clear draw command; goto endSubScene |
| 7b | `0x9102D3` | If `mAvailableTexture` (`self+0xAC`) == 0 → goto endSubScene (no decoded frame) |
| 8 | `0x9102E0–0x91033D` | Emit "clear" draw command (type 7, priority 3) into cTrans command buffer |
| 9 | `0x91033F–0x91037B` | Set technique slot (`self+0x30`) in `pdraw` texture table; dirty state flags if changed |
| 10 | `0x910387–0x910397` | Write pixel-shader constants: blend mode `0x7C7A120` / render flags `0x011FE322` |
| 11 | `0x9103A7–0x910442` | Bind YUV planes (mark `mRefFrame = nDraw__Resource__mRenderFrame` to pin D3D resource): |
| | `0x9103A7` | `pYTex = mpYTexture[mCurrentTexture]` (`self+0x6C + 4*mCurrentTexture`) → slot `ySlot` (`self+0x34`) |
| | `0x9103DF` | `pUTex = mpUTexture[mCurrentTexture]` (`self+0x78 + …`) → slot `uSlot` (`self+0x38`) |
| | `0x910417` | `pVTex = mpVTexture[mCurrentTexture]` (`self+0x84 + …`) → slot `vSlot` (`self+0x3C`) |
| 12 | `0x910451` | Fetch vertex shader from `sShader::mpInstance+0x68CC` (movie VS slot) |
| 13 | `0x910485–0x91052E` | Allocate 96 bytes on `cTrans` UP heap; fill `quadConstants[24]` (6× MtVector4: position scale/offset + YUV UV transforms) |
| 14 | `0x910549–0x9106DD` | Emit draw command (type 4): alloc 32-byte command block, attach material (`cTrans::newMaterial` if dirty), attach shader block, write quad to `drawUP` |
| 15 | `0x9106DF` | `cTrans::endSubScene` |

---

## uMovie Field Map (derived from DX9 + SE cross-reference)

| Offset | Name | Type | Notes |
|--------|------|------|-------|
| `+0x20` | `mStatus` | `int` | 4=playing, 5=pause, 6=stop |
| `+0x30` | (technique slot) | `int` | cTrans texture-table slot for technique |
| `+0x34` | `ySlot` | `int` | cTrans texture-table slot for Y plane |
| `+0x38` | `uSlot` | `int` | cTrans texture-table slot for U plane |
| `+0x3C` | `vSlot` | `int` | cTrans texture-table slot for V plane |
| `+0x40` | `mpMovie` | `rMovie*` | WMV/ASF reader object |
| `+0x48` | `mpRenderTarget` | ptr | render-target wrapper; `+0xCC` = inner `mpTexture` ptr |
| `+0x6C` | `mpYTexture[3]` | `Texture*[3]` | triple-buffered Y plane textures |
| `+0x78` | `mpUTexture[3]` | `Texture*[3]` | triple-buffered U plane textures |
| `+0x84` | `mpVTexture[3]` | `Texture*[3]` | triple-buffered V plane textures |
| `+0xA8` | `mCurrentTexture` | `int` | index into the triple-buffer arrays |
| `+0xAC` | `mAvailableTexture` | `byte` | non-zero when a decoded frame is ready |

---

## Key Globals

| Address | Name | Notes |
|---------|------|-------|
| `0xE55784` | `nDraw__Resource__mRenderFrame` | Frame counter written to `mRefFrame` to keep D3D textures alive |
| `0xE55700` | `sShader::mpInstance` | Shader singleton; `+0x68CC` = movie vertex shader |
| `0xEAC668` | `dword_EAC668` | cTrans draw-command technique descriptor for clear |

---

## DX9 vs SE Differences

| Aspect | DX9 | SE (reference) |
|--------|-----|----------------|
| Render abstraction | `cTrans` (DX9) | `cDraw` (DX11) |
| Clear guard | Always clears when `mStatus ∉ {5,6}` | Additional `mClear` flag gates the clear |
| State-dirty mechanism | Raw bitmask ops on `pdraw[2729]` / `pdraw[2724]` | Named `mContext.sstate` field with typed enum |
| Vertex data | 96-byte `quadConstants` array memcpy'd to UP heap | `cDraw::drawUP` with 4 verts × 16 bytes inline |
| Shader-block emit | Explicit 92-byte `pShaderBlock` struct built by hand | `cDraw::beginDraw` / `cDraw::endDraw` wrappers |
| SRGB path | Not present | Branches on `sRender::mSRGBEnable` for sampler state |
| Subscene naming | `"Movie"` literal | `"Movie"` literal (identical) |

---

## Renamed Symbols

- `sub_A594D0` → `cTrans::setupScene`
- `dword_E55784` → `nDraw__Resource__mRenderFrame`
- Function prototype fixed: `void __thiscall uMovie::draw(uMovie *self, cTrans *pdraw)`
