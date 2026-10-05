# EFL_GENERATOR — the serialized (general) generator descriptor — DX9

The **general generator block**: one record per generator in the on-disk EFL effect list. At runtime
it is reached via `uEffectVFR::Generator.mpGeneratorParam` (Generator **+0xB0**), which is index slot 0
of the per-generator 16-byte record (`(offset<<8)|typeByte` packed; see `RE/uEffectVFR_findings.md`).
DX9 places generator blocks **first** in the record; SE places them 2nd-to-last (before move blocks) —
this is file/record ordering only and does not affect the block's internal layout (it is reached by
pointer, not by linear position).

> **Runtime Generator ↔ Particle nodes (2026-06-03):** the runtime `uEffectVFR::Generator` (544 B, distinct
> from this on-disk descriptor) owns **two intrusive doubly-linked lists** of particle nodes threaded through
> `uEffectVFR::Particle.mpPrev/mpNext`: the **Move list** (`mpMoveTopParticle@+0x0` / `mpMoveBotParticle@+0x4`,
> live particles) and the **Stock list** (`mpStockTopParticle@+0x8` / `mpStockBotParticle@+0xC`, free pool).
> `uEffectVFR::Generator::init` (0x9DECD0) builds the initial Stock free-list. These four head/tail pointers
> are now typed `uEffectVFR::Particle*` (were raw `uint`). The node base class and all 15 render-type children
> are documented in **`RE/particle_type_structs.md`** — the canonical Particle reference.

## Status: the type already exists — `rEffectList::EFL_GENERATOR`, 484 bytes (0x1E4)

A prior session reversed this into a 484-byte DX9-specific type. There is exactly **one** generator
descriptor in the DX9 IDB, read via `mpGeneratorParam` for **every** generator — so structurally this
484-byte record IS the general generator descriptor. It is NOT a base+appended-tail; see the SE
divergence note below. This session did not redeclare it (doing so would rewrite the decompiles of
`setRequest` / the timer funcs that are already typed against it); it adds the verification tiering
below.

## Verification tiers

### Tier 1 — usage-confirmed THIS session (base pointer traced to mpGeneratorParam; semantics match name)

| Offset | Field | Type | Confirmed by |
|------:|-------|------|--------------|
| 0x3C | `ParentNo` | int | `setRequest` 0x9DDF40 — `[edi+3C]` passed to `sVibration::req_with_parent` (joint index) |
| 0x76 | `WaitFrame` | MtRangeU16 | state-0 init in `uknGenBehaviorFunc1`/`Generator::updateSingleGenerator` → `mSetTimer = WaitFrame` |
| 0xB0 | `LoopNum` | MtRangeU16 | `uknGeneratorTimerFunc` 0x9DE250 — reseed `base.s + rand%(r+1)` (per-burst loop window) |
| 0xB4 | `SetFrame` | MtRangeU16 | `uknGenLoopFunc` 0x9DE360 — reseed `base.s + rand%(r+1)` (inter-burst interval) |
| 0xB8 | `SetInterval` | u16 | `uknGeneratorTimerFunc` — fractional-frame distribution gate |
| 0xBC | `SetFrameDist` | float | `uknGenLoopFunc` — fractional-frame distribution gate |
| 0x30 / 0x40 | `Pos` / `Quat` | MtFloat3 / MtVector4 | `moveUnitGenerator` 0x96FF00 — `Pos` (x,y,z) as offset + `&Quat` → `uEffectVFR::setQuatParentOfs(quat, parent, pos, unit, ParentNo, …)`: unit placement relative to a parent joint (2026-10-05) |
| 0xC0 | `member_0xc0` | MtRangeF | `initGeneratorParam` — `addss [esi+0C0h]` / `mulss [esi+0C4h]` → Gen.mParticleScaleBase. (Was `IntervalFrameDist` float + `MtRangeF`@0xC4, a 4-byte overlay error that shifted everything up to 0x13B) |
| 0xC8 / 0xC9 | `RangeType` / `RangeDirType` | u8 / u8 | `sub_999640` switch on byte @0xC8; `Funcx90` reads byte @0xC9 |
| 0xCA / 0xCB | `RangeOptionFlags` / `uknRangeFlag` | u8 / u8 | `initGeneratorParam` (word @0xCA, byte cmp @0xCB) |
| 0xCC / 0xCD / 0xCE | `RangeStripType` / `RangeStripFlag` / `RangeStripPartsNo` | u8 / u8 / s16 | dword test @0xCC (sub_9774B0, sub_99A8A0); byte @0xCD and word @0xCE (sub_99A8A0/99AFD0/99B270). The names are SE-derived; the offsets come from DX9 code |
| 0xD0 | `RangeStripPath` | char[64] | **`createGeneratorResources`** — `cmp byte [edi+0D0h]` / `lea` → `rEffectStrip` (.efs) |
| 0x110 | `UknRangeThing` | MtRangeF[4] | `[0]` = {base 0x110, range 0x114}: `initParticleMoveNone`, `movevel_transform` (addss/mulss) |
| 0x130 | `RangeDivideNum` | u32 | `sub_999640` — dword, modulus divisor `n % (RangeDivideNum+1)` |
| 0x140 / 0x180 | `ExtVibrationPath` / `SoundRequestPath` | char[64] each | **`createGeneratorResources`** → `rVibration` (.vib) / `rSoundRequest` (.srq) |
| 0x13C | `mVibReqType` | u8 | `setRequest` switch (disasm `cmp byte ptr [edi+13Ch]`; 0=none, 1=simple, 2=at_pos, 3=with_parent). Also gates `finish_requests`. (Was typed `float` in the IDB → split into bytes 2026-10-05.) |
| 0x13E / 0x13F | `mVibReqArg0` / `mVibReqArg1` | u8, u8 | `setRequest` — `movzx byte [edi+13Eh]` / `[edi+13Fh]`, packed `arg0 \| arg1<<16` → last `req_*` arg |
| 0x1C0 | `VibReqNo` | u16 | `setRequest` — `movzx word [edi+1C0h]` → `req_*` arg1. Mirrors `SeReqNo`@0x1C8 |
| 0x1C2 | `VibOptionFlag` | u16 | `finish_requests` — bit0 = stop vib on finish. Mirrors `SeOptionFlag`@0x1CA (tested as dword@0x1C8 `& 0x10000`). Was mis-named `ExtVibrationPathOffset` |
| 0x1C4 | `VibPriority` | u32 | `setRequest` — `mov [edi+1C4h]` → `req_*` arg2 (**not** the sound request; the earlier doc row was wrong) |
| 0x1C8 / 0x1CA | `SeReqNo` / `SeOptionFlag` | u16 bitfields | `finish_requests` (SeOptionFlag bit0 = stop SE on finish) |
| 0x1CC | `member_0x1cc` | **int** | `updateWorldMatrix` @0x96BE38 — `mov eax,[esi+1CCh]` (dword), self-relative sub-block offset, gated on `pGen->mStatus & 0x10`. Was mis-typed `SoundPathOffset` int16 + `member_0x1ce`; merged 2026-10-05 |

Also read but on the per-instance randomized-visual path (`initGeneratorParam` 0x96AEC0, all
`base + range*rand`): a count byte at **+0x0B**, the `RandomNo` array at **+0x10**, and several
scale/color/intensity range pairs in the **0x118–0x1D0** region plus keyframe-presence flag dwords
(~0x1CC). These are confirmed *reads* but their individual field identities beyond RandomNo are not
pinned — left to the per-type work.

### Tier 2 — prior-session-named, NOT verified this session

The remaining members (`GroupFlag`, `MaterialFlag`, `someJointIdx`@0x5C,
`Scale`@0x7C, `Range`@0x94, `SetNum`@0xAC, …; `Pos`/`Quat` and the 0xC0–0x13B block are now Tier 1, see above) carry plausible names from the prior pass but were not confirmed by a reader this
session. Reason they could not be cheaply spot-checked: offsets +0x30 / +0x7C / +0xAC **collide** with
unrelated fields on the *particle node* and the *runtime Generator* object (e.g. `initParticleBillboard`
reads node+0x30; `updateWorldMatrix` reads Generator+0xAC), so an offset scan cannot attribute them to
the param block. Treat Tier-2 names as probable-but-unproven.

#### Negative result (this exploration round): the matrix builder does NOT read param Pos/Quat/Scale

`uEffectVFR::Generator::updateWorldMatrix` (0x96BE10) was the natural candidate to confirm
`Pos`@0x30 / `Quat`@0x40 / `Scale`@0x50. In the **typed** decompile it has **zero** `mpGeneratorParam->`
member accesses — it builds the world matrix from the **runtime Generator** instead
(`pGen->uCoordBase.*` for rotation/position, `Generator+0x44/0x50` = `mLscaleBase`/`mLscale` for scale,
and `Generator+0x10C` flags). The earlier linear register-trace that *appeared* to read param +0x30/
+0x40/+0x50/+0x70 was contaminated: this 0x3EF0-byte function keeps three live base pointers (`esi`=param,
reassigned mid-body; `edi`=runtime Generator; `ebx`=runtime object), and the script conflated them.
**Lesson:** on large functions, attribute fields via the Hex-Rays-typed decompile (`mpGeneratorParam->`
renders only for genuine param reads), never via offset/register scans.

Implication: the descriptor's `Pos`/`Quat`/`Scale` are most likely consumed at **load/init time** (copied
into the runtime Generator's uCoord/mLscale), not per-frame — so confirming them needs the load path, not
the matrix builder. Still unproven; Tier-2 stands for those three.

#### Self-relative sub-block offset at +0x1CC (sidecar mechanism)

`updateWorldMatrix` does one genuine param read (re-verified 2026-10-05 from disasm: `esi = [edi+0B0h]` = `pGen->mpGeneratorParam`, gate `test byte [edi+16h],10h`): `eax = mpGeneratorParam[+0x1CC]` (dword); `if(eax) esi = param + eax`
— a **self-relative offset** to an embedded sub-block (a keyframe/path vector source). This is DX9's inline
analog of SE's `*PathOffset` u16 fields (`RangeStripPathOffset`@0xB8 etc.): instead of a separate file
pointer, DX9 stores a byte offset relative to the generator block. The "extended generator / sword-trail"
data is reached this way. Not chased here.

#### initGeneratorParam visual-range reads (anchored, identities tentative)

`initGeneratorParam`'s `v5 = *(Generator+176)` is **never reassigned** — a clean anchored reader. Beyond
the Tier-1 timing fields it reads these param-block ranges as `base + range*rand` (so each is a
`{base, range}` pair) into the runtime Generator's randomized-visual slots:

| Param offset | Pattern → runtime slot | Likely identity (SE concept) |
|------:|----|----|
| 0x0B | count byte for RandomNo modulo | `RandomNoNum` (SE 0xF) |
| 0x10 | indexed array `[i]` | `RandomNo[8]` ✓ (confirmed read) |
| 0x74/0x76 | base + rand%(r+1) → Gen+206 | a frame-offset range (near `WaitFrame`) |
| 0xC0 | `base(0xC0) + rand*range(0xC4)` → Gen+60 | particle-scale pair (SE `ParticleScale` concept) |
| 0x118–0x12C | 3× `base + rand*range` → Gen+68/72/76 | intensity/color range (SE `Range`/color concept) |
| 0x1B8–0x1D0 | 3× `base + rand*range` → Gen+464/468/472 | a 3-axis scale range (SE `RangeScale` concept) |
| ~0x1CC+ | dword presence flags gating the above | keyframe-param presence flags |

These offsets are **confirmed param-block reads** (anchored base), but the SE-concept identities are
inferred from the `base+range*rand` shape and rough semantic match — not pinned to a specific SE field at a
specific offset (DX9's layout diverges from SE). Tier them "read-confirmed, identity-tentative."

## SE divergence (SE = concepts only, NOT offsets)

SE's PDB-named `rEffectList::EFL_GENERATOR` is **192 bytes** and diverges from DX9 **from 0x30 onward** —
they are not the same record with a tail:

| Concept | SE offset | DX9 offset |
|---------|----------:|-----------:|
| `RandomNo` array | 0x10 | 0x10 (coincidence) |
| `RandomNoNum` | 0x0F | ~0x0B |
| 0x30 region | Vib/Se request config | `Pos`/`ParentNo`/`Quat` (Tier-2) |
| `ParticleScale` | 0x40 | n/a (DX9 has `Quat` here) |
| `SetNum` | 0x48 | 0xAC (Tier-2) |
| `LoopNum` | 0x4C | **0xB0** (Tier-1) |
| `SetFrame` | 0x50 | **0xB4** (Tier-1) |
| `SetFrameDist` | 0x58 | **0xBC** (Tier-1) |
| `Range[3]` | 0x60 | 0x94 (Tier-2) |
| `RangeStripType` | 0x7C | 0xD0 (Tier-2) |

SE is a reliable source for what a field *means* (concept/naming), never for its DX9 offset. Every DX9
offset above came from DX9 code.

> **IDB member names re-synced (2026-10-05).** 139 `member_0xNNN` auto-names in `rEffectList::EFL_GENERATOR`
> no longer matched their real offsets (e.g. `member_0x131` sat at 0x135) because the layout had shifted after
> they were generated. All were renamed to their true offsets. Names that came from SE (`ExtVibrationPathOffset`,
> `SoundPathOffset`) and that DX9 readers contradicted were corrected as shown in the Tier-1 table.
> **Consequence for the sidecar question below:** DX9 has *no* confirmed `ExtVibrationPathOffset`. The 0x1C2
> slot is a flag word. The DX9 resolver has since been found; it uses inline paths, as described below.

## "Extended generator" (sword-trail) = `rEffectStrip` sidecar — SE-CONFIRMED mechanism

There is **no second/larger generator descriptor** declared in the DX9 IDB — only this one 484-byte
record. The "extended generator used mostly by sword trails" is a **sidecar resource** referenced from
the generator block via a self-relative byte offset — *not* a distinct generator record.

**SE proof (read-only cross-ref, 0xCD4980 `rEffectList::ResourceInfo::createGeneratorResources(EFL_GENERATOR*)`):**
the consumer reads three packed u16 path-offset fields from the generator block and resolves each to an
embedded sub-block at `pGeneratorParam + offset`, then `sResource::create_3(&DTI, ptr, 1)`:

| SE field (concept) | SE offset | Resolves to (DTI) | File ext | Status byte on fail |
|--------------------|----------:|-------------------|----------|---------------------|
| `RangeStripPathOffset`  | **0xB8** (`(DWORD*)+46`, low u16) | `rEffectStrip` | `.efs` | mStatus \|= 0x20 |
| `ExtVibrationPathOffset`| **0xBA** (`(WORD*)+93`)            | `rVibration`   | `.vib` | mStatus \|= 0x200 |
| `SoundRequestPathOffset`| **0xBC** (`(DWORD*)+47`, low u16) | `rSoundRequest`| `.srq` | mStatus \|= 0x400 |

(Offset arithmetic via `int_convert`: +46 dword = 0xB8, +93 word = 0xBA, +47 dword = 0xBC — three
consecutive u16s at SE 0xB8/0xBA/0xBC.) The **sword-trail effect = `rEffectStrip` (.efs)** reached
through the RangeStrip path offset. This confirms the user's "extended generator, mostly sword trails"
as the strip sidecar, and confirms the self-relative-offset sidecar mechanism (DX9's `+0x1CC` read in
`updateWorldMatrix` is the same pattern).

**DX9 side — RESOLVED (2026-10-05).** The resolver is **`rEffectList::ResourceInfo::createGeneratorResources`
(0xA3B110)**, with signature `(EFL_GENERATOR *pGenParam@<edi>, ResourceInfo *pInfo@<esi>)`. It was found as the only function
that references all three DTIs (`rEffectStrip`, `rVibration`, `rSoundRequest`). It does the same job as SE, with the same
failure bits, but **DX9 does not use self-relative offsets.** The generator block carries **inline `char[64]` paths**:

| DX9 offset | Field | Resource | → `ResourceInfo` | fail bit |
|-----------:|-------|----------|------------------|---------|
| 0xD0  | `RangeStripPath`   | `rEffectStrip` (.efs) | `mpRangeStrip` +0x14  | `Status \|= 0x20`  |
| 0x140 | `ExtVibrationPath` | `rVibration` (.vib)   | `mpExtVibration` +0x24 | `Status \|= 0x200` |
| 0x180 | `SoundRequestPath` | `rSoundRequest` (.srq) | `mpSoundRequest` +0x28 | `Status \|= 0x400` |

So SE's u16 `*PathOffset` fields at 0xB8/0xBA/0xBC have **no DX9 counterpart**. The earlier claim that the `+0x1CC` read
in `updateWorldMatrix` was "the same pattern" as SE's path offsets is withdrawn: +0x1CC is a separate keyframe-style
sub-block offset.

**Load chain:** `rEffectList::load` → **`rEffectList::create_resource_infos`** (0xA3DD10). For each 16-byte `ContentPtr`
record *i* (`(offset<<8)|type` dwords), it rebuilds `ResourceInfo[i]` (stride **0x34**; the IDB type was 0x30 and has
been extended with `member_0x30`):
- `ResourceInfo::release_all` (0xA3B030) releases `+0x04..+0x28`.
- `createGeneratorResources(rec[0])` handles the strip, vib and srq sidecars above.
- `create_particle_resources(rec[1])` (0xA3B1A0) switches on the particle type and creates `rModel` (type 5, +0x50 path,
  fail 0x10) or `rEffectAnim` (+0x130 path, fail 0x8) into +0x10, plus sub-resources via `sub_A3B450/4E0/570/600`. It
  also **copies** particle-param +0x68/+0x6C into ResourceInfo +0x2C/+0x30. So `mpForce` @+0x2C is not a `cResource`
  in DX9 despite its SE-style name.
- `create_move_resources(rec[3])` (0xA3B320) handles move type 3: an `rEffectStrip` path at move-param +0x80 → `mpPathStrip`
  +0x18 (fail 0x40). For all move types 0–6 it then reads `sub_960650(moveParam)` and creates two `rEffectList`s →
  `mpBounceEffect` +0x1C (fail 0x80) and `mpFinishEffect` +0x20 (fail 0x100).

The child/unit generator gets one extra ResourceInfo after the per-record ones, built from the `GeneratorType` /
`mGeneratorMoveType` records.

## Load path & the `createGenerator` (ex-`setFlags`) naming finding

> **Update:** the function was renamed `sDevil4Effect::setFlags` → **`uEffectVFR::createGenerator`** (see the
> deep-dive section below). The reasoning below is preserved as the historical trail; "No rename applied yet"
> no longer holds.

The full EFL load chain is now mapped:

```
uEffectVFR::setEffectList (0x9686E0)   store rEffectList*, addRef, copy mBaseFPS
  → sub_96AC10 (teardown of OLD EffectArr; NOT applyUnitParam — runs pre-store)
  → uEffectVFR::createGenerator (0x96A770, ex-setFlags)   ← THE LIST LOADER / GENERATOR BUILDER
        [also invoked lazily from uEffectVFR::move on first tick if not yet built]
        walks ContentPtr (16-byte records), filters by mGroupFlag & mpParamBlock,
        memAlloc EffectArr (544 B/gen), loops:
          → uEffectVFR::initGenerator (0x96ACA0)   per-record parse → Gen+176/180/184/188 + enums
                → uEffectVFR::initGeneratorParam (0x96AEC0)   visual-range reads from mpGeneratorParam
        sets mAxisType |= 0x100 on success
```

**`sDevil4Effect::setFlags` is misnamed** — it is not a flag-setter, it is the **generator-build /
list-load orchestrator** (alloc `EffectArr`, loop `initGenerator`, set mode bits). The user's instinct
("it's really an apply/build function, maybe `applyUnitParam`") is **directionally correct**: the name is
wrong and it is the build path. The specific guess `applyUnitParam` is off, though — by SE cross-ref the
functional analog is the **`createGenerator` family** (`uEffect::createGenerator` 0xCAFA90: restart →
createParticleManager → allocGeneratorBuff → initJoint → initParticleManager → set flag 0x1000000), which
matches `setFlags`'s shape. **No rename applied yet** — SE decomposes the build into sub-calls DX9 inlines
monolithically, and `uEffectVFR`'s exact SE class (`uEffect` vs `uBaseEffect`, both of which have their own
`applyUnitParam`) is not yet pinned. Hold the rename until the class mapping is confirmed.

**SE's real `applyUnitParam`** (`uBaseEffect::applyUnitParam` 0xCB8A20) is a *separate, smaller* hook: it
reads `mpEffectList->mUnitParamOffset → mpParamBuff[offset]` and sets unit-level flag bits
(masks 0x3FF0000 / 0x8000000). That `mUnitParamOffset` read does **not** appear in DX9 `setFlags` — so DX9's
applyUnitParam-equivalent (if distinct) is elsewhere. **Next narrow check:** grep DX9 for the `0x3FF0000`
mask or the `mUnitParamOffset` read to find a separate DX9 `applyUnitParam`.

### `createGenerator` (0x96A770, formerly mis-filed `sDevil4Effect::setFlags`) deep-dive

**Renamed this session** to `uEffectVFR::createGenerator` — it is a `uEffectVFR` vtable virtual (slot near
`renderGenerators`), not an `sDevil4Effect` member; the old prefix was a misfiling. SE analog =
`uEffect::createGenerator` (0xCAFA90, virtual, returns bool). Invoked from **two** paths:
- **Eager:** `setEffectList` calls it at set-time when `!(mMode & 4)`.
- **Lazy/deferred:** `uEffectVFR::move` gate-1 (0x9645D9): `if (!(mAxisType & 0x100) && mpEffectList) build now`.
  Since the function sets `mAxisType |= 0x100` on success, the lazy build fires exactly once. So this is the
  generator-build orchestrator, reached eagerly *or* on first tick — **not load-time-only**.

The function has three phases:

**Phase 0 — reset + move-buffer presize (0x96A79B–0x96A858).** Masks `mMode` (clear/set flag bits
0x2001), copies `mLifeFrame→loopLimit`, resets timers. Reads `mpEffectList->EffectListNum` (early-out if 0).
If `GeneratorType!=0 && !(mMode&0x200)`: the move-template object `this->member_0x1a0` gates a presize —
reserve `get_move_buffersize(mGeneratorMoveType)+64` into `v41`, cache `[member_0x1a0+420]` into
`member_0x1a4`; else set `mMode|=0x1000` (the single-child path) and pull a default from
`sDevil4Effect::mpInstance+0x8A14`.

**Phase 1 — count survivors (0x96A862).** Walks the 16-byte `ContentPtr` records; `param_3` =
count of records passing `(mGroupFlag & rec[0]) && (mpParamBlock & rec[1])`. This drives allocation
sizing only.

**Phase 2 — allocate + build.** Two branches:
- **`mMode & 0x1000` → single child-unit generator.** `memAlloc(48*param_3 + 544)`, one Generator,
  `Generator::init(slot,0,null,0)`, then `initChildGenerator(this)` fills it from the EFL `+112/+116`
  template records (literal enum byte 19, transType 64) and builds a 12-dword-stride sub-array
  (1.0f-initialized). This is the "GeneratorType" composite/child path.
- **else → multi-generator.** `getMem(8*param_3)` allocates a **size-table** = two parallel `param_3`-length
  u32 arrays `{particleCount[], bufSize[]}`; `getEfxFlag` (0x9DD5A0) fills one entry per surviving record
  (`bufSize = particleHandling + particle_typing + life-block + get_move_buffersize`). The per-generator
  total `544*param_3` + Σ`(count*bufSize)` + `v41` is `memAlloc`'d as `EffectArr`; each slot then gets
  `Generator::init(slot, particleSize, pParticleBuf, count)` which lays out that generator's particle
  free-list inside the shared buffer.

  Finally the **per-generator init loop** (0x96ABB1): bound = **total** record count (not survivor count) —
  it scans every ListNo, skips non-matches via `matchGeneratorFilter`, and advances `GeneratorNo` only on a
  match, calling `initGenerator(this, GeneratorNo, ListNo)` per survivor. Success → `mAxisType |= 0x100`.

**Callees renamed this session (purpose confirmed by use):**

| Addr | Old | New | Role |
|------|-----|-----|------|
| 0x9DD560 | sub_9DD560 | `uEffectVFR::matchGeneratorFilter` | per-record include predicate (group/param mask test) |
| 0x96BB70 | sub_96BB70 | `uEffectVFR::initChildGenerator` | single child-unit generator build (0x1000 path) |
| 0x9DECD0 | sub_9DECD0 | `uEffectVFR::Generator::init` | per-generator ctor: zero 544B, Identity matrices, build particle free-list (args: `pGen@eax, particleSize@esi, pParticleBuf@dl, count`) |
| 0x9DD5A0 | (kept) | `uEffectVFR::getEfxFlag` | per-record work-buffer-size accumulator → fills size-table |
| 0x96A720 | (kept) | `sDevil4Effect::get_move_buffersize` | MoveType→bytes: {0:64,1/4:96,2:80,3/5:128,6:112} |

**"Undefined variables" — two classes (resolved differently):**
1. *Callee register-convention args* (`param_1`/`param_2`/`MoveType` etc. at the call sites): these were
   decompiler artifacts of untyped `__usercall` callees. **Fixed** by setting the callee prototypes — the
   call sites now render cleanly. This was the real readability win.
2. *ebp-scratch frame phantoms* (`v49`, `param`, `param_1`, `p_param`, `p_param_1/2`): `setFlags` reuses
   `ebp` as a general scratch register and IDA flags it "modified by hidden variable assignment(s)" — it
   **cannot** model the frame, so these slots alias unpredictably. They are **not** function arguments
   (the only caller, `setEffectList`, passes just `this@ecx`). **Not renamed** — forcing names would assert
   a clean backing that doesn't exist. Documented via inline comments instead. `setFlags`'s true signature
   is `(this@<ecx>)`; the prototype was left unchanged.

## Pos/Quat/Scale — Pos/Quat CONFIRMED (2026-10-05); the "suspect" verdict below is withdrawn

**Correction.** A typed field-access sweep over the 110 effect functions that load `mpGeneratorParam` found the consumer:
**`uEffectVFR::moveUnitGenerator` (0x96FF00)** reads `Pos.x/y/z` and passes `&Quat` together with `ParentNo` to
`uEffectVFR::setQuatParentOfs` (and `&Quat` to `sub_969990`). That is a transform: it places the child unit
relative to a parent joint. So `Pos`@0x30 and `Quat`@0x40 are real. Only `Scale` remains unconfirmed. The four readers
below were simply not the consumer. Historical reasoning follows.

Four independent readers have now been ruled out as consumers of param `Pos@0x30` / `Quat@0x40` /
`Scale@0x50`: the matrix builder (`updateWorldMatrix`), the list loader (`setFlags`), the record parser
(`initGenerator`), and — by SE analog — `createGeneratorResources` (reads only the three sidecar offsets).
Combined with the SE-divergence table (SE's 0x30 region is **Vib/Se request config**, not a position), the
prior-session DX9 names `Pos@0x30`/`Quat@0x40`/`Scale@0x50` are most likely **misattributed** — which
would explain why no reader treats them as a transform. **Reframe:** these three Tier-2 names are suspect,
not just pending a confirming reader. The runtime transform is built from `uCoordBase` + `mLscale`/
`mLscaleBase` (0x44/0x50 on the *runtime* Generator), whose load-time source is still unidentified.

## uEffectVFR ↔ SE class mapping — it's a MERGE, not a 1:1

DX9 `uEffectVFR` (DTI: `class=uEffectVFR size=0x1D0 parent=uCoord`, init 0xB7C870) maps to the **collapsed
SE `uCoord → uBaseEffect → uEffect` subtree** — DX9 flattens into one class what SE split across a 2-level
hierarchy. Pinned from SE base-subobject inspection (read-only):

- SE `uBaseEffect` (416 B): base subobject = **`uCoord`** @0 → parent `uCoord`. **Matches DX9's DTI parent exactly.**
- SE `uEffect` (544 B): base subobject = **`uBaseEffect`** @0 → `uEffect` derives from `uBaseEffect`.
- DX9 `uEffectVFR` carries the fields of **both** levels in one flat class:
  - uBaseEffect-level: `mStatus`/`mMode`, `mpEffectList`, `mBaseFps`, delta-time rates, `mOfs`/`mDir`,
    `mTransparency`/`mIntensity`/`mColorScale`, `mGroupFlag`, `mAxisType` (cf. SE getters
    `getOfs`/`getDir`/`getTransparency`/`setAxisType`/`getCullingGroup`).
  - uEffect-level: `mParticle3DScale`, `mParticleScale`, `mLifeFrame`, `mWaitFrame`, and the
    generator-array machinery.

This is **why** both `setEffectList` (SE: `uBaseEffect`-virtual) and `setFlags` (SE: `uEffect::createGenerator`
family) live on the single DX9 class. Offsets differ throughout (4 vs 4SE); only the field set / method set
and the parent chain are shared. Do **not** borrow SE `uBaseEffect` *or* `uEffect` layout for DX9 offsets.

**Method-name correspondences now anchored by this mapping:**

| DX9 | SE | Notes |
|-----|----|----|
| `uEffectVFR::setEffectList` (0x9686E0) | `uBaseEffect::setEffectList` (0xCBA130) | near-identical body |
| `uEffectVFR::createGenerator` (0x96A770, ex-`sDevil4Effect::setFlags`) | `uEffect::createGenerator` family (0xCAFA90) | the EFL loader/builder; behavior-justified regardless of mapping |
| `sub_96AC10` (teardown) | `uEffect::releaseGenerator` | pre-store EffectArr teardown |
| `uEffectVFR::Generator::init` (0x9DECD0) | (part of) `allocGeneratorBuff`/`createParticleManager` | per-generator ctor + free-list |

**Two naming consequences:**
1. ✅ **APPLIED** — `setFlags` was filed under `sDevil4Effect::` but is a `this@<ecx>` thiscall + vtable
   virtual on `uEffectVFR`. Renamed to **`uEffectVFR::createGenerator`** (SE-anchored, behavior-matched,
   return-type-corroborated). Confirmed it's a real vtable slot (12 vtable data xrefs) called from
   `setEffectList` (eager) and `move` (lazy). See the deep-dive section above.
2. (HELD) `applyUnitParam` has **two** SE candidates (`uBaseEffect::applyUnitParam` 0xCB8A20 vs
   `uEffect::applyUnitParam` 0xCAF500). Since DX9 merged the subtree, both collapse into the DX9 class —
   so the DX9 applyUnitParam-equivalent (the `mUnitParamOffset → mpParamBuff[]` flag-bit hook) is **still
   to be located** by use; held.
