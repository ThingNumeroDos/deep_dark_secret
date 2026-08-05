# rTexture

MT Framework **texture resource** for the DX9 build (`DevilMayCry4_DX9.exe`).
A `cResource` subclass that parses `.tex` files and owns the D3D9 texture object.

Companion docs: [texture_binding.md](texture_binding.md) (how a texture reaches a
sampler), [cMaterialStandard.md](cMaterialStandard.md) (who holds texture pointers),
[sResource_findings.md](sResource_findings.md) (the generic load path).

## Identity

| Item | Value |
|------|-------|
| DTI global | `rTexture::DTI` @ `0xEAD680` |
| Name string | `"rTexture"` @ `0xC0359C` |
| Instance vtable | `rTexture::vftable` @ `0xC035A8` |
| Alloc size | **232 bytes** (0xE8) — `push 0E8h` @ `0xB7BB24` |
| DTI init | `rTexture::DTI::init` @ `0xB7BB20` |
| Constructor | `rTexture::rTexture` @ `0x9064B0` |
| Destructor | `rTexture::dtor` @ `0x906510` |
| Parent | `cResource::DTI` (`mov edi, offset cResource__DTI` @ `0xB7BB29`) |
| File extension | `"tex"` @ `0xC03598`, returned by `rTexture::getExt` (`0x906480`) |

```
MtObject  ->  cResource  ->  rTexture
```

Related classes (not analyzed here): `rRenderTargetTexture::DTI` @ `0xEAE268`,
`r2Texture::DTI` @ `0xEAE288`, `sRender::TempTexture::DTI` @ `0xEAD5A0`.

## Field layout (232 bytes)

| Off | Field | Type | Evidence |
|-----|-------|------|----------|
| 0x00 | `base` | `cResource` (96 B) | DTI parent link @ `0xB7BB29`; ctor writes `+0x44`=1 refcount @ `0x9064C8` |
| 0x60 | `mSHFactor` | `rTexture::SHFACTOR` (108 B) | `lea eax,[ebx+60h]; push 6Ch` @ `0x90683D`–`0x90683F` |
| 0xCC | `mpTexture` | `cTrans::Texture*` | ctor zeroes @ `0x9064E2`; dtor releases @ `0x906514`; assigned @ `0x906D8B` |
| 0xD0 | `mOrgInvWidth` | `float` | `movss [ebx+0D0h], xmm2` @ `0x90681A` (= `1.0f / width`) |
| 0xD4 | `mOrgInvHeight` | `float` | `movss [ebx+0D4h], xmm0` @ `0x906822` |
| 0xD8 | `mOrgWidth` | `u32` | `mov [ebx+0D8h], eax` @ `0x9067F7` |
| 0xDC | `mOrgHeight` | `u32` | `mov [ebx+0DCh], edx` @ `0x90682A` |
| 0xE0 | `mOrgDepth` | `u32` | `mov [ebx+0E0h], eax` @ `0x906830` |
| 0xE4 | `mDetailBias` | `u32` | ctor zeroes @ `0x906504` — **dead, see below** |

`SHFACTOR` is 108 bytes: `float r[9]`, `float g[9]`, `float b[9]` — spherical-harmonic
lighting coefficients, read only for cube maps.

> **`mDetailBias` (+0xE4) is write-only / dead.** `xrefs_to_field` returns **zero**
> references. The ctor zeroes it and nothing ever reads it. The loader's actual LOD
> source is `cResource+0x4E` (`0x906899`), inside the base — not this field.
> This mirrors the dead `mpTex_E4` slot on the material side.

## TEX file format

Parsed by `rTexture::load` (`0x906760`) — vtable slot 8 (`+0x20`), invoked by the
`sResource` file-load path `sub_8DF980`. The 40-byte header is read in one call
through the stream's `vtbl+0x30` (`push 28h` @ `0x906776`).

### Header (40 bytes)

| Off | Size | Field | Evidence |
|-----|------|-------|----------|
| 0x00 | 4 | **magic `'TEX\0'` = `0x00584554`** | `cmp [var_28], 'XET'` @ `0x906785`; mismatch → `return 0` @ `0x90678F` |
| 0x04 | 4 | packed descriptor | see bit table below |
| 0x08 | 1 | **mip / level count** | `LOBYTE(param_1)` used as level count @ `0x906856` |
| 0x09 | 1 | **face / array count** | `HIBYTE(param_1)`; alloc `4*mip*faces` @ `0x906881` |
| 0x0A | 2 | *(padding — never read)* | |
| 0x0C | 2 | **width** (u16) | `movzx eax, word [var_1C]` @ `0x9067E6` |
| 0x0E | 2 | **height** (u16) | `movzx edx, word [var_1C+2]` @ `0x9067EB` |
| 0x10 | 2 | **depth** (u16) | `movzx eax, word [var_18]` @ `0x9067FD` |
| 0x14 | 4 | **D3DFORMAT / FourCC** | passed straight to the create call @ `0x9069C2`, `0x906AF2`, `0x906C3A` |
| 0x18 | 16 | `mRange` float4 | `.x` compared to 1.0 @ `0x9067BE`; stored to `cTrans::Texture.mRange` @ `0x906D5E`–`0x906D6D` |

#### Packed descriptor (+0x04) bit map

| Bits | Field | Notes |
|------|-------|-------|
| 0–15 | **version — must be `0x70` (112)** | `cmp eax, 70h; jnz fail` @ `0x9067A4` |
| 16–19 | **texture type** | `1`/`2` = 2D, `3` = Cube, `4` = Volume — `switch` @ `0x906983` |
| 20–23 | flags / encode | value `2` + identity range → cleared (`and ecx, 0FF0FFFFFh` @ `0x9067DC`) |
| — | encode field | `mFlags ^= (mFlags ^ (packed>>3)) & 0xE0000` @ `0x906D82` |

> **Types 1 and 2 are indistinguishable at runtime.** The jump table entry at
> `0x90698A` is annotated by IDA as `jumptable 00906983 cases 1,2` — a single shared
> target. Both enter the identical 2D path. Whatever the distinction meant in the
> authoring tools, the DX9 loader does not act on it.

### Body, in order

1. **`SHFACTOR` block** — 108 bytes → `this+0x60`, **only when type == 3** (cube).
   Gated by `(packed & 0xF0000) == 0x30000` @ `0x906806`; read @ `0x906845`.
2. **Mip-offset table** — `4 * mipCount * faceCount` bytes into a `TempAllocator`
   scratch buffer (alloc @ `0x906881`, freed @ `0x906D9B`). Indexed
   `[4 * (baseMip + face*mipCount)]` @ `0x906B39`, used with the stream's seek
   (`vtbl+0x4C`) to locate each surface.
3. **Raw surface data** — copied row-by-row into `LockRect`ed surfaces.
   `UnlockRect` @ `0x906A6D` (2D), `0x906BDB` (cube), `0x906D2B` (volume).

### Mip-skip / texture-quality LOD

At `0x906899`–`0x9068EE`:

```
skipMips        = clamp(2 - (cResource.flags & 7) + sShader::mpInstance->vtbl[9](mPath), 0, 2)
effectiveLevels = clamp(mipCount - skipMips, 8, mipCount)
shift           = mipCount - effectiveLevels
```

`width`/`height`/`depth` are then right-shifted by `shift` (`0x906902`, `0x90692D`,
`0x906954`), and `mOrgInvWidth` is recomputed from the shifted size @ `0x906AA9`.

The per-path bias comes from `sShader::mpInstance->vtbl[9](mPath)` @ `0x9068AB`.
Its link to the `sMediator +0x4C0` TextureResolution enum is **not traced** — treat
as an open lead, not a fact.

## D3D9 creation wrappers

All create calls go through `sRender::mpInstance->mpDevice` (`IDirect3DDevice9`).
`MtRender::checkD3DResult` is called after each.

| Function | Address | Role |
|----------|---------|------|
| `cTrans::Texture::createTexture` | `0xA575E0` | **Central 2D allocator.** `CreateTexture` (device vtbl `+0x5C`) @ `0xA576F1` |
| `cTrans::Texture::ctor_create_2d` | `0xA57500` | ctor + createTexture; called by load case 1/2 @ `0x9069C2` with `mAttr = 0x41` |
| `cTrans::Texture::ctor_cube` | `0xA57A10` | cube ctor; called by load case 3 @ `0x906AF2` |
| `cTrans::Texture::createCubeTexture` | `0xA57A50` | `CreateCubeTexture` (vtbl `+0x64`) @ `0xA57AE4`; sets `mArrayCount = 6` @ `0xA57A6E` |
| `cTrans::Texture::ctor_volume` | `0xA57CC0` | volume ctor; called by load case 4 @ `0x906C3A` |
| `cTrans::Texture::createVolumeTexture` | `0xA57D00` | `CreateVolumeTexture` (vtbl `+0x60`) @ `0xA57D9E` |
| `cTrans::Texture::lock_rect` | `0xA578F0` | `LockRect` @ `0xA57918` |
| `cTrans::Texture::lock_box` | `0xA57E80` | `LockBox`; called @ `0x906CA2` |
| `rTexture::decode_block_pitch` | `0x9066A0` | row pitch / row count per mip |

### `mAttr` → D3D9 usage/pool (`createTexture` @ `0xA575E0`)

| `mAttr` bit | Result | Evidence |
|-------------|--------|----------|
| `0x02` | `D3DUSAGE_RENDERTARGET` (512) | `0xA5761F` |
| `0x04` | `D3DUSAGE_DEPTHSTENCIL` (1) | `0xA57628` |
| `0x08` | `D3DPOOL_SYSTEMMEM` | `0xA57631` |
| `0x40` | `D3DPOOL_MANAGED` | `0xA5763A` |
| `0x84` + SLI | shared | `0xA57609` |

Ordinary `.tex` files load with `mAttr = 0x41` (MANAGED + bit 0). A second SLI copy
is created into `mpSharedTexture` when `mFlags & 0x10000` @ `0xA57735`. Non-DXT
formats are rounded up to power-of-two @ `0xA57673`; DXT1/3/5 are exempt.

The engine's own assert strings name the parameters exactly (`0xC07EE0`–`0xC08170`):
`IRender->getDevice()->CreateTexture(mSurfaceSize.w, mSurfaceSize.h, level, usage,
(XFFORMAT)fmt, pool, &ptex, NULL)`.

### Block / pitch rules (`0x9066A0`)

| FourCC | Decimal | Bytes per block | Evidence |
|--------|---------|-----------------|----------|
| `DXT1` | 827611204 | 8 | `0x906734` |
| `DXT3` | 861165636 | 16 | `0x906716` |
| `DXT5` | 894720068 | 16 | `0x906716` |
| other | — | bits-per-pixel math via `sub_9065C0` | `0x9066E5` |

## `cTrans::Texture` / `cTrans::TextureBase`

The D3D9-side object that `rTexture::mpTexture` points at. Both types were already
declared in the IDB; this analysis confirms them against the code.
`cTrans::TextureBase` is 80 B; `cTrans::Texture` is 96 B (adds `mWRatio`/`mHRatio`).

| Off | Field | Type | Evidence |
|-----|-------|------|----------|
| 0x00 | `base` | `cTrans::Element` (16 B) | |
| 0x04 | `mProtect[]` | u16 per frame | `[eax + 2*mRenderFrame + 4] = 1` @ `0xA63215` — per-frame "in use" marker guarding streaming eviction |
| 0x10 | `mpTexture` | `IDirect3DTexture9*` | `CreateTexture(..., &fmt)` then store @ `0xA57708` |
| 0x14 | `mpSharedTexture` | `IDirect3DTexture9*` | SLI second copy @ `0xA57735` |
| 0x18 | `mParam` | `int` | usage/pool bits (`mAttr`) @ `0xA575FB` |
| 0x1C / 0x1E | `mWidth` / `mHeight` | u16 | `0xA5776A` / `0xA57762` |
| 0x20 | `mDepth` | u32:16 | volume path @ `0xA57E14` |
| 0x22 | `mScratch` / `mEncode` / `mLevelCount` | u32:1 / :3 / :4 | `mLevelCount` @ `0xA57787` |
| 0x23 | `mArrayCount` | u32:8 | cube sets 6 @ `0xA57A6E` |
| 0x24 | `mFormat` | u32 | from `GetLevelDesc` @ `0xA5778E` |
| 0x30 | `mRange` | `MtVector4` | from TEX header floats @ `0x906D5E` |
| 0x40 | `mSurfaceSize[4]` | u32×4 | `[2]`=width @ `0xA57647`, `[3]`=height @ `0xA5764A` |

## Vtable (`0xC035A8`)

| Slot | Off | Target | Role |
|------|-----|--------|------|
| 0 | +0x00 | `0x906510` | `rTexture::dtor` — releases `mpTexture` via `sub_8FB430` @ `0x90652B`, reverts vtable to `cTrans::vftable_0` |
| 4 | +0x10 | `0x906470` | `rTexture::getDTI` |
| 6 | +0x18 | `0x906480` | `rTexture::getExt` → `"tex"` |
| 8 | +0x20 | `0x906760` | **`rTexture::load`** |

## Annotations applied to the IDB

- Renamed: `rTexture::load`, `rTexture::rTexture`, `rTexture::dtor`,
  `rTexture::decode_block_pitch`, `cTrans::Texture::createTexture` /
  `createCubeTexture` / `createVolumeTexture` / `ctor_create_2d` / `ctor_cube` /
  `ctor_volume` / `lock_rect` / `lock_box`.
- Function comments on `0x906760` (full header spec), `0x906899` (LOD), `0xA575E0`
  (`mAttr` decode), `0x9066A0` (block sizes).
- `TEX_TYPE` enum (1/2 = 2D, 3 = Cube, 4 = Volume).

## Open / unresolved

- `sShader::mpInstance->vtbl[9](mPath)` (`0x9068AB`) — the per-path LOD bias source.
  Not traced to the settings enum.
- Header bytes `0x0A`–`0x0B` are never read; assumed padding.
- `mOrgDepth` is written for every texture type, not just volumes (`0x906830`).
  Whether it is meaningful for 2D/cube is undetermined.
- The `MtFileStream` class itself was not analyzed; `rTexture::load` uses its
  `vtbl+0x24` (tell), `+0x30` (read), `+0x4C` (seek).
