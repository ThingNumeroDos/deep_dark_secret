# cTrans Viewport System — Deep Dive

## Overview

The viewport system is built on a **4-level sub-scene stack** embedded inside each `cTrans`
instance. Every render pass — shadow map, reflection, water layer, main scene, post-process —
gets its own stack frame with isolated matrices, shader constants, and a command-buffer scope.
The CPU records commands into a downward-growing stack-allocated buffer; the render thread
consumes them asynchronously.

---

## Sub-scene Stack

### Stack Slots

Each of the 4 render pass blocks (2720 bytes, at `cTrans+16 + N×2720`) is one stack frame.
The active frame is tracked by:

```
this[2736]  (+10944)  depth counter  (0 = top-level, max 3)
this[2724]  (+10896)  cur_state_block — ptr to cTrans+16+depth×2720
this[2725]  (+10900)  slot_table = cur_state_block + 660 bytes
```

### Sub-scene Lifecycle

| Function | Address | Action |
|----------|---------|--------|
| `cTrans::createSubScene` | `0xA584D0` | Pre-allocate N sub-scene budget slots from `dword_E5577C` (global counter, lock-protected) |
| `cTrans::beginSubScene` | `0xA58500` | Push: depth++, advance state block, zero it, inherit pass-type flags, emit opcode-16 "begin" |
| `cTrans::endSubScene` | `0xA586C0` | Pop: emit opcode-16 "end", depth--, restore parent state block, re-push 4 matrices to cmd buf |

`createSubScene` is called **once** per object to reserve a count of sub-scenes (e.g., 3 for
water's refraction/reflection/composite). Then `beginSubScene + endSubScene` pairs are used
per actual render pass.

### `cTrans::beginSubScene` (`0xA58500`) — detail

```cpp
// Signature: __usercall beginSubScene(a1=scene_type@<eax>, a2=cTrans*@<esi>, param_1, param_2, param_3)
// param_1 = byte flag: sub-pass type (1 = reflection, etc.)
// param_2 = label string ptr (debug GPU scope name)
// param_3 = debug id

++a2[2736];                                       // depth++
cur_block = &a2[680 * depth + 4];                 // = cTrans + 16 + 2720 * depth
a2[2724] = cur_block;                             // update cur_state_block
a2[2725] = cur_block + 660;                       // slot_table = block + 660 bytes
memset(cur_block, 0, 0xAA0);                      // zero entire 2720-byte block

// Inherit parent pass-type flags (bits 0-28) from parent's state flags (+564)
cur_block[+564] = parent[+564] & 0x1FFFFFFF;
// Override bits [24:28] with scene_type (the a1 param, shifted)
cur_block[+564] ^= (cur_block[+564] ^ (a1 << 24)) & 0x1F000000;

// Set byte at +508 = sub-pass type param
cur_block[+508] = param_1;
// Pack default render state magic values
cur_block[+500] = 19005730;     // 0x01224F62 — packed blend/depth/cull flags
cur_block[+504] = 667959971;    // 0x27D2CA63 — packed pipeline flags
// Clear control bits in +508
cur_block[+508] &= ~0x100;      // clear bit 8
cur_block[+508] &= ~0x200;      // clear bit 9
cur_block[+508] = (cur_block[+508] & 0xFFFFC3FF) | 0x400;  // set bit 10

// Push opcode-16 "begin" to command queue (20 bytes):
// [0]=16, [1]=0 (begin marker), [2]=scene_type, [3]=debug_label_ptr, [4]=debug_id

// Init slot_table from sShader default constant registry:
//   sShader has v9[6158] registered entries; each 5 DWORDs wide
//   copies sShader[530 + i*5] → slot_table[i] for i=0..count-1

// Call sShader::vtable[8](sShader, cTrans) — bind default shader state
```

### `cTrans::endSubScene` (`0xA586C0`) — detail

```cpp
// Mark the sub-scene exit point in state flags (+564):
//   set bits with loc_B00000 address (used as cmd-buf jump label)
//   clear bits [0:19], set pass ID [20:23] = 0xC

// Push opcode-16 "end" (20 bytes):
// [0]=16, [1]=1 (end marker), [2]=0, [3]=&Default (callback), [4]=debug_id

--depth;   // pop
cur_block = cTrans + 16 + 2720 * depth;   // restore parent block
a2[2724] = cur_block;
a2[2732] -= 64;                            // grow cmd buffer (aligned)
a2[2725] = cur_block + 165;               // slot_table = parent + 660 bytes (165 dwords)

// Re-push 4 matrices from parent state block (opaque restore):
// Reads parent[+0], [+64], [+192], [+256] (four 4×4 float matrices)
// For each: aligns cmd buf ptr, copies 16 floats, updates slot_table entry, sets dirty 0x20000000

// Call set_viewport_constants with parent[+304..319] (viewport rect)
// Set dirty flags 0xE0000000
```

---

## Render Pass State Block Layout (2720 bytes per depth level)

`cur_state_block = cTrans + 16 + depth × 2720`

| Offset | Size | Content |
|--------|------|---------|
| +0 | 64 | `MtMatrix` — projection matrix (float[16]) |
| +64 | 64 | `MtMatrix` — view matrix (float[16]) |
| +128 | 64 | `MtMatrix` — derived matrix (view-proj inverse?) |
| +192 | 64 | `MtMatrix` — derived matrix |
| +256 | 64 | `MtMatrix` — derived matrix |
| +304 | 16 | `int[4]` viewport rect (x1, y1, x2, y2) — source scissor |
| +512 | 16 | `int[4]` current viewport scissor rect (x1, y1, x2, y2) |
| +528 | 4 | `int` render target width (pixels) — written by GPU side after opcode-5 |
| +532 | 4 | `int` render target height (pixels) |
| +500 | 4 | packed render state flags (low) — default 19005730 |
| +504 | 4 | packed render state flags (high) — default 667959971 / 130564768 |
| +508 | 4 | per-scene byte flags: bit10=enabled, bits8/9=clear mode, byte0=pass type |
| +552 | 4 | ptr → viewport rect data in cmd buffer (set by `set_viewport_constants`) |
| +564 | 4 | pass control flags: bits[24:28]=pass type, bit30=cmd-buf jump label, bits[20:23]=pass ID |
| +568 | 4 | current pixel shader ptr (from sShader) |
| +576 | 4 | double-sided render flag (bit 0) |
| +580 | 8 | per-pass QWORD data A |
| +588 | 8 | per-pass QWORD data B |
| +660 | 2060 | **resource slot table** — array of ptrs to shader constants in cmd buffer |

The slot table region (+660..+2719) holds one pointer per shader constant slot (about 515
entries). Each entry points to a 4-float (16-byte) vector somewhere in the command buffer stack.
When a constant changes, the pointer is updated and `dirty |= 0x20000000` is set.

### Matrix Writes (`sub_A594D0` @ `0xA594D0`)

This 70 KB function sets up the view/projection transform for a sub-scene:

```cpp
// Inputs: ECX = view matrix (float[16]), EDX = proj matrix (float[16])
//         param_2 = cTrans*, a4 = viewport_rect[4]
cur_block[+0]  ← proj matrix  (16 floats, 64 bytes)
cur_block[+64] ← view matrix  (16 floats, 64 bytes)
// Then: compute view_proj, inverse_view_proj, normal matrix etc.
// Each derived matrix is pushed to cmd buf stack and slot_table is updated
```

---

## Viewport Constant System

The slot table stores pointers to 4-float shader constant vectors. Several indices are used
specifically for viewport/transform data:

| Global slot index | Role | Data (float4) |
|-------------------|------|---------------|
| `view_no` (≈`0xE553D8`) | RT dimensions | (width, height, 1/width, 1/height) |
| `dword_E55440` | Viewport offset A | UV offset X (pixel-center corrected) |
| `dword_E555D0` | Viewport offset B | UV scale Y (negated) |
| `dword_E555CC` | Viewport inverse size | (1/vp_width, 1/vp_height, 0, 0) |
| `dword_E55580` | Scene color texture | RT texture ptr |
| `dword_E5558C` | Secondary RT texture | |
| `dword_E55600` | Full-viewport UV | (0, 0, 1, 1) when no clip |
| `dword_E553B4` | UV clamp rect | (u1, v1, u2, v2) |
| `dword_E553C4` | Pass identifier | pass type value |
| `dword_E553B8` | Shape blend tex array | ptr to textures |
| `dword_E55328` | Default shader slot | |

### `cTrans::set_viewport_constants` (`0xA5CCC0`)

```
Input: a1 (edx) = int[4] viewport rect {x1, y1, x2, y2}
       a2 (ecx) = cTrans*
```

1. Pushes the raw viewport rect (24 bytes) to the cmd buffer stack:
   `[x1, y1, x2, y2, 0, 1.0f]`
2. Reads RT dimensions from `cur_state_block+528` (width) and `+532` (height)
3. Computes three UV-space shader constants for pixel-accurate sampling:

```
slot[dword_E55440] = UV offset A:
    x = (x1/RT_W) / px_scale_x + 0.5/RT_W
    y = (y1/RT_H) / px_scale_y - 1.0
    (encodes viewport-to-UV mapping with pixel-center bias)

slot[dword_E555D0] = UV scale:
    x = px_scale_x                 (positive)
    y = -px_scale_y                (negated for Y-flip)

slot[dword_E555CC] = UV inverse size:
    x = 1/vp_width, y = 1/vp_height, z=0, w=0
```

4. Stores the viewport rect ptr into `cur_state_block+552`

### Full-Pass Viewport Setup (`sub_8F9710` @ `0x8F9710`, `sub_8F8C80` @ `0x8F8C80`)

These are the **top-level** render pass entry points. They:

1. Read screen dimensions from `sRender+80/84`
2. Call `set_viewport_constants({0, 0, screen_W, screen_H}, cTrans)` — full-screen viewport
3. Update `slot_table[view_no]` with `(screen_W, screen_H, 1/screen_W, 1/screen_H)` if changed
4. Set `cur_state_block+568` = current default shader (from sShader)
5. Read the stored scissor rect from `cur_state_block+512` for a second `set_viewport_constants` call (scissor sub-rect if different from full-screen)

`sub_8F8C80` also:
- Emits up to 4 opcode-7 (Clear) commands for different depth/stencil regions
- Emits opcode-1 (SetViewport) with the scissor rect
- Determines pass mode: 0 = full viewport, 2 or 4 = scissored (when viewport rect ≠ screen size)
- Sets 3 texture slots for UV-clamp, UV-adjust, and blend-factor shader constants

---

## Command Opcodes (decoded)

Commands are pushed to `this[2732]` (cmd buf ptr, grows downward, 16-byte aligned) and
enqueued via `this[2730/2731]` (queue base + write index).

Each queue entry is 8 bytes: `(cmd_ptr, state_flags_at_time_of_push)`.  
`state_flags` = `cur_state_block+564` at push time — the render thread uses this to route
commands to the correct pass.

| Opcode | Size | Layout | Meaning |
|--------|------|--------|---------|
| 1 | 20 B | `[1, x1, y1, x2, y2]` | **SetViewport** / scissor rect |
| 4 | 32 B | `[4, material*, geometry*, viewport_rect*, flags_lo, flags_hi, shader_data*, draw_offset]` | **DrawCall** |
| 5 | 40 B | `[5, target_tex*, miplevel, cubeface, clear_flags, format, w, h, depth_fmt, depth_only_flag]` | **SetRenderTarget** |
| 7 | 40 B | `[7, clear_type, enable, depth_stencil_spec, 1.0f, 0, {rect_start_qword, rect_end_qword}]` | **Clear** |
| 16 | 20 B | `[16, begin/end_flag, scene_type, callback_ptr, debug_id]` | **BeginScene / EndScene** |

The `flags_hi` field of opcode-4 (DrawCall) packs:
- `state_block+504` base flags
- bit 28: XOR'd from `state_block+508` bit 8 — "depth-write-disabled" hint

---

## Shader State Caching (`dirty` flags at `this[2729]`)

```
bit 29 (0x20000000) — slot_table has changed; newMaterial must rebuild next draw call
bit 30 (0x40000000) — pixel shader changed
bit 31 (0x80000000) — vertex declaration / vertex shader changed
bits [0:7]          — current pass index (low byte of dirty)
bits [8:28]         — shader selection (which sShader technique slot)
```

Pattern before every draw call:
```cpp
if (dirty & 0x20000000) {
    dirty &= ~0x20000000;
    this[2727] = cTrans::newMaterial(this);  // rebuild material command
}
if (dirty & 0x80000000) {
    // push 92-byte vertex declaration command (opcode in v3[2732]-92)
    // fills: shader ptr, VB ptr, IB ptr, byte_offset, stride, draw_count
    dirty &= ~0x80000000;
    this[2744] = geom_cmd_ptr;
}
```

---

## Geometry Buffer (`this[2744..2752]`)

Packed geometry for procedural / immediate-mode draws (screen-space quads, particle quads, etc.):

| Index | Offset | Role |
|-------|--------|------|
| 2744 | +10976 | current geometry command ptr |
| 2745 | +10980 | vertex buffer ptr (`cTrans_VertexBuffer`) |
| 2746 | +10984 | index buffer ptr (`cTrans_IndexBuffer`) |
| 2750 | +11000 | geometry ring buffer base ptr |
| 2751 | +11004 | geometry ring buffer write ptr |
| 2752 | +11008 | geometry ring buffer end ptr |

Draw calls write geometry into the ring buffer, then update `this[2744]+40` (vertex count).
The draw command (opcode 4) stores `geometry[+40]` as the vertex count/draw-offset.

---

## sRender Timing and Double-Buffering

The 8 cTrans instances (slot 0–7) are used as double-buffered render passes:
- Render thread processes slots 0–3 (or 4–7) while CPU builds the other set
- The per-frame counter `dword_E55784` increments every frame; texture usage stamps use it
- `sRender+94248` = frame start timestamp; `sRender+94256` = frame elapsed (both LARGE_INTEGER)
- `sRender+96` = CPU→GPU event; `sRender+100` = GPU→CPU done event

The state_block+528/532 (RT width/height) is written by the **render thread** after processing
an opcode-5 (SetRenderTarget) command — the CPU reads it on the NEXT frame, which is valid
since RT size is stable across frames unless a resolution change occurs.

---

## Viewport Sub-scene Usage Patterns

### Full-screen pass (most common)
```
beginSubScene(type=1, cTrans, "SceneName", id)
  sub_A594D0(view_mat, proj_mat, cTrans, {0,0,W,H})   // set transforms
  applyRenderTarget(main_color_tex, depth_tex, flags, 0, 0, fmt, -1)
  sub_8F9710(...)  // or sub_8F8C80(...) — set viewport constants
  [draw calls: newMaterial, geometry submit, draw...]
endSubScene()
```

### Reflection / water sub-pass (3-layer example from uInteractiveWater)
```
createSubScene(3)     // pre-allocate 3 budget slots
for layer in 0,1,2:
    beginSubScene(layer_type, cTrans, "Layer", id)
    sub_A594D0(identity, identity, cTrans, rect)
    applyRenderTarget_tex(layer_tex, depth_tex, 0, ...)
    // push clear (opcode 7)
    // [draw layer geometry]
    endSubScene()
```

### Shape-blend / post-process (sub_A689A0)
```
// inline createSubScene (decrement dword_E5577C directly)
for each shape:
    applyRenderTarget(shape_target, 0, 0, 0, 0, D3DFMT_R32F, -1)
    // push opcode-7 clear
    set_viewport_constants(rect, cTrans)
    // set shader slots (dword_E554CC..E55704 — 16 texture stages)
    newMaterial → draw quad
    endSubScene()
```

---

## Key Addresses Summary

| Symbol | Address |
|--------|---------|
| `cTrans::beginSubScene` | `0xA58500` |
| `cTrans::endSubScene` | `0xA586C0` |
| `cTrans::createSubScene` | `0xA584D0` |
| `cTrans::set_viewport_constants` | `0xA5CCC0` |
| `cTrans::applyRenderTarget` | `0xA5CF80` |
| `cTrans::applyRenderTarget_tex` | `0xA5CF40` |
| `cTrans::newMaterial` | `0xA59190` |
| `sub_A594D0` (set transforms) | `0xA594D0` |
| `sub_8F9710` (full-pass viewport setup) | `0x8F9710` |
| `sub_8F8C80` (viewport + scissor setup) | `0x8F8C80` |
| `dword_E5577C` (sub-scene budget counter) | `0xE5577C` |
| `dword_E55784` (frame index) | `0xE55784` |
| `view_no` (viewport size slot index) | `~0xE553D8` |
