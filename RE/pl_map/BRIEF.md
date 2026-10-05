# Player (uPl*) DX9 → SE mapping — worker brief

Goal: give every **DX9 function in the player code range** its SE (leaked-PDB) identity. This
pass is **DX9-first**: the unit of work is each DX9 function in your address range. Do **not**
enumerate or record SE-only methods. SE has Vergil/Lady/Trish and other content DX9 lacks, so
those methods are irrelevant except as possible matches when code was moved or shared.

A previous identical-method pass over `uEm*` succeeded. Its lessons are baked in below; see
`RE/uem_se_dx9_map.md`.

## HARD RULES

1. **Never call `select_instance`.** Seven workers share one MCP proxy and the active instance is
   DX9 (13337). All SE data is pre-dumped. Anything only resolvable in SE stays `medium` or
   unmatched, with a note.
2. **Keep every IDA call short (< ~15 s).** Do bulk matching **offline** in local Python (Bash,
   `python`) against the JSON dumps. Use IDA only for spot verification (`decompile`, `disasm`,
   small `py_eval`) and for applying renames and comments in batches of ≤ 150.
3. **Only rename functions inside your assigned address range.** Data labels such as vtables and
   DTIs are allowed for classes whose vtable or ctor lives in your range.
4. Do not call `idb_save`. Never hand-convert number bases for reporting; use Python or `int_convert`.

## Inputs (scratchpad, read-only)

`S = C:\Users\Home\AppData\Local\Temp\claude\c--Tools-MCP-dev-test-re-test\44865d16-522b-4fef-aa4c-ace8a730064e\scratchpad`

| File | Content |
|------|---------|
| `S\dx9_pl_features.json` | DX9: `vtables{cls:{ea,slots}}`, `funcs{ea:feat}` for all 1668 functions in 0x7A0000–0x840000 |
| `S\se_pl_features.json` | SE: same schema for all 4666 SE `uPl*` methods (225 vtables) |

`feat = {name, size, nbb, ninsn, strs, callees[[ea,name]], callers[ea], gl[named globals], imms, flts, vt[[cls,slot]]}`.

- **Comparable names:** callee and global names can be compared across sides when the DX9 helper is already named.
- **DX9 player vtable tags may be wrong:** the `vt` tags in the DX9 dump come from current labels.
- **Out-of-range SE helpers aren't dumped:** SE helpers outside `uPl*` (cPlParam, kDamageParam, MtMath, uActor, …) are not in the SE dump. If a DX9 function in your range clearly is one of those, record `se_name: null`, `notes: "non-uPl helper: <evidence>"`.

Generator: `RE\scripts\uem_features.py` (config `S\features_cfg.json`). Also read `CLAUDE.md`, and `RE\player_instance_findings.md` if it covers your classes.

## Lessons from the uEm pass (apply them)

- **SE→DX9 vtable slots shift by a constant per base class.** For `uEnemy` derivatives, SE 21→DX9 12 (`kill`), SE 53→30 (`main`), SE 54→31 (`updatePtr`). Player classes derive from uActor too, so expect a similar fixed shift. Derive it once from anchor slots (dtor, createProperty, getDTI, setup, kill) and reuse it for every class.
- **Existing vtable labels are often wrong.** The old labelling script put `Class::vftable` on a nested or embedded class's vtable (15 cases in uEm). Verify each vtable in your range from the ctor's `mov [reg], offset vtbl` write or from the getDTI stub `B8 <DTI> C3`. Fix the label if needed; the true vtable usually sits just before the nested one. Example suspects: `uPlayerNeroBenchmark::vftable` is only 0x50 past `uPlayerNero`'s, and `uPlayer::vftable` (0xBE66EC) sits after `uPlayerNeroTutorial`'s.
- **Player DTIs were not emulated.** `mSizeAndPage` reads 0xFFFFFF and names are sometimes odd (`MtDTI_uPlayerDante`, `uActor::MtDTI`). Get the real size and parent from the registration call (`push size` / `mov edi, parent` / `mov eax, name` / `mov esi, dti` / `call MtDTI__MtDTI`).
- **ICF folding:** DX9 merged identical functions. One DX9 body can match several SE methods. Pick the name of the class that owns the address region, and add a comment listing the other SE aliases: `ICF-folded: one DX9 body for N SE methods: …`.
- **Callee-order propagation breaks on action tables.** When a class dispatches through a static function-pointer table, match by table index, setter constants and motion IDs instead. Verify by decompiling.
- **Destructors** are often undefined `loc_` code at vtable slot 0. Define them with `ida_funcs.add_func`, and name them with the SE mangled name (`??_G…`/`??1…`) because IDA turns `~` into `_`.

## Code moved between classes (player-specific)

SE hoisted some Dante/Nero code into `uPlayer` (shared with Vergil/Trish/Lady), and reuses Dante weapons and shells for Trish and Lady. Name a DX9 function **`<DX9 owning class>::<SE method name>`**.

- **Determining the owning class:** use the vtable it sits in, the address region it lives in, and its `this` type. Use the SE class only if it agrees with those.
- **Recording moved code:** if the SE class differs, say so in the comment, e.g. `SE: uPlayer::setDTMotion(void) @ 0x… (hoisted to uPlayer in SE)`.
- **Matching against SE-only classes:** matching against `uPlayerVergil/Trish/Lady/SE` methods is fine as evidence, e.g. Trish's Pandora is Dante's Pandora. Still name by the DX9 owner.

## Confidence and actions

- **`high`**: two or more independent signals agree (vtable alignment + callees/strings/constants; unique string set; propagation + order + size; decompile-verified), with no competing candidate. Rename it.
- **`medium`**: one signal, or two candidates. Add a comment only: `SE candidate: <sig> @ <SE ea> (medium: <evidence>)`.
- **`none`**: no SE identity found. Leave a short comment only if you learned something useful.

### Applying names in DX9

- **`high` renames:** `ida_name.set_name(ea, name, ida_name.SN_NOWARN | ida_name.SN_NOCHECK)`, plus a repeatable function comment `SE: <full demangled signature> @ <SE ea>`. On an overload name collision, append `_2`, `_3`, …
- **Existing non-auto names** (about 510 in this range, from earlier sessions):
  - If high confidence says otherwise, replace the name, keep the old one as `was: <old>` at the top of the comment, and set `action: "replaced_existing"`.
  - If the existing name already equals the SE name, only add the `SE:` comment (`action: "confirmed"`).
  - Keep any existing analysis comment text. Prepend yours; never overwrite.
- **Code:** wrap `py_eval` code in `def main(): ... ; main()`.

## Output

Write `C:\Tools\MCP_dev\test\re-test\RE\pl_map\<GROUP>.json`:

```json
{
  "group": "P1",
  "range": ["0x...", "0x..."],
  "classes": {
    "uPlayer": {"dx9": {"dti": "0x...", "vtable": "0x...", "ctor": "0x...", "size": "0x...", "parent": "..."},
                "se": {"vtable": "0x..."}, "slot_shift": "SE n → DX9 n-k (k=..)", "vtable_label_fixed": false}
  },
  "functions": [
    {"dx9_ea": "0x...", "old_dx9_name": "sub_...", "new_dx9_name": "uPlayer::setup",
     "se_ea": "0x...", "se_name": "uPlayer::setup(void)", "confidence": "high|medium|none",
     "evidence": ["vtable","callees","strings","consts","order","propagation","decompile","table"],
     "action": "renamed|replaced_existing|confirmed|commented|none", "notes": ""}
  ],
  "notes": "free-form: moved/hoisted code, DX9-only code, layout surprises"
}
```

**Every DX9 function in your range** must appear in `functions`.
Put helper scripts in `S\<GROUP>\`, not in the repo.
