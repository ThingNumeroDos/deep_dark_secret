# cTrans & sRender — Rendering System Findings

## Overview

`sRender` is the MT Framework singleton that owns the D3D9 device, the dedicated rendering
thread, and 8 `cTrans` command-buffer instances. `cTrans` is a 11 024-byte object that
accumulates per-frame render commands into a stack-allocated command buffer and dispatches
them to the GPU via the rendering thread.

---

## sRender (singleton)

| Symbol | Address |
|--------|---------|
| `sRender::mpInstance` (global ptr) | `0xE552D8` |
| `sRender::sRender` (ctor, full init) | `0x8EF930` |
| Rendering thread entry | `sub_8F60C0` @ `0x8F60C0` |
| D3D9 state reset (called per frame) | `sub_8F3EA0` @ `0x8F3EA0` |
| Actual render dispatch | `loc_8F4120` @ `0x8F4120` |

### sRender Struct Layout (117 264 bytes, parent `cSystem`)

| Offset | Size | Content |
|--------|------|---------|
| +0 | 4 | vtable (`off_C01AA8`) |
| +4 | 24 | `CRITICAL_SECTION` |
| +28 | 1 | `bool` initialized flag |
| +32 | 1 | `bool` rendering thread enabled |
| +40 | 4 | `float 0.5f` (sub-pixel bias?) |
| +48 | 4 | `DWORD = 1` |
| +52 | 4 | `IDirect3DDevice9*` D3D9 device |
| +80 | 4 | screen width (default 1280) |
| +84 | 4 | screen height (default 720) |
| +88 | 4 | `HANDLE` rendering thread (→ `sub_8F60C0`) |
| +92 | 4 | `DWORD` rendering thread ID |
| +96 | 4 | `HANDLE` wake event (game → renderer) |
| +100 | 4 | `HANDLE` done event (renderer → game) |
| +144 | 88 192 | `cTrans[8]` (8 × 11 024 bytes) |
| +88 400 | 1 680 | `sRender_TempTexture[12]` (12 × 140 bytes) |
| +90 080 | 4 096 | 256-entry array (4 DWORDs each — render pass queue?) |
| +94 248 | 8 | `LARGE_INTEGER` frame start timestamp |
| +94 256 | 8 | `LARGE_INTEGER` frame elapsed time |
| +110 732 | 24 | `CRITICAL_SECTION` |
| +116 660 | ~520 | Resolution enum data |
| +117 180 | ~84 | RefreshRate enum data |

The 8 `cTrans` slot indices (cTrans+10948) are written 0–7 at construction:
```
cTrans[0] @ sRender+144   → slot 0
cTrans[7] @ sRender+88336 → slot 7
```
Likely double-buffered across 4 render passes (shadow / pre-pass / main / post).

### Rendering Thread (`sub_8F60C0`)

```
loop:
  WaitForSingleObject(sRender+96, INFINITE)     ← game signals "render now"
  ResetEvent(sRender+96)
  if sRender+134 == true  → break (exit)
  sub_8F3EA0()                                   ← D3D9 state reset (17 SetRenderState)
  loc_8F4120(sRender)                            ← actual render dispatch
  QueryPerformanceCounter → sRender+94256        ← elapsed time record
  SetEvent(sRender+100)                          ← signal completion to game thread
```

`sub_8F3EA0` resets D3D9 to a known baseline (alpha-blend off, CW culling, Z-test on,
stencil off, FILL_SOLID, etc.) before each frame and records the frame-start timestamp at
`sRender+94248`.

---

## cTrans

### Registration

```
sub_8B69B0("cTrans", &MtDTI_MtObject, &MtDTI_cTrans, 11024, 0)  @ 0xB7CFD0
```

Instance vtable: `0xC08208` (13 entries).  
Constructor: `cTrans::cTrans` @ `0xA580A0`.

### Instance Vtable (13 entries @ 0xC08208)

| Slot | Offset | Function | Role |
|------|--------|----------|------|
| 0 | +0x00 | `loc_A58200` | destructor |
| 1 | +0x04 | `sub_8FC2F0` | (unknown) |
| 2 | +0x08 | `sub_521BF0` | (unknown) |
| 3 | +0x0C | `sub_A582C0` | (unknown method) |
| 4 | +0x10 | `sub_A553B0` | `getDTI()` ← standard MtObject slot |
| 5 | +0x14 | `sub_A554A0` | `init()` ← standard slot |
| 6 | +0x18 | `sub_8FC2F0` | `tick()` ← standard slot (same as [1]) |
| 7 | +0x1C | `sub_521BF0` | same as [2] |
| 8 | +0x20 | `sub_A554D0` | (unknown method) |
| 9 | +0x24 | `sub_A552F0` | returns `&MtDTI_cTrans_Element` |
| 10 | +0x28 | `nullsub_2` | (stub) |
| 11 | +0x2C | `nullsub_2` | (stub) |
| 12 | +0x30 | `0x410360` | (currently mis-labeled) |

Sub-class vtables are stored immediately after cTrans's vtable in memory:

| Vtable label | Address |
|-------------|---------|
| `MtDTI_vt_cTrans_Element` | `0xC08238` |
| `MtDTI_vt_cTrans_VertexDecl` | `0xC0825C` |
| `MtDTI_vt_cTrans_VertexBuffer` | `0xC08280` |
| `MtDTI_vt_cTrans_IndexBuffer` | `0xC082A4` |
| `MtDTI_vt_cTrans_TextureBase` | `0xC082CC` |
| `MtDTI_vt_cTrans_Texture` | `0xC082F4` |
| `MtDTI_vt_cTrans_ArrayTexture` | `0xC0831C` |
| `MtDTI_vt_cTrans_CubeTexture` | `0xC08344` |
| `MtDTI_vt_cTrans_VolumeTexture` | `0xC0836C` |
| `MtDTI_vt_cTrans_Technique` | `0xC08390` |

### cTrans Internal Layout (11 024 bytes)

```
cTrans+0       : vtable ptr (→ 0xC08208)
cTrans+16      : render pass block [0]  (2720 bytes)
cTrans+2736    : render pass block [1]  (2720 bytes)
cTrans+5456    : render pass block [2]  (2720 bytes)
cTrans+8176    : render pass block [3]  (2720 bytes)
cTrans+10896   : "hot path" management fields (128 bytes)
```

The range `cTrans+16 … cTrans+10895` is zeroed by `memset` in the ctor after the
sub-object array initialization.

#### Per Render-Pass Block (2720 bytes = 0xAA0)

Each block starts at `cTrans+16 + N × 2720`. Internal layout (confirmed from API analysis):

| Block-relative offset | Content |
|-----------------------|---------|
| +0 | 4×4 float matrix (world/view) |
| +64 | 4×4 float matrix |
| +192 | 4×4 float matrix |
| +256 | 4×4 float matrix |
| +304 | viewport rect (4 floats: x1, y1, x2, y2) |
| +512 | sub-scene scissor data |
| +528 | `float` render target width |
| +532 | `float` render target height |
| +552 | stored viewport rect ptr (set by viewport helper) |
| +564 | render state flags DWORD (bits: sub-scene return address, pass ID, etc.) |
| +660 | **resource slot table** — array of ptrs to active shader constants / textures |

Inside each pass block, 7 groups of sub-objects (raw 16-byte records, trivially constructed)
are allocated at sub-block boundaries by `sub_401020` calling the no-op `sub_414E40`.  
Counts: 4, 4, 4, 4, 4, 4, **6** (last group has 6 entries — likely 6 texture slots).

#### Hot-Path Management Fields (cTrans+10896, indexed as `this[N]`)

| DWORD index | Byte offset | Name / Role |
|-------------|-------------|-------------|
| 2724 | +10896 | `cur_state_block` — ptr to active render pass block |
| 2725 | +10900 | `slot_table` — ptr to resource slot table (= cur_state_block + 660) |
| 2728 | +10912 | current shader index |
| 2729 | +10916 | dirty flags (bit `0x20000000` = "slot table modified, needs flush") |
| 2730 | +10920 | command queue base ptr |
| 2731 | +10924 | command queue write index |
| 2732 | +10928 | **command buffer stack pointer** (grows downward, 16-byte aligned) |
| 2736 | +10944 | sub-scene nesting depth counter |
| 2737 | +10948 | cTrans slot index within sRender (0–7, set at sRender ctor time) |

---

## cTrans Sub-class Hierarchy

All sub-classes ultimately inherit `cTrans::Element`. Registration via `sub_8B69B0`.

```
MtObject
├── cTrans  (11024 bytes)
└── cTrans::Element  (16 bytes) — base GPU resource handle
    ├── cTrans::VertexDecl    (28 bytes)
    ├── cTrans::VertexBuffer  (28 bytes)
    ├── cTrans::IndexBuffer   (28 bytes)
    ├── cTrans::Technique     (24 bytes)
    └── cTrans::TextureBase   (80 bytes)
        ├── cTrans::Texture        (96 bytes)
        ├── cTrans::ArrayTexture   (96 bytes)
        ├── cTrans::CubeTexture    (80 bytes)
        └── cTrans::VolumeTexture  (80 bytes)
```

| Class | Registered size | Parent | DTI address | DTI vt address |
|-------|----------------|--------|-------------|----------------|
| `cTrans` | 11024 | `MtObject` | `0xEAE008` | `0xC08398` |
| `cTrans::Element` | 16 | `MtObject` | `0xEAE04C` | `0xC08238` |
| `cTrans::VertexDecl` | 28 | `Element` | `0xEADF88` | `0xC0825C` |
| `cTrans::VertexBuffer` | 28 | `Element` | `0xEAE06C` | `0xC08280` |
| `cTrans::IndexBuffer` | 28 | `Element` | `0xEAE028` | `0xC082A4` |
| `cTrans::Technique` | 24 | `Element` | `0xEAE0C4` | `0xC08390` |
| `cTrans::TextureBase` | 80 | `Element` | `0xEADF68` | `0xC082CC` |
| `cTrans::Texture` | 96 | `TextureBase` | `0xEAE0A4` | `0xC082F4` |
| `cTrans::ArrayTexture` | 96 | `TextureBase` | `0xEADFC8` | `0xC0831C` |
| `cTrans::CubeTexture` | 80 | `TextureBase` | `0xEADFA8` | `0xC08344` |
| `cTrans::VolumeTexture` | 80 | `TextureBase` | `0xEADFE8` | `0xC0836C` |

Key destructors:
- `cTrans_Element__dtor` @ `0xA55420`
- `cTrans_VertexDecl__dtor` @ `0xA555B0`
- `cTrans_VertexBuffer__dtor` @ `0xA55870`
- `cTrans_IndexBuffer__dtor` @ `0xA56F50`
- `cTrans_ArrayTexture__dtor` @ `0xA57930`
- `cTrans_CubeTexture__dtor` @ `0xA579E0`
- `cTrans_VolumeTexture__dtor` @ `0xA57C90`

---

## Key cTrans API

### `cTrans::setTexture` @ `0xA58240`

```c
// __usercall: eax=tex_ptr, edx=cTrans*, esi=slot_index
void cTrans::setTexture(cTrans_Texture* tex, cTrans* ctx, int slot)
```

- Marks `tex` as used this frame: `tex[+204]` is a frame-tracking table;
  writes `1` at `[tex+204 + 2*frame_index + 4]` where `frame_index = dword_E55784`.
- Checks `ctx->slot_table[slot]`; if changed, updates it and sets dirty flag
  `ctx->dirty |= 0x20000000`.

### `cTrans::createSubScene` @ `0xA584D0`

```c
int cTrans::createSubScene(int budget_decrement)
```

- Atomically decrements the global sub-scene budget counter `dword_E5577C`
  (protected by a `CRITICAL_SECTION`).
- Returns the new counter value. Callers use this to allocate a sub-scene slot.

### `cTrans::endSubScene` @ `0xA586C0`

Pops the current sub-scene from the render stack:
1. Emits an opcode-16 (0x10) command to the command queue (5 DWORDs: size=16, type=1,
   timestamp, callback ptr `Default`, zero).
2. Decrements `this[2736]` (sub-scene depth).
3. Restores `cur_state_block` to the parent scene's block
   (`block[2736 - 1]`).
4. Copies 4 matrices (64 bytes each) from the parent block back into the command
   buffer stack (16-byte aligned).
5. Calls `sub_A5CCC0` to recompute viewport shader constants for the restored viewport.
6. Sets final dirty flags `0xE0000000`.

### `cTrans::newMaterial` @ `0xA59190`

```c
undefined4* cTrans::newMaterial(cTrans* this)
```

- Reads the current technique from `sShader::mpInstance` at offset
  `18488 + 4 * this[2728]` (shader slot lookup).
- Resolves pass and pixel shader sub-objects from the technique.
- Pushes a variable-length material command onto the stack: base 2 DWORDs
  (pixel_shader_ptr, vertex_shader_ptr) followed by N texture slot references
  (copied from `slot_table[index]` for each sampler declared in the technique).
- Number of texture refs = `(technique[+12] >> 25)` + optional per-pass count.

### `cTrans::applyRenderTarget` @ `0xA5CF80`

```c
void cTrans::applyRenderTarget(
    cTrans_Texture* target, cTrans_Texture* depth,
    uint flags, uint miplevel, uint cubeface,
    int targetformat, int depthformat)
```

- Derives width/height from the target texture at `texture[+28]` (width) and
  `texture[+30]` (height), shifted right by `miplevel`.
- Checks/updates the viewport-size shader constant in the slot table (`view_no`).
- Pushes a 40-byte opcode-5 command to the command queue:
  - DWORD[0] = 5 (opcode)
  - DWORD[1] = target ptr (or 0 if depth-only)
  - DWORD[2] = miplevel
  - DWORD[3] = cubeface
  - DWORD[4] = clear flags (bits 0/1/8 → 2/4/8)
  - DWORD[5] = target pixel format (or fallback from texture[+36])
  - DWORD[6] = width, DWORD[7] = height
  - DWORD[8] = depth format (75 = D24S8 default if negative)
  - DWORD[9] = `(flags >> 2) & 1` (depth-only flag)

---

## Viewport/Scissor Helper (`sub_A5CCC0`)

Called at end of `endSubScene`. Given a viewport rect (`x1, y1, x2, y2` ints):

1. Pushes the rect as a 24-byte record to the command buffer stack.
2. Reads render target dimensions from `cur_state_block+528` (width) and `+532` (height).
3. Computes three 4-float shader constant vectors and updates the slot table:
   - **`dword_E55440` slot**: viewport position offset (`(x/w)/scale + 0.5/w`, ...)
   - **`dword_E555D0` slot**: inverse viewport size Y (negated)
   - **`dword_E555CC` slot**: inverse viewport dimensions (`1/w, 1/h, 0, 0`)
4. Stores viewport rect ptr into `cur_state_block+552`.

---

## Globals Referenced by cTrans

| Global | Address | Role |
|--------|---------|------|
| `dword_E55784` | `0xE55784` | Current frame index (for texture usage tracking) |
| `dword_E5577C` | `0xE5577C` | Sub-scene budget counter (decremented by createSubScene) |
| `dword_E553D0` | `0xE553D0` | Shader slot index (view matrix?) |
| `dword_E55578` | `0xE55578` | Shader slot index |
| `dword_E553F0` | `0xE553F0` | Shader slot index |
| `dword_E55620` | `0xE55620` | Shader slot index |
| `dword_E552EC` | `0xE552EC` | Shader slot (viewport transform?) |
| `dword_E55440` | `0xE55440` | Shader slot: viewport offset constant |
| `dword_E555D0` | `0xE555D0` | Shader slot: viewport scale Y |
| `dword_E555CC` | `0xE555CC` | Shader slot: inverse viewport dimensions |
| `view_no` | `0xE553D8` (approx) | Viewport shader slot index |
| `sShader::mpInstance` | (see sShader singleton) | Shader system singleton |
