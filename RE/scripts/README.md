# RE/scripts

IDAPython analysis scripts for the DevilMayCry4_DX9 multiplayer / `sMediator` decoupling work.
Run them **inside the live IDA session** through the ida-pro-mcp `py_exec_file` tool — they use a
shared-globals scope. Do **not** paste them into `py_eval`: that tool splits globals/locals and
nested-function name lookups fail.

| Script | Purpose | Output |
|--------|---------|--------|
| `uem_features.py` | Dump per-function matching features (strings, callees, constants, vtable slots) for a class family from either IDB; config `features_cfg.json` in the scratchpad (`prefix`, `tag`, optional DX9 `span`). Used for the SE→DX9 name passes. | `se_<tag>_features.json`, `dx9_<tag>_features.json` |
| `uem_merge.py` / `pl_merge.py` | Merge the per-group SE→DX9 mapping JSONs and check coverage and duplicate claims. Plain Python (`python RE/scripts/...`), not IDA. | `RE/uem_map/uem_se_dx9_map.json`, `RE/pl_map/pl_dx9_se_map.json` |
| `build_mpplayer_sites.py` | Enumerate every `sMediator::mpPlayer` (mpInstance+0x24) reference — inline reads + `getPlayerPos`/`getPlayerMat` call sites — and enrich each with owning class, `this`-register/CC, category, and instruction lengths. | `RE/mpplayer_call_sites.json` |

## Regenerating the call-site inventory

```
py_exec_file  RE/scripts/build_mpplayer_sites.py
```

Regenerate after **any** database change that defines, renames, or retypes functions — the JSON is
keyed to live instruction addresses and function prototypes and goes stale otherwise. The script is
idempotent and overwrites the JSON in place.

Expected output (baseline, DB as of 2026-10-05, after the uEm + player SE-name passes): **1048 sites** = 944 inline + 104 accessor;
categories camera 19 / damage-derivable 17 / nero-grab 14 / damage-review-aggro 5 / uncategorized 993;
`this_reg` = ecx 366, stack 247, eax 223, esi 115, edi 67, edx 13, ebx 3, null 14.
Sites with no owning class: 245 (was 716 before the SE-name passes). Previous baseline (2026-07-09): 1047 sites; the +1 is
`uPlayerDanteBoss::checkPlayerDeadThink` (0x7C6470), formerly undefined code.

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
