# uEm SE → DX9 mapping — worker brief

Goal: map every **SE (leaked-PDB) `uEm*` class and method** to its counterpart in the **DX9** IDB,
apply confirmed names in DX9, and record the full mapping (including non-matches) as JSON.

## HARD RULES (read twice)

1. **Never call `select_instance`.** Nine workers share one MCP proxy; switching instance redirects
   *everyone's* calls into the SE database. The active instance is DX9 (port 13337) and must stay so.
   All SE information you need is in the pre-dumped JSON below. If something is only resolvable in
   SE, leave it `medium`/unmatched and say so in `notes`.
2. **Keep every IDA call short (< ~15 s).** IDA serialises requests from all workers; a long
   `py_eval` stalls the other eight and the proxy times out. Do all bulk matching **offline** in local
   Python (Bash tool, `python`) against the JSON dumps. Use IDA only for spot verification
   (`decompile`, `disasm`, small `py_eval`) and for applying renames/comments in batches of ≤ 150.
3. **Only rename DX9 functions to names whose class prefix is in your group.** Shared/inherited
   code (`uEnemy::*`, `uActor::*`, `cUtil::*`, another group's `uEm*` class) — record it, don't rename it.
4. Do not touch functions outside the DX9 uEm span `0x54B280–0x72B7E0` except vtable labels/ctors of
   your own classes.
5. Never convert number bases in your head for anything you report — use `int_convert` or Python.

## Inputs (scratchpad, read-only)

`S = C:\Users\Home\AppData\Local\Temp\claude\c--Tools-MCP-dev-test-re-test\44865d16-522b-4fef-aa4c-ace8a730064e\scratchpad`

| File | Content |
|------|---------|
| `S\se_uem_features.json` | SE: `vtables{cls:{ea,slots[[i,ea,name]]}}`, `funcs{ea:feat}` for all 6985 uEm methods |
| `S\dx9_uem_features.json` | DX9: same schema, all 4058 functions in the uEm span (mostly `sub_*`) |
| `S\se_uem_raw.json` | SE per-class: funcs (with mangled names → full signatures), DTI addr |
| `S\dx9_uem_state.json` | DX9 per-class: DTI addr, vtable label, already-named funcs |

`feat = {name, size, nbb, ninsn, strs, callees[[ea,name]], callers[ea], gl[named globals], imms, flts, vt[[cls,slot]]}`.
Callee/global **names** are comparable across sides when the DX9 helper is already named
(`cUtil::*`, `uEnemy::*`, `sMediator::mpInstance`, MtMath, etc.). Generator: `RE\scripts\uem_features.py`.
Also read `RE\enemy_classes.md` (DX9 DTI roster + uEnemy vtable) and `CLAUDE.md` (engine conventions).

## Known structural facts

- SE is a **newer engine**: base-class vtables are much longer (SE uEm000Base 323 slots vs DX9 uEnemy 84),
  so **absolute slot numbers do not correspond**. Align the *relative order of class-owned overrides*.
- SE added content (Vergil/Lady/Trish, `mGrapTrish`, Vergil trick timers, etc.) — some SE methods have
  **no DX9 counterpart**. Inlining also differs. Unmatched is a valid, expected outcome.
- MSVC keeps per-TU function order; DX9 class code is contiguous per class and order tends to follow SE.
- DX9 DTI globals are at `0xE58xxx`; SE's are at `0x1492xxx` (`enemy_classes.md` wrongly says they're equal).
- DX9 vtables missing / wrong: `uEm019_lure`, `uEm019_string`, `uEm021`, `uEm021_Leaf`, `uEm021_Pipe`,
  `uEm021_Snake` have no vtable label; `uEmAngelo`'s vtable is labelled `uEmAngeloWeapon::vftable` (0xBD8B08) —
  check whether that's a real separate class or a mislabel. Find vtables via the ctor's `mov [reg], offset vtbl`
  or the getDTI stub (`B8 <DTI> C3`) referenced from data.

## Suggested pipeline

1. **Class anchors** per class: DTI, getDTI stub, vtable, ctor (writes vtable), scalar-deleting dtor,
   `createProperty` (property-name strings are near-unique), `createUI`, `setup`.
2. **Vtable alignment**: for each class, take the slots whose SE function is owned by that class and the
   slots whose DX9 function lies in that class's code region; align the two ordered sequences (DP/LCS)
   scored by size/nbb ratio, named callees, strings, floats.
3. **String anchors**: unique string sets (Jaccard) pair functions directly.
4. **Callgraph propagation**: for each matched pair, align their callee lists in order; positionally
   corresponding unmatched callees with compatible size become candidates; iterate to fixpoint. Same for callers.
5. **TU-order fill**: between two consecutive anchored matches, align the unmatched SE run against the
   unmatched DX9 run by order + size/nbb similarity.
6. **Verify**: decompile a sample of every evidence type (especially order-fill and propagation-only),
   and every match where size ratio is outside 0.5–2.0. Demote anything that doesn't hold up.

## Confidence

- `high` — ≥ 2 independent signals agree (e.g. vtable alignment + callees/strings; unique string set;
  propagation + order + size), **no competing candidate**, or decompile-verified. → rename.
- `medium` — one signal, or two candidates. → comment only, no rename.
- `none` — unmatched (record SE-only / DX9-only).

## Applying in DX9

- `high`: rename to `Class::method` (strip the arg list; IDA allows `::`). On a name collision (overloads),
  append `_2`, `_3`, … Set a **function comment** (repeatable): `SE: <full demangled signature> @ <SE ea>`.
- Existing non-auto DX9 name that differs: if it's a lowercase_underscore placeholder or clearly wrong →
  replace and keep the old name in the comment (`was: <old>`); if it looks like a deliberate real name →
  don't rename, record a `conflict`.
- `medium`: function comment only: `SE candidate: <sig> @ <SE ea> (medium: <evidence>)`.
- Label missing vtables for your classes as `Class::vftable`.
- Use `ida_name.set_name(ea, name, ida_name.SN_NOWARN | ida_name.SN_NOCHECK)` and `idc.set_func_cmt(ea, c, 1)`
  inside a short `py_eval` (wrap code in `def main(): ... ; main()`).
- Do **not** call `idb_save` — the coordinator saves once at the end.

## Output

Write `C:\Tools\MCP_dev\test\re-test\RE\uem_map\<GROUP>.json`:

```json
{
  "group": "A",
  "classes": {
    "uEm010": {
      "se": {"dti": "0x...", "vtable": "0x...", "nslots": 0, "nfuncs": 0},
      "dx9": {"dti": "0x...", "vtable": "0x...", "ctor": "0x...", "nslots": 0, "code_range": ["0x...", "0x..."]},
      "slot_map": [[se_slot, dx9_slot, "method"], ...]
    }
  },
  "methods": [
    {"se_ea": "0x...", "se_name": "uEm010::setup(void)", "dx9_ea": "0x...", "confidence": "high",
     "evidence": ["vtable", "callees", "strings", "order", "propagation", "decompile"], "action": "renamed|commented|conflict|none",
     "old_dx9_name": "sub_...", "notes": ""}
  ],
  "se_only": ["0x..."], "dx9_only": ["0x..."],
  "notes": "free-form observations: missing features, inheritance surprises, layout differences"
}
```

Every SE function of your classes must appear in `methods` (with `dx9_ea: null` if unmatched).
Put helper scripts in `S\<GROUP>\` — not in the repo.
