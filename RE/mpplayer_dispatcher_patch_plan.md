# Mass-Patch Plan: Redirect mpPlayer Resolution → Dispatcher

**Status:** DESIGN ONLY — nothing patched yet. The dispatcher itself (signature, index
selection, per-player table) is TBD; this document defines *how* to redirect existing sites to it
once it exists.

## The problem we're patching

Every player-resolution site ultimately executes the idiom:

```asm
mov rX, [sMediator::mpInstance]   ; load singleton  (rX ∈ {eax,ecx,edx,ebx,esi,edi,ebp})
mov rY, [rX+24h]                  ; rY = mpPlayer    (or cmp [rX+24h],0 for a null-check)
```

Measured against the live DB (2026-06-29):

| Route | Sites | Funcs | Shape |
|-------|-------|-------|-------|
| Inline `[mpInstance]`→`[+24h]` | **942** | 707 | 8 load-reg forms × dozens of deref-reg forms; insns up to 6 apart |
| Accessor `getPlayerPos` (`0x493240`) | 59 | 35 | uniform `call` |
| Accessor `getPlayerMat` (`0x493350`) | 45 | 24 | uniform `call` |
| **Distinct player-touching funcs** | — | **724** | |

The inline reads are the hard part: **there is no single byte signature** to find-and-replace.
The load register varies (eax 518, ecx 208, edx 128, edi 37, esi 25, ebx 20, ebp 5) and the
`+0x24` deref appears in 40+ register-pair combinations plus `cmp` null-check forms. So a literal
"NOP these N bytes and write a call" sweep across 942 sites is not viable — each site is a
different instruction pair at a different length.

## Key insight: patch the field, not the 942 sites

All 942 inline sites and both accessors funnel through **one** memory access: `[mpInstance + 0x24]`.
That offset is the choke point. Three mechanisms can intercept it, in increasing order of how much
code we touch:

### Option 1 — Repoint the two accessors only (104 sites, 2 patches) — *partial*

`getPlayerPos`/`getPlayerMat` both begin `mov ecx,[ecx+24h]`. Replace each function's prologue with
a `jmp dispatcher_pos` / `jmp dispatcher_mat`. **2 patches** cover **104 call sites / 59 functions**.

- ✅ Trivial, reversible, no call-site edits.
- ❌ Covers only the 13% of sites that use accessors. The 942 inline reads are untouched.
- **Use as:** the first, safe slice — and a template for the dispatcher's pos/mat ABI.

### Option 2 — Trampoline the accessors + convert inline sites to accessor calls — *full, invasive*

For every inline site, overwrite the `mov rX,[mpInstance]; mov rY,[rX+24h]` pair with a
`call get_player_into_rY` thunk. **Rejected as the primary plan:**

- The two instructions are not always adjacent (≤6 apart) — can't assume a contiguous patch window.
- Variable total length (7–12 bytes) per site; many are too short to hold a 5-byte `call` + the
  register-move semantics without a per-site trampoline.
- 942 bespoke trampolines = enormous surface, high regression risk, hard to audit.
- Only justifiable for sites the dispatcher must treat specially (e.g. the Nero-grab handlers).

### Option 3 — **Recommended: relocate `mpPlayer` behind the dispatcher via the field load** 

Keep the existing idiom intact and make `[mpInstance+0x24]` *itself* resolve through the
dispatcher. Two ways to do that, pick per how much we control the singleton:

**3a — Hook the writer, keep field as a cache.** Only **one** site writes a live `mpPlayer`:
`uPlayer::registerWithMediator` (`0x7A91C0`) does `mpInstance->mpPlayer = this`. If the dispatcher
owns player selection, redirect that single write (and the teardown `mov [edx+24h],0` in the spawn
state machine) so `+0x24` always holds "the player the dispatcher currently considers active for
this context." Every inline read then transparently gets the dispatcher's choice **with zero
read-site patches**. 
- ✅ Smallest patch set (1 writer + 1 teardown).
- ❌ Only works if "active player" is a *global* notion per frame — it is **not** for true
  splitscreen (camera A wants player 0 while camera B wants player 1 in the same frame). Good
  enough for "swap which single player everything sees" but not concurrent multi-view.

**3b — Trap the field via a guard page / indirection slot.** Make `+0x24` a pointer the dispatcher
updates per-consumer, or relocate the singleton so `+0x24` lands on an intercepted address. Heavy;
only if 3a's global-active-player model is insufficient and we still want to avoid read-site edits.

## Recommended layered plan (build order)

1. **Accessors first (Option 1).** Patch `getPlayerPos`/`getPlayerMat` prologues to
   `jmp` the dispatcher's pos/mat entry. Defines the dispatcher ABI on the simplest 104 sites and is
   independently testable (camera + enemy-grab matrix math run through these).
2. **Writer redirect (Option 3a).** Redirect the single `mpPlayer` write in
   `registerWithMediator` + the teardown zero-write. This makes all 942 inline reads follow the
   dispatcher's global active-player choice for free. Validates the "swap active player" path.
3. **Targeted inline conversions (Option 2, surgical).** ONLY for sites that must diverge from the
   global active player in the same frame — primarily the **per-player camera** cluster (15 fns) and
   the **Nero-grab handlers** (10 fns) which need a *specific* index/downcast, not "active player."
   For these, convert the inline idiom to a `call dispatcher_get(index)` via per-site trampolines.

This means the **bulk** (account for >900 sites) is handled by 2+2 patches (steps 1–2); only the
~25 context-sensitive functions identified this session need individual trampolines (step 3).

## Mechanism details for the jump-to-dispatcher

- **x86, 32-bit, imagebase 0x400000.** A near `jmp rel32` / `call rel32` is 5 bytes
  (E9/E8 + rel32). The dispatcher must live where rel32 from each patch site can reach it (the whole
  .text fits in ±2GB, so any code-cave or appended section works).
- **Accessor patch (step 1):** overwrite byte 0 of `getPlayerPos`/`getPlayerMat`. `getPlayerPos`
  starts at `0x493240` with `mov ecx,[ecx+24h]` (3 bytes) — write `E9 <rel32>` (5 bytes), which
  spills 2 bytes into `test ecx,ecx`; fine, we never return into it. Dispatcher replicates the
  null-guard + the `result@<eax>`/`this@<ecx>` __usercall ABI and the field reads (+0x30 pos / +0x60
  mat) for the chosen player, then `retn`.
- **Code cave:** prefer appending a new section (e.g. `.disp`) over scavenging alignment padding —
  942-site coverage will need real space for the dispatcher + per-site trampolines. A new PE section
  avoids cave-size limits and keeps the patch auditable.
- **Index source for step 3 trampolines:** the dispatcher needs to know *which* player a site wants.
  Candidates already available at those sites: camera owner index (give each `cCameraPlayer`/
  `uDevilCamera` a `mPlayerIndex`), and for Nero-grab the existing `strcmp "uPlayerNero"` /
  `vtbl[134]` test becomes "ask dispatcher for the Nero-slot player, null if none." TBD with the
  dispatcher design.

## Reversibility / safety

- Save original bytes of every patched site to `RE/patch_backups/` (addr → original bytes) before
  any write, so the whole set can be rolled back.
- Steps are independent and each is testable in isolation (1 → accessors, 2 → active-player swap,
  3 → per-view divergence). Do not proceed to a later step until the prior one is verified in-game.
- `idb_save` after each step; keep the patch list in this file updated with applied/not-applied.

## Site inventories (already enumerated this session)

- Inline reader functions (707) and 942 sites: regenerated on demand from the live scan
  (`scratchpad/cam_scan.py` pattern). 
- Accessor call sites: `getPlayerPos` 59, `getPlayerMat` 45.
- Camera cluster needing step-3 treatment: 15 fns — see *Camera Subsystem* section of
  `player_instance_findings.md`.
- Nero-grab handlers needing step-3 treatment: 10 fns — see *Enemy Grab-Interaction Tables* section.
- Cached-member writers (set once in `init()`): 14 classes — see *Cached mpPlayer Members*; these
  are a separate hazard (stale pointer) and are fixed at the writer, like step 2, not the readers.
