# Player (uPl*) classes — DX9 → SE map

Date: 2026-10-05. This pass started from **DX9**: every function in the DX9 player code range
`0x79F000–0x840000` was given its SE (leaked-PDB) identity. SE-only content (Vergil, Lady, Trish,
`uPlayerSE`, shader debug, …) is out of scope and not recorded. Seven workers (P1–P7) each owned
one address range.

- **Data:** `RE/pl_map/pl_dx9_se_map.json`, one row per DX9 function: `dx9_ea`, old and new name, `se_ea`/`se_name`, confidence, evidence and action. Per-worker files are `RE/pl_map/P1..P7.json`.
- **Brief:** `RE/pl_map/BRIEF.md`.
- **Scripts:** `RE/scripts/uem_features.py` (feature dump, now configurable through `features_cfg.json`) and `RE/scripts/pl_merge.py` (merge and checks).
- **Rollback:** `DevilMayCry4_DX9.exe.pre_pl_map.i64` is the IDB before this pass (after the uEm pass).
- **Companion:** `uem_se_dx9_map.md` (enemies).

## Totals

| | Count |
|---|---|
| DX9 functions covered | 1795 (1668 pre-existing + ~110 undefined stubs newly defined + 4 switch-case fragments merged back) |
| **high** | 1656 |
| medium (comment only) | 22 |
| none | 117 |
| renamed (was `sub_*`) | 1146 |
| replaced an existing hand-given name (`was:` kept in comment) | 99 |
| existing name confirmed by SE | 411 |

The 117 `none` are almost all **non-player code inside the padded range**: PC UI (`uPause*`,
`uPc*`) below `0x7A4640`, and `uPopeHitCheck` / `uPowerUp*` above `0x83EE20`. Only about 15 actual
player functions lack an SE identity.

The merge check found no DX9 function claimed by two workers. All other functions are covered; the
one missing address is `0x840000`, which lies outside the range (uPowerUp).

## Class table (DX9)

Sizes and parents come from each class's `MtDTI::MtDTI` registration call. The player DTIs were
**not** covered by the Unicorn emulation pass, so their static `mSizeAndPage` reads `0xFFFFFF`.
"inl" means DX9 has no standalone ctor; it is inlined into `create` / `MyDTI::newInstance`.

| Class | DTI | Vtable | Ctor | Size | Parent |
|---|---|---|---|---|---|
| uPlayer | 0xE5A360 | **0xBE30E0** (181 slots) | 0x7A5B30 | 0x3270 | uActor |
| uPlayerDante | 0xE5A3E0 | 0xBE3C50 | 0x7B2150 | 0x152F0 | uPlayer |
| uPlayerDanteBenchmark | 0xE5A400 | 0xBE3FE8 | 0x7BF730 | 0x15340 | uPlayerDante |
| uPlayerDanteBoss | 0xE5A420 | 0xBE4440 | 0x7BF9B0 | 0x16340 | uPlayerDante |
| uPlayerDanteBossMeleeCancel | 0xE5A440 | 0xBE4818 | 0x7C8D00 | 0x1C80 | uActor |
| uPlayerNero | 0xE5A4A0 | 0xBE4FA0 | 0x7E1B30 | 0xD680 | uPlayer |
| uPlayerNeroBenchmark | 0xE5A4C0 | 0xBE52D8 | 0x7EAEF0 | 0xD6D0 | uPlayerNero |
| uPlayerNeroTutorial | 0xE5A4E0 | 0xBE6260 | 0x8022C0 | 0xD690 | uPlayerNero |
| uPlNeroDevil | 0xE5AA90 | 0xBE8B70 | 0x827E50 | 0x2460 | uActor |
| uPlNeroDevilFlicker | 0xE5AAB0 | 0xBE8CE0 | inl 0x82B920 | 0x1380 | uActor |
| uPlGrabShortHit | 0xE5AA70 | 0xBE8898 | 0x8202E0 | 0x1860 | uActor |
| uPlOwnHit | 0xE5AB50 | 0xBE9438 | 0x82F870 | 0x1800 | uActor |
| uPlacement | 0xE5A280 | 0xBE28AC | 0x7A46B0 / 0x7A4750 | 0x20 | cUnit |
| uPlSwordBlur | 0xE5AB90 | 0xBE9760 | 0x8310F0 / 0x831160 | 0x7C | cUnit |
| uPlWeapon | 0xE5ABB0 | 0xBE97B0 | 0x831B50 | 0x13A0 | uActor |
| uPlWpRightHand (Devil Bringer) | 0xE5AD30 | 0xBEAB48 | 0x83B0E0 | 0x3560 | uPlWeapon |
| uPlWpRightHand::uCollisionCtrl | 0xE5ACF0 | **0xBEACC0** | 0x83D580 | 0x1B80 | uActor |
| uPlWpRightHand::uEffectCtrl | 0xE5AD10 | 0xBEACA4 | inl 0x83B090 | 0xC | MtObject |
| uPlWpLucifer | 0xE5AC50 | 0xBEA128 | 0x833A30 | 0x2E00 | uPlWeapon |
| uPlWpYamatoDante | 0xE5AD70 | 0xBEAFE0 | 0x83E850 | 0x2270 | uPlWeapon |
| uPlWpPandora | 0xE5AC70 | 0xBEA508 | 0x836300 | 0x1840 | uPlWeapon |
| uPlWpRevellion | 0xE5ACD0 | 0xBEA898 | 0x838EA0 | 0x17E0 | uPlWeapon |
| uPlWpGilgamesh | 0xE5AC30 | 0xBE9EF0 | 0x832D30 | 0x1650 | uPlWeapon |
| uPlWpEbonyIvory | 0xE5AC10 | 0xBE9CF0 | 0x832390 | 0x13B0 | uPlWeapon |
| uPlWpBlueRose / CoyoteAce / RedQueen / Yamato | 0xE5ABD0 / 0xE5ABF0 / 0xE5AC90 / 0xE5AD50 | 0xBE9958 / 0xBE9B08 / 0xBEA6C8 / 0xBEAE30 | inl | 0x13A0 / 0x13B0 / 0x13B0 / 0x13B0 | uPlWeapon |
| uPlWpCaliburn | 0xE5ACB0 | 0xBE6548 | inl 0x838810 | 0x13B0 | uPlWpRedQueen |
| uPlShl | 0xE5AB70 | 0xBE95C0 | 0x82FE30 | 0x17C0 | uShell |
| uPlCmnShl000, uPlDanteShl000–019, uPlNeroShl000–003 | 0xE5A520–0xE5AB30 | 0xBE6720–0xBE92B0 | mostly inl | 0x17C0–0x3530 | uPlShl (DanteBossShl000 → uPlDanteShl000) |

Nested uPlayer components (MtObject-derived; ctor inlined into the uPlayer ctor):

| Component | DTI | Vtable | Size |
|---|---|---|---|
| cSECtrl | 0xE5A2A0 | 0xBE33D0 | 0x17C |
| cMotCancel | 0xE5A2C0 | 0xBE66EC | 0x2C |
| cHitSlowCtrl | 0xE5A2E0 | 0xBE3478 | 0x10 |
| cLegIkCtrl | 0xE5A300 | 0xBE345C | 0x210 |
| cParamTblCtrl | 0xE5A320 | 0xBE3424 | 0xC |
| cPeripheral | 0xE5A340 | 0xBE3408 | 0x98 |
| cWeaponCtrl | 0xE5A380 | 0xBE3440 | 0x44 |
| cInterface | 0xE5A3A0 | 0xBE33B4 | 0x4C |
| cProcSpdCtrl | 0xE5A3C0 | 0xBE33EC | 0x30 |
| cBenchmarkCtrl | 0xE5A500 | 0xBE66BC | 0x4C |

Nero has two nested components. `uPlayerNero::cOverDriveGuage` (0x54) is at instance `+0xCCE4`, with vtable `0xBE5288`. `cDevilTrgAtckCheck` (0x1C) is at `+0xCDC4`, with vtable `0xBE52A4`.

**Label fixes this pass:**
- **uPlayer nested vtables:** cSECtrl, cMotCancel, cWeaponCtrl, cHitSlowCtrl and cProcSpdCtrl had wrong or swapped labels. `0xBE66EC` was labelled cSECtrl but is cMotCancel.
- **Devil Bringer collision control:** `uPlWpRightHand::uCollisionCtrl` was previously a bare `uCollisionCtrl`.
- **Nero:** `cDevilTrgAtckCheck`.
- **DTI globals:** `MtDTI_uPlayerDante` → `uPlayerDante::DTI` and `MtDTI_uPlayerNero` → `uPlayerNero::DTI`.
- **MyDTI vtables:** labelled for Dante, Benchmark, Boss, MeleeCancel and Nero.

## SE → DX9 vtable slot mapping (piecewise)

Unlike the enemies, the player-side mapping is **not** one constant. SE's newer engine inserts
virtuals at several depths, so the offset `k = SE − DX9` grows in bands. All three workers who
derived the Dante, uPlayer and Boss maps independently agree.

| DX9 slots | SE slots | k | Anchors |
|---|---|---|---|
| 0–5 | 0–5 | 0 | dtor, createUI, isEnable, createProperty, getDTI, setup |
| 6–9 | 8–12 | 2–3 | |
| 12 | 21 | 9 | `kill` |
| 29 | 50 | 21 | |
| 30–37 | 53–60 | 23 | `main` 30, `updatePtr` 31 |
| 54 / 57 | 80 / 83 | 26 | |
| 77–86 (shells / weapons) | 114–124 | 37 | weapons: SE 116 has no DX9 slot |
| 101 | 146 | 45 | uPlayer |
| 106–119 | 173–186 | 67 | uPlayer / Nero |
| 142–151 | 216–228 | 74–77 | uPlayer |
| 153–163 | 233–243 | 80 | |
| 170–175 | 261–266 | 91 | |
| 176–180 | 269–273 | 93 | uPlayer tail |
| 182–221 | 289–328 | 107 | Dante / Boss own virtuals |

The exact per-slot tables are in each worker JSON (`classes.<cls>.slot_map_dx9_to_se` / `slot_shift`).

**Other virtual differences:**
- **DX9-only virtuals:** Nero slots 123 and 132.
- **Virtual in SE only:** `checkPoseEnd`, `checkWeaponChange` and about 6 others are non-virtual direct calls in DX9.

## Findings that matter for the multiplayer refactor

- **99 earlier hand-given names were wrong** and are now replaced. The old name is kept as `was:` in the comment. Several put methods on the wrong class:
  - `uPlayerNero::setShortGrabTarget` → **`uPlNeroDevil::setBusterParam`**: buster parameters live on the Devil Bringer devil arm, not on uPlayerNero.
  - `updateGrabMotionStep` → `uPlNeroDevil::setErase`: `this` is uPlNeroDevil, and it isn't grab logic.
  - `setGrabRangeParam` → `setSnatchTargetPos`.
  - `uPlayerNero::setKabutoCollisionDown/Up` → `uPlNeroDevil::setYamatoMotionStop/Restart`.
  - `uPlWpRightHand::setMotion` and `uPlayer::getNoFromMotSeq` → `uPlNeroDevil::`.
  - `uCollisionCtrl::setGrabHit` → `uPlWpRightHand::setGrabHit`. The rest of `uPlWpRightHand::uCollisionCtrl` (long grab, buster, enemy guard) is now fully named.
  - `registerWithMediator` → SE `setGameSystem`.
  - `uPlayerDante::checkRunBegin`, `tickLuciferTimer` (→ `checkAtckRenda`) and five other Nero/Dante-labelled functions are base **uPlayer** code.
  - `uPlayer::setActionFootwork_w` → `uPlayerDante::moveActSnatch`. That one ICF body covers moveActSnatch, moveActBuster, moveActDanteDead and moveActDanteButDead (Dante slots 217–220).
- **Confirmed:** all 97 existing `uPlayerDante::moveAct*`/`moveAtck*` names match SE. Their motion-ID constants and the `moveActionLower` dispatch order agree.
- **`0x7B0250–0x7B2020` is uPlayer component code** (cWeaponCtrl, cSECtrl, cLegIkCtrl), not Dante. `cSECtrl::request/stop` take the owning `uPlayer*` (component at `+0x1D60`), not `cSECtrl*`.
- **Nero grab dispatch:** the grab action table `off_E15F38` confirms the `mvAtckSG*` ground/air/D assignment. The four Echidna snatch handlers stay `medium` because only address order separates them.
- **Action tables:** Boss AI uses a 60-entry table at `0xE15C10`. The command table has 85 entries in DX9 vs 102 in SE.

## ICF folding and other gotchas

- **Folded bodies (identical code merged by the linker):** examples are one deleting dtor (`0x81F5F0`) for 9 shell vtables, one `updateMatrix` (`0x833740`) for 7 weapons, and `uPlShl::die` (`0x820700`) for every shell plus uPlGrabShortHit. Several Nero/Dante bodies are shared too (`sync`, kMdlHead ctor, `atckGunPoseShotSub`, `updateMotionSeWeatherCtrl`, `setCameraVib` = `uPlayer::setCameraVibration`). Each carries an `ICF-folded:` comment listing all SE aliases.
- **Switch-case fragments:** IDA had split `uPlayer::cBenchmarkCtrl::getActType`'s switch cases (`0x802B6E–0x802B80`) into 4 fake functions. They are merged back into `0x802B60`.
- **Moved code:** `uPlNeroDevil::requestSe` has a DX9 copy in the uPlNeroShl003 region, named `uPlNeroShl003::requestSe`.
- **Content difference:** `isArea408BedRoof` tests area 344 in DX9 rather than 408.
- **Name mangling:** IDA turns `<>` into `_`, e.g. `setup<uPlWpCaliburn>` → `setup_uPlWpCaliburn_`. Dtors use mangled names (`??1`, `??_G`, `??_E`).

## mpPlayer call-site inventory regenerated

`RE/mpplayer_call_sites.json` was rebuilt after both passes. **1048 sites** (944 inline + 104 accessor):

- **+1 vs the 1047 baseline:** an inline read in `uPlayerDanteBoss::checkPlayerDeadThink` (`0x7C6470`), which was undefined code before this pass.
- **Owning class:** sites with **no owning class dropped from 716 to 245**; 471 now resolve to a named uEm or uPl class through the new names.

## Open items

| DX9 ea | Status |
|---|---|
| 0x7B2020 | medium: `cSECtrl::stop` variant with type fixed to 1 |
| 0x7B6A20 | medium: likely `setDrawMode` (SE moved it to slot 52) |
| 0x7B8D90, 0x7E4F80 | medium: stinger-jump check / SE slot-203 ICF stub; both resemble one SE function |
| 0x7C7700 | medium: `nextTutorial` |
| 0x8034E0 | medium: `isEnableAtckForceCancel` or `checkMotCnclEnable` |
| 0x831800 | medium: `uPlSwordBlur::setPause` or `setBlur` |
| Nero Echidna snatch handlers (4) | medium: separated by address order only |

Not covered: `uActor` / `uShell` base methods and non-`uPl` helpers inside the range (kDamageParam, sMediator thunks).
