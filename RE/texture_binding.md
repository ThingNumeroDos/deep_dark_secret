# Texture binding & sampler state (DX9)

How a loaded [`rTexture`](rTexture.md) becomes a bound D3D9 sampler.

The short version: **nothing in the material layer talks to D3D9.** Binding is
deferred through the `cTrans` command buffer and only becomes real device calls
during CMD replay on the render thread. See
[cTrans_and_sPrim.md](cTrans_and_sPrim.md) for the command-buffer machinery.

```
cMaterialStandard::beginDraw (0xA62C30)
  └─ cTrans::setTexture (0xA58240, inlined ~12x)
       └─ cTrans.mpTextureTable[paramIndex] = rTexture->mpTexture   (cTrans+0x2A94)
          cTrans.mStateDirty |= 0x20000000                          (cTrans+0x2AA4)
             └─ cTrans::newMaterial (0xA59190) packs a MATERIAL command
                  └─ sRender::dispatchCommands (0x8F4120) replays it:
                       ├─ opcode 3/4/11 → sub_8F4494        → SetTexture     (device +0x104)
                       ├─ opcode 8      → sRender.vtbl[+0x88] → SetTexture x13 + DrawIndexedPrimitive
                       └─ sRender::applySamplerState (0x8F4000) → SetSamplerState (device +0x114)
```

## `cTrans::setTexture` (`0xA58240`)

```c
if (res) {
    tex = res->mpTexture;                        // rTexture + 0xCC
    if (tex) tex->base.mProtect[mRenderFrame] = 1;
}
if (mpTextureTable[idx] != tex) {
    mpTextureTable[idx] = tex;
    mStateDirty |= 0x20000000;
}
```

- **`rTexture + 0xCC`** is where the D3D9 handle lives. Proof at the NormalMap slot:
  `mov eax,[edi+0D0h]` (`0xA631FB`) → `mov eax,[eax+0CCh]` (`0xA6320B`).
  The same `+0xCC` load appears at every slot: `0xA6328C`, `0xA632D6`, `0xA63320`,
  `0xA6336A`, `0xA633A9`, `0xA63595`, `0xA6361D`, `0xA6365C`, `0xA63693`, and in the
  base class at `0xA61CB6`.
- The `mProtect[2*mRenderFrame]` write (`0xA63215`) is a **double-buffered per-frame
  "in use" marker** that guards streaming eviction. It is not a binding.

> Previously these slots were typed `cResource*` in the IDB. `cResource` is only 96 B,
> so `+0xCC` decompiled as out-of-bounds arithmetic (`v13[51]`). They are really
> `rTexture*`; retyping them fixes ~12 call sites.

## Per-slot sampler map

The `dword_E555xx` globals are **indices into `sShader::mParameterDesc[512]`**
(`sShader+0x838`, stride 20 B), allocated by name at startup — not raw D3D9 stage
numbers. All are `0xFFFFFFFF` until resolved at runtime. Names below are read from
the binary's own strings, not inferred.

| Material off | Param index global | Shader parameter | Semantic | Null fallback |
|---|---|---|---|---|
| `cMaterial+0x1C` `mpBaseTex` | `mhXfSamplerAlbedoMap` (`0xE5540C`) | `XfSamplerAlbedoMap` | albedo / base | NullWhite |
| `+0xD0` | `mhXfSamplerNormalMap` (`0xE55714`) | `XfSamplerNormalMap` | normal | **NullBlack** ⚠ |
| `+0xD4` | `mhXfSamplerMaskMap` (`0xE554D4`) | `XfSamplerMaskMap` | mask | NullWhite |
| `+0xD8` | `mhXfSamplerShadowMap` (`0xE55568`) | `XfSamplerShadowMap` | shadow | NullWhite |
| `+0xDC` | `mhXfSamplerLightMap` (`0xE5568C`) | `XfSamplerLightMap` | lightmap | NullWhite |
| `+0xE0` | `mhXfSamplerGlossMap` (`0xE5546C`) | `XfSamplerGlossMap` | gloss / specular | NullWhite |
| `+0xE4` | — | — | **dead slot** | — |
| `+0xE8` | `mhXfSamplerEnvironmentMap` (`0xE55340`) | `XfSamplerEnvironmentMap` | environment cube | DefaultCube_CM |
| `+0xEC` | `mhXfSamplerDetailMap` (`0xE55408`) | `XfSamplerDetailMap` | detail | NullBlack |
| `+0xF0` | `mhXfSamplerAmbientOccMap` (`0xE555B0`) | `XfSamplerAmbientOccMap` | ambient occlusion | NullWhite |
| `+0xF4` | `mhXfSamplerAdditionalMap` (`0xE55520`) | `XfSamplerAdditionalMap` | additional | NullWhite |
| `+0xF4` | `mhXfSamplerScreenMap` (`0xE55554`) | `XfSamplerScreenMap` | screen / refraction | NullWhite |

Bind sites: `0xA631FB`, `0xA6326D`, `0xA6358B`, `0xA6339B`, `0xA63307`, `0xA63351`,
`0xA632BD`, `0xA635FE`, `0xA6364E`, `0xA6368D`; base texture at `0xA61B3D`.

### Two corrections to the earlier `cMaterialStandard.md`

1. **`+0xE4` is a dead slot.** An instruction scan of the whole of `beginDraw`
   (`0xA62C30`–`0xA63890`) finds loads of `D0/D4/D8/DC/E0/E8/EC/F0/F4` but **no
   `[edi+0E4h]`**, and `uModel::setMaterials` (`0x9E7410`) writes only `+0xE0`,
   never `+0xE4`. There are **9 live slots** in `0xD0..0xF4`, not 10.
2. **`+0xF4` is bound twice** — `0xA6364E` → AdditionalMap and `0xA6368D` →
   ScreenMap. Two separate loads of `[edi+0F4h]`, not a decompiler artifact.

Net: **11 texture bindings from 9 distinct slots**, plus the base texture = 12.

### System fallback textures — `sShader::mpSysTexture[6]` (`sShader+0x6868`)

Assigned in `sShader::sShader` (`0x8FC9B0`):

| Idx | Off | Resource | Assigned |
|-----|-----|----------|----------|
| 0 | 0x6868 | `system\texture\NullWhite` | `0x8FCBFA` |
| 1 | 0x686C | `system\texture\NullBlack` | `0x8FCC16` |
| 2 | 0x6870 | `system\texture\NullNormal_NM` | `0x8FCC32` |
| 3 | 0x6874 | `system\texture\DefaultCube_CM` | `0x8FCC4E` |
| 4 | 0x6878 | `system\texture\font` | `0x8FCC6A` |
| 5 | 0x687C | `system\texture\XfPCFNoise` | `0x8FCC7F` |

> ⚠ **Suspected engine bug (not confirmed).** The NormalMap fallback reads
> `mpSysTexture[1]` = NullBlack (`0xA63233`, `mov [edx+686Ch]`), *not*
> `mpSysTexture[2]` = NullNormal_NM — even though NullNormal_NM exists for exactly
> this purpose. DetailMap does the same (`0xA632CC`). A flat black texture is not a
> valid tangent-space normal. The code is confirmed; the **intent is not**. Do not
> treat this as a bug without dynamic verification.

Debug toggles corroborating the semantic set: `mDisableBaseMap` (`sShader+0x68C6`)
through `mDisableAmbientOccMap` (`+0x68CC`).

## `sShader::SamplerState` (16 bytes)

`sShader+0x5038`, 256 records, indexed by `ParameterDesc.mStateHandle`
(`ParameterDesc+0x0E`, i.e. `sShader+0x846 + 20*i`). Count in `mSamplerStateNum`
(`sShader+0x6040`). A packed bitfield — **not** D3D9 enum values in memory.

**dword +0x00**

| Bits | Field |
|------|-------|
| 0–3 | `mAddressU` |
| 4–7 | `mAddressV` |
| 8–11 | `mAddressW` |
| 12–15 | `mMaxMipLevel` |
| 16–19 | `mMinMipLevel` — **never emitted to D3D9** |
| 20–23 | `mMaxAnisotropy` — **stored value is N−1** |
| 24–26 | `mMagFilter` |
| 27–29 | `mMinFilter` |

**dword +0x04**

| Bits | Field |
|------|-------|
| 0–2 | `mMipFilter` |
| 10–25 | `mMipLodBias` — fixed point, `float × 2048` then `>>6` |

**+0x08** `mBorderColor`.

Accessors — getters `0x8FB800/820/840/860/8B0/900/920/940/960/980/9F0`;
setters `0x75AD10/AD40/AD70/ADA0/ADD0/AE00`, `0x8FB880/8D0/9B0`, `0x8AE020`.

## The D3D9 translator — `sRender::applySamplerState` (`0x8F4000`)

This is where the bitfield becomes real device state. Called from
`sRender::dispatchCommands` at `0x8F520E` and `0x8F54C4`. It issues **10**
`SetSamplerState` calls (device vtable `+0x114`) for one record:

Listed in **emission order** (the `D3DSAMP_*` number is the 2nd argument, so the last
three are emitted out of numeric order — 10, 9, 8):

| `D3DSAMP_*` | Source expression | Site |
|---|---|---|
| 1 ADDRESSU | `dword[0] & 0xF` | `0x8F4027` |
| 2 ADDRESSV | `dword[0] >> 4 & 0xF` | `0x8F403B` |
| 3 ADDRESSW | `dword[0] >> 8 & 0xF` | `0x8F4052` |
| 4 BORDERCOLOR | `dword[2]` (record +0x08) | `0x8F406A` |
| 5 MAGFILTER | `byte[3] & 7` | `0x8F407D` |
| 6 MINFILTER | `dword[0] >> 0x1B & 7` | `0x8F4091` |
| 7 MIPFILTER | `dword[1] & 7` | `0x8F40A9` |
| 10 MAXANISOTROPY | `(dword[0] >> 0x14 & 0xF) + 1` | `0x8F40BD` |
| 9 MAXMIPLEVEL | `dword[0] >> 0xC & 0xF` (as `HIBYTE(word[0]) >> 4`) | `0x8F40DE` |
| 8 MIPMAPLODBIAS | `(s16)((dword[1] >> 0xA) << 6) × (1/2048)` | `0x8F4104` |

Two things this settles:

- **The filter values pass through untranslated.** There is no lookup table, so the
  engine's 3-bit filter enum **is** `D3DTEXF_*`: `0 = NONE`, `1 = POINT`,
  `2 = LINEAR`, `3 = ANISOTROPIC`.
- **`mMinMipLevel` (bits 16–19) is never emitted**, nor is `D3DSAMP_SRGBTEXTURE`.

The LOD-bias constant `dword_C0EE98` = `0x3A000000` = **1/2048**, the exact inverse
of the `×2048` encoder in the setter — confirming the fixed-point round trip.

If `arg_4 == 0`, the stage index is offset by `+0x101` (`0x90401D`).

> The earlier "where does this reach D3D9" question went unanswered for a while
> because byte-pattern searches for `call dword ptr [reg+114h]` find nothing — the
> call is a two-step `mov ecx,[edx+114h]` / `call ecx`, so the displacement never sits
> in a `call` instruction. Search the `mov`, not the `call`.

## Defaults — `sShader::sampler_defaults_init` (`0x8FDE80`)

Writes the low qword `0x84300048890D0111` (high qword 0 → BorderColor 0). Called from
`sub_8FBBA0` @ `0x8FBC0A` whenever a new parameter is allocated. Decoded:

| Field | Value |
|-------|-------|
| AddressU/V/W | 1 = `D3DTADDRESS_WRAP` |
| MaxMipLevel | 0 |
| MinMipLevel | 13 *(never emitted)* |
| MaxAnisotropy | stored 0 → **1 effective** (anisotropy off) |
| MagFilter / MinFilter | 1 = **`D3DTEXF_POINT`** |
| MipFilter | 0 = `D3DTEXF_NONE` |
| MipLodBias | 0 |

Bits 20, 21, 26, 31 of the `+0x04` dword are set by the `0x84300000` half but map to
no field `applySamplerState` consumes — **purpose undetermined**.

## Quality override — `sShader::sampler_quality_override` (`0x8FDF10`)

Driven by `mTextureDetail` (`sShader+0x68EC`); strings `TEXDETAIL_HIGH/MEDIUM/LOW`
@ `0xC01C00`. Registered in a vtable by `sShader::sShader` @ `0x8FD68D`.

- `MaxAnisotropy` = `{1,2,4,8,16} − 1` (`0x8FDF35`–`0x8FDF51`), merged as
  `(v & 0xF) << 20` @ `0x8FE0A9`
- `MinFilter` → 3 (ANISOTROPIC) or 2 (LINEAR) @ `0x8FDFB9` / `0x8FE01B` / `0x8FE044`
- `MagFilter` → 2 (LINEAR) @ `0x8FDFE2`
- `MipFilter` |= 2 or 1 @ `0x8FDFFC` / `0x8FE081`

It loops over **exactly three** parameters (`0x8FDF5A`–`0x8FDF6C`):
`mhXfSamplerAlbedoMap`, `mhXfSamplerAlbedoMap2`, `mhXfSamplerNormalMap`.
**Shadow, light, env, detail and AO samplers never get anisotropic filtering** —
the texture-quality slider does not affect them at all.

## `uLeafAnim` — a second, independent confirmation

`uLeafAnim::newInstance` (`0x75BAB0`–`0x75CA24`) was **undefined code** in the IDB —
IDA had never created a function there, so it was invisible to `decompile` and to
every xref-based sweep. Defined during this session.

It loads `system\xfshader\XfLeafAnim`, registers technique `tXfLeafAnim` and 21
parameters via `sub_8FE1E0(shader, nameId, typeTag, 1)`, then configures its four
samplers by indexing `mSamplerState[16 * mParameterDesc[handle].mStateHandle]`:

| Sampler | Address | Min | Mag | Mip |
|---------|---------|-----|-----|-----|
| `XfPrimSampler` | CLAMP (3) | 2 LINEAR | 2 LINEAR | 2 |
| `XfVertexSampler` | CLAMP (3) | 1 POINT | 1 POINT | 0 |
| `XfSecondarySampler` | CLAMP (3) | 1 POINT | 1 POINT | 0 |
| `XfConstantSampler` | CLAMP (3) | 1 POINT | 1 POINT | 0 |

POINT filtering on the vertex-texture-fetch samplers is what you would expect for
reading exact texel data rather than filtering it. Every field position agrees with
the decode from `applySamplerState` — two unrelated call sites, same layout.

The 3rd argument to `sub_8FE1E0` is a **parameter type tag**: `0` = sampler,
`1` = flag, `3` = scalar, `4` = vector (read off the names it registers).

## UV scroll / screen refraction

`mStateSelectors[4] == 6` (`0xA636CA`) selects a **screen-space refraction** pass:
forces `mpContext->mBlendState = 0x2A20625` (`0xA636D6`), computes an
aspect-corrected vector from `mDetailWrap × (1/720)` (`flt_C0F374` @ `0xA636FA`)
scaled by viewport w/h (`0xA63734`) into `dword_E5572C` (`0xA6379C`), then binds
`mpContext->mpSceneTexture` (`cContext+0x218`) into `XfSamplerScreenMap`
(`0xA637B5`). The same computation also runs unconditionally when
`mStateSelectors[2] == 2` (`0xA63130`–`0xA631F5`).

The `mUVOffset0/1/2` pairs are plain shader constants (`dword_E55540` @ `0xA62FA2`,
`dword_E55350` @ `0xA6303C`) — shader-side UV math that never touches sampler state
or texture binding.

## Annotations applied to the IDB

- Defined `uLeafAnim::newInstance` (`0x75BAB0`) and `uLeafAnim::dtor_scalar_deleting`
  (`0x75CA30`) from previously undefined bytes.
- Renamed `sRender::applySamplerState` (`0x8F4000`), `cTrans::setTexture`,
  `cMaterial::beginDraw` (`0xA61A70`), `sShader::sampler_defaults_init`,
  `sShader::sampler_quality_override`.
- Renamed all 12 sampler param-index globals `dword_E555xx` / `local_*` →
  `sShader::mhXfSampler*`.
- Declared `sShader::SamplerState` (16 B bitfield record).
- Retyped the 10 `cMaterialStandard` texture slots and `cMaterial::mpBaseTex`
  from `cResource*` to `rTexture*`.
- Comments on `0xA62C30`, `0xA6364E`, `0xA6368D`, `0xA63233`, `0xA636CA`,
  `0xA58240`, `0x8F4000`, `0x8FDE80`, `0x8FDF10`, `0x75BAB0`.
- `D3DTEXTUREFILTERTYPE_MT` enum.

## Open / unresolved

- Bits 20, 21, 26, 31 of `SamplerState +0x04` — set by the default value, consumed
  by nothing found.
- `mMinMipLevel` (bits 16–19) is stored and has accessors but is never sent to D3D9.
- Whether the NormalMap → NullBlack fallback is deliberate.
- `sub_8F4494` (opcode 3/4/11 material apply) and `sRender.vtbl[+0x88]` (opcode 8
  draw submit, SetTexture ×13) were identified as the `SetTexture` consumers from
  [cTrans_and_sPrim.md](cTrans_and_sPrim.md) but not decompiled in detail here.
