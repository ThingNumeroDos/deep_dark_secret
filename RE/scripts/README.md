# RE/scripts

IDAPython analysis scripts for the DevilMayCry4_DX9 multiplayer / `sMediator` decoupling work.
Run them **inside the live IDA session** through the ida-pro-mcp `py_exec_file` tool — they use a
shared-globals scope. Do **not** paste them into `py_eval`: that tool splits globals/locals and
nested-function name lookups fail.

| Script | Purpose | Output |
|--------|---------|--------|
| `build_mpplayer_sites.py` | Enumerate every `sMediator::mpPlayer` (mpInstance+0x24) reference — inline reads + `getPlayerPos`/`getPlayerMat` call sites — and enrich each with owning class, `this`-register/CC, category, and instruction lengths. | `RE/mpplayer_call_sites.json` |

## Regenerating the call-site inventory

```
py_exec_file  RE/scripts/build_mpplayer_sites.py
```

Regenerate after **any** database change that defines, renames, or retypes functions — the JSON is
keyed to live instruction addresses and function prototypes and goes stale otherwise. The script is
idempotent and overwrites the JSON in place.

Expected output (baseline, DB as of 2026-07-09): **1047 sites** = 943 inline + 104 accessor;
categories camera 19 / damage-derivable 17 / nero-grab 14 / damage-review-aggro 5 / uncategorized 992;
`this_reg` = ecx 358, stack 268, eax 214, esi 114, edi 64, edx 13, ebx 3, null 13.

If the counts drift, that's real signal (new functions defined, or a category function was
re-typed) — reconcile against `RE/mpplayer_dispatcher_patch_plan.md` before trusting the delta.

## Notes / gotchas baked into the script

- `func_type_data_t` exposes the calling convention via `.get_cc()`, **not** a `.cc` attribute
  (IDA 9.3).
- `this` is **not** uniformly `ecx` — ~66% of sites pass it in eax/esi/edi/edx or on the stack.
  Resolved from the prototype, falling back to a Hex-Rays decompile for untyped functions.
- FP-return functions misreport arg0 as a `st0`/`xmm0` return slot; the script skips to the first
  GP-register (or stack) argument.
- The category EA sets (`CAMERA`, `NERO_GRAB`, `DAMAGE`, `DAMAGE_REVIEW`) are hardcoded from this
  session's analysis. Extend them there if new per-player/damage/grab handlers are identified.
