# uEm* classes: SE → DX9 method map

Date: 2026-10-05. This maps every `uEm*` class and method from the leaked-PDB Special Edition build onto the DX9 IDB. The work was split across 9 groups by enemy family; each group matched its classes and applied the names in DX9.

- **Full per-method data:** `RE/uem_map/uem_se_dx9_map.json`, with one row per SE method giving the SE address and signature, the DX9 address, confidence, evidence, and the action taken.
- **Per-group raw output:** `RE/uem_map/<A..I>.json`.
- **Worker brief:** `RE/uem_map/BRIEF.md`.
- **Scripts:** `RE/scripts/uem_features.py` dumps matching features from either IDB. `RE/scripts/uem_merge.py` merges the group files and checks consistency.
- **Rollback point:** `DevilMayCry4_DX9.exe.pre_uem_map.i64` is the DX9 database before any of these renames.

## Totals

| | Count |
|---|---|
| SE classes | 91 (90 with their own vtable) |
| SE methods | 6985 |
| **high**: renamed in DX9 to `Class::method`, with function comment `SE: <signature> @ <SE ea>` | 4126 |
| **medium**: comment only, `SE candidate: …` | 274 |
| **unmatched** | 2585 |
| DX9 functions renamed | ~3870 |
| Previously undefined code defined as functions (deleting dtors, `MyDTI::newInstance` stubs) | ~170 |

### Why 37% of SE methods are unmatched (expected, not missing work)

- **Allocator boilerplate:** SE has per-class `operator new` / `operator delete` / `usage` functions (about 98 in group A alone). DX9 has no counterpart.
- **Inlined setters:** most small `setX` action setters are compiled into their callers in DX9 (`setAction` switch bodies, etc.), so there is no separate function to match.
- **SE-only content:** Vergil/Trish/Lady support, `setDeltaTimeRate` virtuals, `uEm019_00::adjustChain` (24 KB), uEm036 path-finding, the Leaf/Snake/Hand/Pipe `damage*` handlers, and uEm027 `SyncAtkD`/`DmgBarrierC` actions.

The groups found almost no DX9 code without an SE counterpart. Inside the uEm code regions only a few dozen DX9 functions are left unmatched. Most are spawn helpers and small math helpers, and they are commented.

## Engine-wide findings

### SE → DX9 vtable slot map is uniform

The same offset applies to every `uEnemy`-derived class: SE slot *n* corresponds to a fixed DX9 slot.

| SE slot | DX9 slot | Method |
|---|---|---|
| 21 | 12 | `kill` |
| 53 | 30 | `main` |
| 54 | 31 | `updatePtr` |

SE's newer base classes add about 9 slots below slot 21 and about 23 slots below slot 53. DX9 adds a `setMotion` virtual that SE does not have: slot 110 in uEm005, slot 109 in uEm022, slot 103 in uEm017.

### `die` / `validateTargetPtrs` were misnamed in the base class

DX9 `uEnemy::die` (`0x72FB50`) is SE **`kill`**, and `uEnemy::validateTargetPtrs` (`0x72FAC0`) is SE **`updatePtr`**. This matches the earlier DX9 names `uPlayer::kill` and `uPlayer::updatePtr`. Both base functions and all 20 subclass overrides in slots 12 and 31 are now renamed, each with a `was:` comment. SE's real `die` is a separate per-class function; groups named it where it was found.

### ICF folding

DX9's linker merged identical functions into one copy (identical COMDAT folding, ICF). 90 DX9 functions are each claimed by more than one SE method:

- **86** have identical SE copies: same size, named callees and immediate constants.
- **4** are tiny stubs (`draw`, empty message handlers) whose SE copies differ by a few bytes.

Each of these functions keeps one name and carries a comment beginning `ICF-folded: one DX9 body for N SE methods:` that lists every alias. 85 comments were applied; the other 5 addresses are not defined as functions in IDA. **Consequence:** a DX9 function named `uEm010::setWalk` may also be `uEm008_009Base::setMoveR`. Check the comment before assuming the function is exclusive to one class.

### Vtable labels on nested-class vtables

The earlier labelling pass (`label_dti_vtables.py`) often put `Class::vftable` on the vtable of an embedded or nested class. Corrected labels:

| Class | Old label at | Real vtable | Old address was actually |
|---|---|---|---|
| uEm005 | 0xBCB888 | **0xBCB6A8** | uEm005Shield |
| uEm015 | 0xBD05F0 | **0xBD0448** | uEm015::uEm015LeftBody |
| uEm019_00 | 0xBD2710 | **0xBD2568** | uEm019_string |
| uEm019_lure | — | **0xBD2290** | |
| uEm019_string | — | **0xBD2710** | |
| uEm021 | — | **0xBD3360** | (was labelled uEm021_Hand) |
| uEm021_Hand | 0xBD3360 | **0xBD3A00** | uEm021 |
| uEm021_Leaf / _Pipe / _Snake | — | **0xBD3520 / 0xBD3860 / 0xBD36C0** | |
| uEm022 | 0xBD3EFC | **0xBD3F18** | cComboCtrl |
| uEm027 | 0xBD6760 | **0xBD65B8** | uEm027::uCamCtrl |
| uEm030GroundCtrl | 0xBD728C | **0xBD7150** | cGroundParam |
| uEm031 | 0xBD7BB0 | **0xBD79D8** | uEm031::cCmnd |
| uEmAngelo | 0xBD8B08 | **0xBD8950** | uEmAngeloWeapon (a real nested class with its own DTI; label kept on 0xBD8B08) |

uEm036's vtable label is cut off by an `off_BD88AC` label; the real vtable has 103 slots. The `vt` tags in the scratch feature dump were computed from the old labels and are wrong for these classes.

### Other structure

- **`cPopeCommon`** (DTI `0xE57350`, now named and typed): it inherits uEnemy, has size `0x28A0`, and is registered at `0xB6ECB0`. It is the parent of **uEm029 and uEm030**, which `enemy_classes.md` listed as "unknown". This DTI was missed by the Unicorn emulation pass, so its static fields are placeholders.
- `uEmRange` is embedded inside `uEm000Base`.
- `uEm012Dodge` and `uEm033Shl` have no standalone ctor in DX9; it is inlined into `MyDTI::newInstance` and its callers.
- uEm029, uEm030 and uEm033 dispatch actions through static function-pointer tables at `0xE15130`, `0xE15250` and `0xE153E4`. For these classes, matching by callee order gave wrong pairs, so the groups re-matched them by table index and setter constants and checked by decompiling.
- **Existing wrong names fixed** (old name kept as `was:` in the comment):
  - several `damageMessage_N` → `effectMessage` / `effectMeleeMessage` / `effectGuardMessage`
  - `damageMessage7` → `getNearTargetEnemy`
  - `uEm030::newInstance` → `getBusterTargetPos`
  - `uEm023::newInstance` (`0x7271C0`) → `uEmAngelo::setEffectFromMotSeq`
  - `uEmRange::uEmRange` → `init`
  - two `createProperty` names that really belong to nested classes

## Open items

| DX9 ea | Current name | SE says | Why left |
|---|---|---|---|
| 0x5498D0 | `uEm010::setRecoverHand` | also `uEm000Base::setTurn180` | ICF-folded; the alias is in the comment |
| 0x58C770 | `uEm010::setAttackIceMC` | also `uEm008_009Base::setJumpUp` | ICF-folded; the alias is in the comment |
| 0x718860 | `j_uEnemy::damageMessage5` | `uEm032::effectHighTimeMessage` | uEnemy-level name; out of uEm scope |

- **Destructor names:** destructors use mangled names (`??1Class@@…`, `??_G`, `??_E`) because IDA turns `~` into `_`. The rest of the IDB does not do this consistently.
- **Game-name column:** group E reports that uEm031 is Agnus, while `enemy_classes.md` lists it as Credo and uEm029 as Agnus. That column was never derived from code, so it is unverified.
- **Not covered:** methods of `uEnemy` itself, `cPopeCommon`, and other non-`uEm` helpers (`cEm*`, `kEm*`).

## Per-class results

SE vtable / DX9 vtable / DX9 ctor are addresses. In the method columns, H = high, M = medium, U = unmatched.

| Class | Grp | SE vtable | DX9 vtable | DX9 ctor | SE methods | H | M | U |
|---|---|---|---|---|---|---|---|---|
| uEm000 | A | 0x1165968 | 0xBC9D68 | 0x53F840 | 20 | 10 | 2 | 8 |
| uEm000Base | A | 0x1166A38 | 0xBCA278 | 0x540560 | 242 | 198 | 18 | 26 |
| uEm001 | A | 0x11670D0 | 0xBCA960 | 0x55E740 | 22 | 11 | 3 | 8 |
| uEm003 | A | 0x11678C8 | 0xBCAF30 | 0x55F810 | 20 | 11 | 1 | 8 |
| uEm003Shl | A | 0x1167F70 | 0xBCB3C0 | 0x560330 | 25 | 13 | 0 | 12 |
| uEm005 | B | 0x1168F08 | 0xBCB6A8 | 0x561A70 | 259 | 155 | 15 | 89 |
| uEm005GenkiShl | B | 0x1169400 | 0xBCB9E8 | 0x575300 | 30 | 20 | 0 | 10 |
| uEm006 | B | 0x116A068 | 0xBCC658 | 0x576C80 | 109 | 50 | 1 | 58 |
| uEm006Coop | B | 0x116A420 | 0xBCC848 | 0x57D140 | 36 | 9 | 0 | 27 |
| uEm008 | A | 0x116A670 | 0xBCCC58 | 0x57F210 | 28 | 19 | 1 | 8 |
| uEm008_009Base | A | 0x116B410 | 0xBCD0A8 | 0x581320 | 217 | 168 | 21 | 28 |
| uEm009 | A | 0x116BA70 | 0xBCD9B0 | 0x595840 | 58 | 43 | 7 | 8 |
| uEm009Shl | A | 0x116C450 | 0xBCDE60 | 0x59BC30 | 77 | 37 | 3 | 37 |
| uEm010 | C | 0x116C880 | 0xBCE0D0 | 0x5A3F90 | 174 | 152 | 4 | 18 |
| uEm010CrawShl | C | 0x116CC78 | 0xBCE2A8 | 0x5AEB30 | 32 | 19 | 0 | 13 |
| uEm010Ice | C | 0x116CE80 | 0xBCE490 | 0x5B0100 | 29 | 18 | 2 | 9 |
| uEm010ShlCtrl | C | 0x116D1C8 | 0xBCE648 | — | 25 | 6 | 0 | 19 |
| uEm010Warp | C | 0x116D3F8 | 0xBCE790 | — | 24 | 9 | 0 | 15 |
| uEm011 | D | 0x116DD98 | 0xBCEA90 | 0x5B31A0 | 254 | 163 | 1 | 90 |
| uEm011Shl | D | 0x116E280 | 0xBCEC58 | 0x5CEC20 | 28 | 15 | 0 | 13 |
| uEm011Test | D | 0x116E4C8 | 0xBCEDF0 | 0x5CFB40 | 49 | 23 | 3 | 23 |
| uEm012 | D | 0x116E7B8 | 0xBCF060 | 0x5D1790 | 216 | 161 | 7 | 48 |
| uEm012Dodge | D | 0x116EAD0 | 0xBCF210 | inlined (0x5DA280 / 0x5DACD0) | 23 | 8 | 0 | 15 |
| uEm012Shl | D | 0x116ED18 | 0xBCF370 | 0x5DB250 | 32 | 18 | 0 | 14 |
| uEm013 | C | 0x116F310 | 0xBCF660 | 0x5DC190 | 129 | 87 | 3 | 39 |
| uEm013SeedJimen | C | 0x116F760 | 0xBCF838 | — | 15 | 3 | 0 | 12 |
| uEm013SeedShell | C | 0x116F938 | 0xBCF978 | 0x5EC920 | 32 | 16 | 0 | 16 |
| uEm014 | D | 0x116FC90 | 0xBCFC50 | 0x5EF780 | 70 | 37 | 2 | 31 |
| uEm015 (+LeftBody) | E | 0x1170738 | 0xBD0448 | 0x5F3CB0 | 297 | 217 | 7 | 73 |
| uEm015Ctrl | E | 0x11710D0 | 0xBD0788 | 0x609C50 | 35 | 18 | 0 | 17 |
| uEm016 | E | 0x1171838 | 0xBD0B68 | 0x60AFF0 | 216 | 156 | 2 | 58 |
| uEm016Ctrl | E | 0x1171CE8 | 0xBD0E88 | — | 72 | 40 | 0 | 32 |
| uEm017 | F | 0x1172728 | 0xBD11B0 | 0x61A7E0 | 207 | 103 | 37 | 67 |
| uEm017HeadShl | F | 0x1172B50 | 0xBD1380 | 0x62D4E0 | 38 | 20 | 3 | 15 |
| uEm018 | F | 0x1172DC0 | 0xBD1730 | 0x630AF0 | 224 | 120 | 19 | 85 |
| uEm018BreakHouse | F | 0x1173448 | 0xBD1BE0 | 0x644E30 | 46 | 19 | 2 | 25 |
| uEm018FireShl | F | 0x1173988 | 0xBD1D48 | 0x649220 | 28 | 12 | 1 | 15 |
| uEm019 | G | 0x1173E38 | 0xBD20F0 | 0x649D10 | 208 | 154 | 0 | 54 |
| uEm019ShlLand | G | 0x11756E0 | 0xBD2E30 | 0x684690 | 20 | 7 | 0 | 13 |
| uEm019_00 | G | 0x11745B8 | 0xBD2568 | 0x66C110 | 164 | 103 | 1 | 60 |
| uEm019_00Shl | G | 0x1174DF8 | 0xBD2868 | 0x67D030 | 27 | 13 | 0 | 14 |
| uEm019_00_Yoke | G | 0x1175040 | 0xBD29C0 | 0x67ECC0 | 20 | 8 | 0 | 12 |
| uEm019_hair | G | 0x1175248 | 0xBD2B90 | 0x67FA30 | 30 | 18 | 0 | 12 |
| uEm019_ice | G | 0x11754D0 | 0xBD2CD8 | 0x6809E0 | 26 | 11 | 0 | 15 |
| uEm019_lure | G | 0x1173C68 | 0xBD2290 | 0x668E40 | 29 | 12 | 0 | 17 |
| uEm019_string | G | 0x11743F0 | 0xBD2710 | 0x66B9D0 | 24 | 8 | 0 | 16 |
| uEm021 | H | 0x1176970 | 0xBD3360 | 0x685430 | 234 | 155 | 4 | 75 |
| uEm021Shell | H | 0x1177258 | 0xBD3C30 | 0x6A55E0 | 44 | 27 | 3 | 14 |
| uEm021_Hand | H | 0x1176728 | 0xBD3A00 | 0x6A0A70 | 85 | 40 | 1 | 44 |
| uEm021_Leaf | H | 0x11762A8 | 0xBD3520 | 0x69A7D0 | 152 | 53 | 1 | 98 |
| uEm021_Pipe | H | 0x1176EA8 | 0xBD3860 | 0x6A30C0 | 66 | 36 | 1 | 29 |
| uEm021_Snake | H | 0x11764E8 | 0xBD36C0 | 0x69E4B0 | 100 | 49 | 0 | 51 |
| uEm022 | B | 0x1177D00 | 0xBD3F18 | 0x6AA320 | 217 | 131 | 9 | 77 |
| uEm022EngelShl | B | 0x11780B0 | 0xBD4100 | 0x6B7100 | 17 | 8 | 0 | 9 |
| uEm022JavelinShl | B | 0x11782C8 | 0xBD4270 | 0x6B7470 | 32 | 22 | 0 | 10 |
| uEm022SpearShl | B | 0x1178770 | 0xBD43C0 | 0x6BB4E0 | 31 | 23 | 0 | 8 |
| uEm023 | C | 0x1179028 | 0xBD4630 | 0x6BDE90 | 178 | 101 | 3 | 74 |
| uEm023Shl | C | 0x1179408 | 0xBD47F8 | 0x6D3220 | 25 | 12 | 1 | 12 |
| uEm023ShlCutlass | C | 0x1179648 | 0xBD4998 | 0x6D4700 | 34 | 17 | 2 | 15 |
| uEm023ShlGladius | C | 0x11798A8 | 0xBD4B00 | 0x6D6C60 | 30 | 12 | 2 | 16 |
| uEm025 | I | 0x117A1A0 | 0xBD4D58 | 0x6D87D0 | 265 | 145 | 3 | 117 |
| uEm025Core | I | 0x117A558 | 0xBD4F20 | 0x6E8860 | 20 | 9 | 0 | 11 |
| uEm025Shl00 | I | 0x117A7E8 | 0xBD50E8 | 0x6EACE0 | 20 | 9 | 0 | 11 |
| uEm025Shl01 | I | 0x117AA08 | 0xBD5230 | 0x6EBE40 | 23 | 13 | 0 | 10 |
| uEm025Shl01_2_Ctrl | I | 0x117AC08 | 0xBD5380 | 0x6ED6C0 | 19 | 7 | 0 | 12 |
| uEm025Shl02 | I | 0x117AE10 | 0xBD54C8 | 0x6EDE20 | 18 | 7 | 0 | 11 |
| uEm025Shl02Ctrl | I | 0x117B010 | 0xBD5618 | — | 19 | 6 | 1 | 12 |
| uEm025Shl03 | I | 0x117B220 | 0xBD5760 | 0x6EED00 | 20 | 9 | 0 | 11 |
| uEm025Shl04 | I | 0x117B428 | 0xBD58A8 | 0x6EFCF0 | 20 | 9 | 0 | 11 |
| uEm026 | F | 0x117BDA0 | 0xBD61E8 | 0x6F1080 | 75 | 26 | 22 | 27 |
| uEm027 | F | 0x117C200 | 0xBD65B8 | 0x6F3DB0 | 106 | 55 | 8 | 43 |
| uEm029 | I | 0x117C6D8 | 0xBD6AC8 | 0x6F8210 | 140 | 109 | 4 | 27 |
| uEm030 | I | 0x117CD08 | 0xBD6F50 | 0x702320 | 161 | 116 | 3 | 42 |
| uEm030GroundCtrl | I | 0x117D298 | 0xBD7150 | 0x70D550 | 32 | 9 | 1 | 22 |
| uEm030GroundParts | I | 0x117D4E0 | 0xBD72E8 | — | 23 | 8 | 0 | 15 |
| uEm030Shl | I | 0x117D738 | 0xBD7458 | 0x70DC80 | 32 | 20 | 1 | 11 |
| uEm030Spada | I | 0x117D968 | 0xBD75E8 | 0x70F2F0 | 35 | 25 | 1 | 9 |
| uEm031 | E | 0x117DCF0 | 0xBD79D8 | 0x710270 | 107 | 63 | 0 | 44 |
| uEm032 | H | 0x117E200 | 0xBD7C30 | 0x713BA0 | 83 | 44 | 6 | 33 |
| uEm032BitCtrl | H | 0x117E4D8 | 0xBD7E20 | 0x7188D0 | 26 | 11 | 0 | 15 |
| uEm033 | G | 0x117E758 | 0xBD7FC0 | 0x719170 | 47 | 25 | 0 | 22 |
| uEm033Shl | G | 0x117EA68 | 0xBD8188 | inlined in newInstance | 23 | 11 | 0 | 12 |
| uEm035 | G | 0x117ECF8 | 0xBD83D8 | 0x71B2F0 | 72 | 44 | 5 | 23 |
| uEm036 | D | 0x117F210 | 0xBD8780 | 0x723C30 | 107 | 40 | 2 | 65 |
| uEmAngelo | B | 0x117F8E8 | 0xBD8950 | 0x726D20 | 65 | 30 | 2 | 33 |
| uEmAppear | A | 0x117FBB8 | 0xBD8C50 | 0x7282F0 | 32 | 12 | 5 | 15 |
| uEmBombShl | A | 0x117FC60 | 0xBD8CC0 | 0x728B10 | 24 | 9 | 0 | 15 |
| uEmPushShl | A | 0x117FE78 | 0xBD8E40 | 0x729090 | 20 | 8 | 0 | 12 |
| uEmRange | A | 0x11800B0 | 0xBD8FC0 | — (embedded in uEm000Base) | 24 | 8 | 0 | 16 |
| uEmSample | A | 0x1180278 | 0xBD9030 | 0x72B330 | 96 | 35 | 17 | 44 |
