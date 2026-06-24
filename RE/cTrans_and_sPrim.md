# cTrans — the render command builder, and its relationship to sPrim

Cross-referenced from the **PS3 debug build** (leaked-PDB = ground-truth names) and validated
against the **DX9** constructor, `beginSubScene`, and `sPrim::submitLine`/`getcPrim`.

> ⚠️ DX9 `cTrans` = **11024 B**, PS3 = **10656 B**. The DX9 `CONTEXT` is 2720 B vs PS3's 2608 B
> (+112), which shifts the whole post-array tail by 4×112 = 448 B. Names are from PS3; **every DX9
> offset is anchored on DX9 code** (ctor `0xA580A0`, `beginSubScene` `0xA58500`, `submitLine` `0x45D1F0`).

## What `cTrans` is

`cTrans` ("transfer context") is the MT Framework **render-command builder**. It is *not* a singleton —
`sRender` embeds **8** of them (`sRender::mTransArray[8]`, one per render thread/slot). Each `cTrans`:

1. Maintains a **stack of view CONTEXTs** (`mContexts[4]`, indexed by `mSubSceneDepth`). Each CONTEXT
   holds the view/proj matrices, frustum, viewport, scene render-targets, a per-scene sort **tag**, and
   a snapshot of the shader parameter/texture table.
2. Builds a **tag list** (`mpCmdList`, array of `cTrans::TAG`, count `mCmdCount`) — each tag is an
   8-byte `{ sortkey, pcmd }` pair. The sort key front-loads scene/pass/priority/depth bits so the whole
   list can be radix-sorted before replay.
3. Carves CMD records and geometry out of a **double-ended buffer**: command/scene records grow *down*
   from `mpCmdStack`; the free-space check is `mpGeoBufferBase + 16*mCmdCount - mpCmdStack`.

### `cTrans` layout (DX9, validated)

| Offset | Field | Type | Evidence |
|--------|-------|------|----------|
| 0x0000 | __vftable | cTrans_vtbl* | ctor |
| 0x0004 | mContexts[4] | CONTEXT[4] (2720 each) | ctor loop stride 2720; `beginSubScene` `680*depth` dwords |
| 0x2A90 | mpContext | CONTEXT* | active stack top; `beginSubScene` |
| 0x2A94 | mpTextureTable | u32* | → active `CONTEXT.mTextureTable` (+0x294); `beginSubScene` |
| 0x2A98 | mpTextureTable2 | u32* | second param/texture table |
| 0x2A9C | mpMaterial | int | bound material |
| 0x2AA0 | mTechniqueSlot | int | active technique slot |
| 0x2AA4 | mStateDirty | u32 | ctor `\|= 0xE0000000`, masked |
| 0x2AA8 | mpCmdList | cTrans::TAG* | tag array; `beginSubScene` `mpCmdList + 8*mCmdCount` |
| 0x2AAC | mCmdCount | u32 | tag count; submitLine `[2731]` |
| 0x2AB0 | mpCmdStack | u32 | downward CMD/geo write ptr; submitLine `[2732]`, `beginSubScene -= 20` |
| 0x2AB4 | mpCmdStackEnd | u32 | |
| 0x2AB8 | mpGeoBufferBase | u32 | buffer base for free-space check; submitLine `[2734]` |
| 0x2AC0 | mSubSceneDepth | int | CONTEXT-stack index (PS3 `mContextPt`); `beginSubScene ++` |
| 0x2AC4 | mSlotIndex | int | which sRender slot/thread owns this cTrans |
| 0x2AD0 | mCameraPos | MtVector3 | eye/camera world pos; used for distance LOD/cull (`sub_ACDE00`, `sub_82BCD0`: `sqrt(Δ²)` vs radius) |
| 0x2AE0 | mpShaderBlock | void* | current shader/command block; `+0x28` is a running counter |
| 0x2AE4 | mpVSCBuffer / mpPSCBuffer | void*×2 | VS/PS constant-buffer objects (`[ptr+16]` copied into draw cmd) |
| 0x2AEC | mpIdxBufferBase/Ptr/End | u16*×3 | 16-bit index-buffer bump allocator (stride 2) |
| 0x2AF8 | mpUPHeapBase/Ptr/End | void*×3 | "UP" dynamic-geometry upload heap (bump alloc, bounds-checked) |

(`_reserved2A84/2A88/2A8C/2AC8/2ACC` confirmed unused — no access anywhere in `.text`. `mGeoBufferUsed@0x2ABC`
reset with the buffer pointers, role tentative.)

### `cTrans::CONTEXT` (per-view, 2720 B DX9 / 2608 B PS3)

| Offset | Field | Notes |
|--------|-------|-------|
| 0x000–0x140 | mViewMat, mProjMat, mProjInvMat, mViewProjMat, mViewInvMat, mViewProjInvMat | 6× MtMatrix |
| 0x180 | mFrustum[6] | MtVector4[6] clip planes |
| 0x1E0 | mTilePlane | MtVector4 |
| 0x1F0 | mPersRate | f32 (perspective-depth scale, used by submitLine sort) |
| 0x1F4 | mBlendState / mDrawState | u32 (`beginSubScene` = 0x1220122 / 0x27D042A3) |
| 0x1FC | mMode | u32 bitfield (cull flip, TPAA, HDR, MSAA, …) |
| 0x200 | mViewport | MtRect |
| 0x210 | mSceneSize | MtSize |
| 0x218 | mpSceneTexture / mpSceneZTexture / mpSceneTextureEx / mpSceneReductionZTexture | scene render-targets |
| 0x228 | **mpViewportConst** | void* → current viewport-rect constant (set by `set_viewport_constants`, `*(mpContext+552)=ptr`) |
| 0x22C–0x230 | _unk22C / _unk230 | 2 dwords, scene-record header |
| 0x234 | **mTag** | u32 scene/sub-scene sort-key prefix; every tag in this scene inherits it (`*(mpContext+564)`) |
| 0x238 | _sceneParamHdr[92] | scene-record/param header (role known, fields not individually named) |
| 0x294 | **mTextureTable[512]** | **per-view shader-constant pointer table** — indexed by shader param slot ID (`dword_E55xxx`), each slot → pointer to that param's current value (matrix/vec data living in the command stack). Mirrors PS3 `mParam[512]`. |

**How the +112 vs PS3 resolves:** the DX9 CONTEXT is 2720 B (PS3 2608). The param region is confirmed
from `endSubScene`/`set_viewport_constants`/`applyRenderTarget`:
- `mpViewportConst@0x228`, `mTag@0x234`, and `mTextureTable@0x294` (`endSubScene` literally sets
  `mpTextureTable = (float*)mpContext + 165` = +0x294).
- `mTextureTable` is **512 pointers** (0x294 → 0xA94), one per `sShader` parameter slot — `endSubScene`
  stores matrix-constant pointers into `mTextureTable[dword_E553D0/E55578/E553F0/E55620/E552EC]`
  (those globals are runtime-resolved shader param IDs, statically `0xFFFFFFFF`); `beginSubScene`
  fills `sShader::mParameterNum` entries. This is the constant-binding table, not a texture array.
- The 0x238–0x290 gap (88 B) is per-view scene-record header state, role-known but not field-named.

### Nested types (defined in DX9, names from PS3)

- `cTrans::TAG` (8 B) — `union { u64 tag; struct { u32 sortkey; void* pcmd; } prim; }`. Built as a
  sort key, resolved to a CMD pointer at replay. (PS3 lays it `{pcmd, bitfield}`; the DX9 sPrim path
  writes `{sortkey@0, pcmd@4}` — modelled as the `prim` view.)
- `cTrans::PARAM_DATA` (4 B union) — `{ f32 fvalue; s32 ivalue; u32 bvalue; const void* padr; }`.
- `cTrans::MESH` (112 B) — `pvdecl, pibuf, iBufOfs, location, VSTREAM vstream[4]`.
- `cTrans::VSTREAM` (24 B) — `pvbuf, vBufOfs, vbase, stride, vnum, location`.
- `cTrans::MATERIAL` (12 B) — `pps (PS), pvs (VS), PARAM_DATA data[]`.
- `cTrans::VIEWPORT` (24 B) — `MtRect r, f32 minz, f32 maxz`.

## The cTrans ↔ sPrim relationship

`sPrim` is the engine's **immediate-mode primitive / 2D-overlay** submitter (lines, sprites, debug
shapes, HUD). It does **not** own a command buffer — it is a *producer of tags* for a `cTrans`.

### How they couple

`sPrim::Prim` (the per-primitive-batch packet, see [`sPrim_struct.md`](sPrim_struct.md)) holds:

| sPrim::Prim field | Role in the coupling |
|-------------------|----------------------|
| `mpTrans` (cTrans*) | the cTrans this batch submits into |
| `mpTag` (cTrans::TAG*) | sPrim's own tag array — **where submitLine appends** |
| `mTagNum` | running tag count for this batch |
| `mhTechnique` | shader technique handle (resolved via `sShader::getTechniqueFromName`) |
| `mViewVec` (MtVector4) | view vector for depth sorting |
| `mSubPriority`, `mDisp_lv` | pack into the tag sort key |
| `mPrimPacketBorder` | geometry-buffer capacity limit |
| `mMetaData`, `mModelMaterial` | optional 12-B metadata for transparent/overlay tags |

### The submit path — `sPrim::submitLine` (`0x45D1F0`)

For each primitive (e.g. one line segment):

1. **Depth sort key** = `dot(start_pos, prim->mViewVec.xyz) + mViewVec.w`, scaled by
   `mpTrans->mpContext->mPersRate`, clamped to 15 bits `[0, 0x7FFE]`.
2. **Capacity check** against `cTrans`'s shared geometry buffer
   (`mpGeoBufferBase + 16*mCmdCount - mpCmdStack > mPrimPacketBorder`).
3. **Allocate an 80-byte vertex slot** by decrementing `cTrans`'s downward write pointer
   (`mpTrans[2732] = mpCmdStack`), and write the start/end positions + colors there.
4. **Append a `cTrans::TAG`** into `prim->mpTag[mTagNum++]`:
   `sortkey = mSubPriority | (depth<<8) | (mDisp_lv<<23)`, `pcmd = vertex_slot`.
5. For transparent/overlay blends (`flags[1] & 0xA0`), also push a 12-byte METADATA entry
   (`mMetaData`, `mModelMaterial`) into the high-water region.

So the division of labour is: **sPrim computes per-primitive sort keys and owns the tag list;
cTrans owns the shared geometry/command memory and later sorts + replays all tags** into the GPU
stream. The `cTrans::CONTEXT.mTag` (scene prefix) and per-primitive sort key together form the full
radix-sort token.

### `sPrim::getcPrim` (`0xA34EE0`)

Acquires a primitive packet from a per-thread pool (`mpTrans[2737]` = thread index) and populates its
SCENECONTEXT (240-B block): the camera-relative translation (negated view-matrix column), the
view+proj matrices copied from the source transform, and a snapshot of the shader texture-handle table
(`sShader` param IDs). It assigns the packet a slot (`InterlockedIncrement` over a 0x400 ring) and the
sort priority (`a4 >> 6`). This is the per-frame setup that `submitLine` then feeds.

## The consumer side — sort → merge → replay (CMD model)

Once producers (sPrim, models, etc.) have filled each cTrans's `mpCmdList` (TAG array) and `mpCmdStack`
(variable-size CMD records, each beginning with a u32 **opcode**), the frame is finalized in three stages:

1. **Per-list merge sort** — `cTrans::sortCmdList` (`0xA584A0`) → `cTrans::mergeSortTags` (`0xA58E10`):
   bottom-up merge sort of `mpCmdList[mCmdCount]` by `TAG.sortkey` (ascending). Scheduled as a worker job.
2. **k-way merge** — `sRender::buildDisplayList` (`0x8F6480`): schedules the per-list sorts, then merges
   the sorted lists (picking the min `sortkey` across lists) into the final per-frame display list.
3. **Replay / dispatch** — `sRender::dispatchCommands` (`0x8F4120`), run on `sRender::render_thread`
   (`0x8F60C0`). For each tag: `pcmd = tag.pcmd`, `opcode = *pcmd`, then
   `switch(opcode-1)` over **21 cases** via jump table `jpt_8F448D` (`0x8F6060`). Each case issues the
   matching **D3D9** calls on `sRender->mpDevice` (`sRender+0x34`, `IDirect3DDevice9*`).

### CMD opcode set (first dword of each record)

Dispatch is `switch(opcode-1)`; jump table `jpt_8F448D` @ `0x8F6060` (index `i` → opcode `i+1`). In
every handler `ebx` = record ptr, `esi` = `sRender->mpDevice`. The handler addresses and record
layouts below were read from the jump table + each handler (and producers where isolable):

| Op | Handler | Role | Record (key fields) | D3D9 call(s) |
|----|---------|------|---------------------|--------------|
| 1 | `0x8F579C` | set scissor rect | viewport ints | SetScissorRect (+0x12C) |
| 2 | `0x8F5784` | set viewport | viewport block | SetViewport (+0xBC) |
| 3/4/11 | `0x8F4494` | **material / shader-state apply** (memcmp vs cached) — `+0x08`→shader block (`cTrans::newMaterial` @`0xA59190`: pps/pvs/textures), `+0x0C`→render-state block, `+0x14`→layer mask | BeginScene, SetViewport, SetRenderState, SetClipPlane, SetIndices, PS/material set, SetStreamSource loop |
| 5 | `0x8F581B` | **render-target set** — `cTrans::applyRenderTarget` (`0xA5CF80`), 40-B rec: `+4`target, `+8`mip, `+C`cubeface, `+14`fmt, `+18/+1C`w/h, `+24`scissorEn | EndScene, SetTexture×16(clear), SetRenderTarget(0..3), SetDepthStencilSurface, SetScissorRect |
| 6 | `0x8F5EAB` | **no-op** (default case) | — | — |
| 7 | `0x8F5B11` | clear + viewport — `+10`Z(f32), `+14`stencil/color, `+18/+1C`vp | EndScene, SetViewport, Clear |
| 8 | `0x8F5C03` | **draw primitive** — `cTrans::CMD_DRAW` (56 B, `cTrans::submitDrawCmd` @`0xA5D160`) | geometry callback → bind streams + DrawIndexedPrimitive (see below) |
| 9 | `0x8F5E35` | set z-test/depth toggle flag (`+4`) | — (state) |
| 10 | `0x8F5DDD` | generic deferred callback — `+4`fn, `+8`ctx, `+C`arg, `+10`endScene? | calls `fn(arg)`; optional EndScene |
| 12 | `0x8F5E17` | **SetClipPlane** — `+4`index, `+8..`plane(4f) | SetClipPlane (+0xDC) |
| 13,14,15 | `0x8F5EAB` | **no-op** | — | — |
| 16 | `0x8F5EAB` | **no-op at replay** — begin/end-subscene markers (`cTrans::beginSubScene`/`endSubScene`, 20 B); consumed by the sort/merge, **skipped** at dispatch | — |
| 17 | `0x8F5E2C` | set layer/visibility mask (`+4`) — tested by ops 3/4/8/11/21 via `(field>>30)&mask` | — (state) |
| 18 | `0x8F5EAB` | **no-op** | — | — |
| 19 | `0x8F57B0` | **resolve / screen-copy** — `cTrans::resolveScreen` (`0xA5CC40`), 44 B: `+18`mpScreenTempTexture, `+1C`mpScreenZTexture, `+28`region | EndScene, SetRenderTarget(0..3), SetDepthStencilSurface (backs the prologue StretchRect) |
| 20 | `0x8F5EAB` | **no-op** | — | — |
| 21 | `0x8F5E60` | viewport-scratch swap (mask-filtered) | EndScene |

> Two corrections to the earlier (rougher) table: **opcode 16 is NOT replayed** — subscene markers route
> to the default no-op case and are consumed only by the sort/k-way merge. And `cTrans::set_viewport_constants`
> (`0xA5CCC0`) is **not** an op-1/2 producer — it builds a *no-opcode* 24-B shader-constant scratch block
> (viewport scale/bias) referenced via `mpContext`'s constant slots, not a replay command. The op-1/2/7/9/
> 10/12/17/21 records are emitted by **inlined** helper code (no standalone producer function), so their
> layouts above come from the handler reads.

**Observed `IDirect3DDevice9` vtable offsets** (device = `sRender->mpDevice`): +0x48 GetBackBuffer ·
+0x88 StretchRect · +0x94 SetRenderTarget · +0x9C SetDepthStencilSurface · +0xA4 BeginScene ·
+0xA8 EndScene · +0xAC Clear · +0xBC SetViewport · +0xDC SetClipPlane · +0xE4 SetRenderState ·
+0x104 SetTexture · +0x114 SetSamplerState · +0x12C SetScissorRect · +0x170 SetVertexShader ·
+0x190 SetStreamSource · +0x1A0 SetIndices · +0x1AC SetPixelShader.

So the full pipeline is: **sPrim/models append TAGs+CMDs into cTrans → sortCmdList orders each list by
sort key → buildDisplayList k-way-merges them → dispatchCommands replays the merged stream as D3D9
calls on the render thread.** This closes the loop: the sort key `submitLine` computes (scene tag |
depth | priority) is exactly what determines draw order here.

### The draw record — `cTrans::CMD_DRAW` (opcode 8, 56 B)

Emitted by `cTrans::submitDrawCmd` (`0xA5D160`), the central draw-submit primitive (100+ callers across
model/effect rendering). Carved off `mpCmdStack`:

| Offset | Field | Meaning |
|--------|-------|---------|
| 0x00 | mOpcode | = 8 (DRAW) |
| 0x04 | mpGeometry | geometry/mesh resource (w/h at +0x1C/+0x1E) |
| 0x08 | mFlags | 0 / reserved |
| 0x0C | mIdxFirst / mVtxFirst | draw-range start (index/vertex), from caller param0 |
| 0x14 | mIdxLast / mVtxLast | draw-range end; handler uses `Last - First` as the counts |
| 0x20 | mRange20/24/28 | base offsets / extra range data (from caller param2) |
| 0x30 | mDrawState | snapshot of `mpContext->mDrawState` (CONTEXT+0x1F8) |

The appended TAG takes `sortkey = mpContext->mTag` (CONTEXT+0x234) — so every draw inherits its scene's
sort prefix.

### Opcode-8 handler — geometry → D3D9 binding (`dispatchCommands` @ `0x8F5CF7`)

1. `(mDrawState >> 30)` tested against the active layer/visibility mask (`var_1134`, set by opcode 17) → skip if filtered; `memcmp` vs the cached material/state (redundant-state elision).
2. **LOD select:** `pGeo = mpGeometry`; `edi = pGeo[0x10 + ((pGeo[0x22] & 1) & Camera)*4]` — one of **two submesh/LOD objects** at `geo+0x10` / `geo+0x14`, chosen by the `geo+0x22` flag byte and the global `Camera` mask.
3. **Resolve:** `call pGeo.vtbl[0x28]` → readiness / vertex-format code (**3**, **5**, or other).
4. **Build MESH:** `call pGeo.vtbl[0x48](geo, range…, &meshOut)` — builds a MESH descriptor into a local (`var_1158`); arg count varies by the code from step 3 (3 → 1 range arg, 5 → 2). Skips the draw if `meshOut` is null.
5. **Submit:** the draw range (`mIdxLast-mIdxFirst`, `mVtxLast-mVtxFirst`, plus `mRange20/24/28`) and the MESH are handed to `sRender.vtbl[+0x88]`, which binds the VB/IB streams (SetStreamSource / SetIndices), shaders (SetVertexShader / SetPixelShader), and textures (SetTexture×13) and issues `DrawIndexedPrimitive`. `meshOut.vtbl[8]` releases the descriptor.

So the actual draw is **never a direct device-vtable call in the opcode handler** — it is issued through
the geometry object's own `vtbl[0x48]` MESH builder and `sRender`'s draw-submit method. Geometry object
layout used here: `+0x10`/`+0x14` = the two LOD/submesh pointers, `+0x1C`/`+0x1E` = width/height (u16),
`+0x22` = LOD-select flag byte, `vtbl[0x28]` = resolve/classify, `vtbl[0x48]` = build MESH descriptor.

### sPrim submit primitives

`sPrim` exposes immediate-mode submitters that all share the same tag-append + double-ended-buffer
mechanic; the **geometry-record format byte** (low 5 bits of the record's first dword) tags the type:

| Function | Addr | Record | Format byte | Used by |
|----------|------|--------|-------------|---------|
| `sPrim::submitLine` | `0x45D1F0` | 80 B, 2 verts | 1 | `cUtil::drawSphere`/`drawCapsule` (debug wireframe) |
| `sPrim::submitSprite` | `0x459DA0` | 144 B, 4 verts (pos+color+UV `*4096` fixed-point) | 0xB | `sPrim::drawSprite` (`0x45B410`), HUD/effect quads |

Both: capacity-check `mpGeoBufferBase + 16*mCmdCount - mpCmdStack > mPrimPacketBorder`, allocate the
vertex record downward off `mpTrans`'s geometry stack, then append a `cTrans::TAG` into `prim->mpTag`
with `sortkey = subPriority | depth<<8 | disp_lv<<23`. The `uEffectVFR::render*` family (billboard,
polyline, polygon, texline, lensflare, …) are a separate **effect** subsystem that also acquires prim
packets via `sPrim::getcPrim` but builds its own geometry.

## Per-view scene setup — `cTrans::setupScene` (`0xA594D0`)

Signature: `setupScene(float *projMat@<ecx>, float *viewMat@<edx>, cTrans *this, int *viewportRect)`
(viewportRect = `{x0, y0, w, h}`). Everything writes through `this->mpContext` — it fills the **active**
CONTEXT (per-view, inside a `beginSubScene`/`endSubScene` bracket; it does not manage `mSubSceneDepth`).
~23 callers, all per-pass render drivers (e.g. `sub_A77170` = ShadowCast, `sub_8E6830` = main scene,
`uMovie::draw`, plus lighting/reflection/post passes). It:

1. **Copies the input matrices** into the CONTEXT: `mViewMat@0x00` ← viewMat, `mProjMat@0x40` ← projMat.
2. **Computes inverses & products** (full 4×4, with det==0 → `MtMatrix::Identity` fallback):
   `mProjInvMat@0x80` = inv(proj); `mViewProjMat@0xC0` = proj·view; `mViewProjInvMat@0x140` = inv(viewProj).
   (It does **not** write `mViewInvMat@0x100`.)
3. **Builds the frustum** `mFrustum[6]@0x180` from the viewProj rows (standard "row4 ± rowN" clip-plane
   combinations); planes 3–5 and `mTilePlane@0x1E0` go through `MtPlane::fromPoints` (`0x8BD540`:
   `n=normalize(cross(P1-P0,P2-P0)), d=-dot(n,P0)`).
4. **Sets** `mViewport@0x200` ← viewportRect, and `mPersRate@0x1F0` = `1 / (sRender[+0x28] * projMat[5])`.
5. **Emits per-view shader-constant uploads**: pushes 64-B matrix blocks (view, proj, viewProj, their
   inverses, Identity) onto `mpCmdStack`, storing each block ptr into the CONTEXT constant table
   (`mpTextureTable[slot]`) keyed by runtime-resolved shader param IDs; sets `mStateDirty |= 0x20000000`
   per upload. Tail-calls `cTrans::set_viewport_constants` (`0xA5CCC0`) for the viewport scale/bias
   constants (`0.5/w+0.5`, `1/w`, `1/h`) and `mpViewportConst@0x228`.

`setupScene` does **not** set `mBlendState`/`mDrawState` or apply a render target — the caller brackets it
with `applyRenderTarget` and sets `mTag` before/after. Most of its 0x3764 bytes are the two matrix
inverses (inline SSE/FPU) and the six frustum-plane builds.

## SE (`nDraw`) cross-reference — architecture confirmation only

In the **Special Edition** build (newer MT Framework, D3D11-style renderer) the `cTrans` lineage was
refactored from one fat class into a whole `nDraw::` namespace (~40 classes: `Scene`, `CommandCache`,
`Material`, `BlendState`/`RasterizerState`/`DepthStencilState`, `CBuffer`, `InputLayout`, …). There is
**no 1:1 SE struct to port onto DX9 `cTrans`**, and SE offsets/layouts do **not** transfer (per the
"SE base-engine ≠ ground truth" rule). It is useful only as a naming/architecture check:

- **`nDraw::CommandCache`** is the descendant of cTrans's command list and corroborates the model:
  `mTags` is typed **`cDraw::TAG*`** (the engine's canonical base name is **`cDraw`**; DX9 `cTrans`
  is the older spelling), with `mpBuffer`/`mBufSize`/`mBufPt` (≈ our geometry buffer) and
  `mTagNum`/`mValidTagNum` (≈ our `mCmdCount`). Confirms the TAG-array + double-ended-buffer reading.
- **`nDraw::Scene`** is the descendant of `cTrans::CONTEXT` and is almost entirely scene render-target
  pointers (`mpMainTarget`, `mpGBuffer`, `mpHDRTarget`, 25-slot RT/DS/texture arrays). This confirms
  the DX9 CONTEXT's unresolved `0x228–0x394` region is in spirit a **scene render-target + texture
  binding table** — consistent with `beginSubScene` snapshotting the shader texture table into
  `mTextureTable@0x294`.

Ground truth for DX9 `cTrans` remains the **PS3** build, as used above.

## Status / unresolved
- `cTrans` tail `_unk2A84..2A8C`, `_unk2ABC`, `_unk2AC8..2ADC`, `_unk2AEC..2AF4` — touched by the
  draw/flush path but not yet named.
- CONTEXT `_unk22C/_unk230` (2 dwords) and `_sceneParamHdr[92]` (0x238–0x290) — per-view scene-record
  header; role known (scene-record + param state), individual fields not enumerated.
  `mpViewportConst@0x228`, `mTag@0x234`, `mTextureTable[512]@0x294` are confirmed.
- `cTrans_vtbl` 5 slots (`sub_A58200`, `sub_8FC2F0`=stub, `sub_521BF0`, `sub_A582C0`, `sub_A553B0`)
  — not yet mapped to PS3 method names.
