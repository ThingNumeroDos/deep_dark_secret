# Nero grab / buster / snatch paths that read `sMediator::mpPlayer`

Date: 2026-10-05, after the SE-name passes (`uem_se_dx9_map.md`, `pl_dx9_se_map.md`). This lists
every grab-related function that resolves "the player" through `sMediator::mpPlayer` instead of
the actual grabber, and says how each can get the right player.

- **Data:** `RE/nero_grab_audit.json` (132 grab/buster/snatch functions that read mpPlayer) and `RE/nero_field_scan.json` (every subclass-only field read through mpPlayer, binary-wide).
- **Scripts:** `RE/scripts/nero_grab_audit.py` (Hex-Rays signals) and `RE/scripts/nero_field_scan.py` (instruction-level taint scan). Both are run with `py_exec_file`.

## Why this needs special care

`mpPlayer` is typed `uPlayer*` (size `0x3270`). In single-player, grab code can treat it as Nero,
because only Nero has a Devil Bringer. In multiplayer, `mpPlayer` can be a different player from
the grabber, which leads to three failure modes:

| Severity | What happens |
|---|---|
| **Crash** | **Unguarded downcast.** The code reads `mpPlayer+0xCDF8` (`uPlayerNero::mpDevilStand`) without a type check. If mpPlayer is Dante, that offset lands inside Dante's data, and the value is dereferenced as a pointer. |
| Wrong player, no crash | **Guarded downcast.** A Nero check runs on `mpPlayer`, then Nero fields are read. The enemy snaps to, or reads state from, the wrong Nero, or takes the non-Nero branch while being grabbed. |
| Wrong player, no crash | **Type-agnostic use.** Position, rotation, `mActStat`, `isDevilTrigger()` or `mPlayerID` are taken from the wrong player. |

Hex-Rays prints reads past `0x3270` as nonsense (e.g. `mpPlayer_1[4].MotionArray[1].mInterRate`),
so the crash class was found with an **instruction-level** scan. Pseudocode alone undercounts it.

### The four Nero checks in use

| Form | Where |
|---|---|
| `strcmp(p->getDTI()->mName, "uPlayerNero")` (slot 4; one pooled string at `0xBCF654`) | 10 functions |
| `checkDTI(p, &uPlayerNero::DTI)` (is-kind-of) | 10 call sites |
| `p->mPlayerID == 1` | uEm019/uEm021 grabbed routines, `uEm022::setBusterCameraEnd`, camera |
| `p->isDevilTrigger()` (vtable **slot 134**, virtual on all players) | 14 call sites; picks the DT variant of a grab, usually after a Nero check |

## The correct pattern already exists

**`uEnemy::grabMessage`** (`0x734EE0`) does it right:
1. It takes the attacker from the hit record: `hit->+0x98` gives the collision owner, and `->+0xE4` gives the attacker unit.
2. It calls `checkDTI(attacker, &uPlayerNero::DTI)`.
3. Only then does it read `attacker->mpDevilStand->mpRightHand`.

`uEm021_Leaf::hitMessage` checks both Nero and Dante on the attacker the same way.

The grabber is also directly reachable from the Devil Bringer objects through typed back-pointers:

| From | Field | To |
|---|---|---|
| `uPlWpRightHand` | `mpParentPl` (+0x2F34) | `uPlayerNero*` |
| `uPlWpRightHand` | `mpParentDevil` (+0x2F30) | `uPlNeroDevil*` |
| `uPlNeroDevil` | `mpParent` (+0x1370) | `uPlayerNero*` |
| `uPlWeapon` | `mpParent` (+0x1378) | `uPlayer*` (any weapon) |

## 1. Crash class: unguarded Nero downcasts through mpPlayer

| Function | Chain read through mpPlayer | Fix source |
|---|---|---|
| `uEm000Base::setGrabBlown` 0x552B40 | `mpDevilStand -> mpRightHand` | cached hand (+0x2680) → `mpParentPl` |
| `uEm010::grabBlown` 0x5AA280 | `mpDevilStand -> mpRightHand -> mRetPos` | cached hand (needs one; uEm010 caches none) |
| `uEm011::grabBlown` 0x5C9E90 | `mpDevilStand -> mpRightHand -> mRetPos` | needs cached grabber |
| `uEm015::setGrabFar` 0x6008F0 | `mpDevilStand -> mpRightHand` | cached hand (+0x8C20) |
| `uEm016::setGrabFar` 0x612800 | `mpDevilStand -> mpRightHand` | cached hand (+0x20A8) |
| `sub_629850` (uEm017, likely `grabSnatch`, medium) | `mpDevilStand -> mpRightHand -> mRetPos` | cached hand (+0x8158) |
| `uEm022SpearShl::moveEx` 0x6BD6B0 | `mpDevilStand -> mpRightHand -> … +0x3C` | shell owner / grabber at spawn |
| `uEm015::moveEx` 0x5F9340, `uEm016::sync` 0x60E640 | `mIsEnemyBuster` (Nero-only flag) | cached hand → `mpParentPl` |
| `cCameraPlayer::getJointPosGrabedEnemy` 0x421A30, `sub_4219D0` | `mpSGEnemy` (Nero snatch target) | camera's own player |
| `sub_4AB060` (called only from `uPlayerNero::moveEx`) | `mpDevilStand -> mpRightHand` | **`this`**: player-side code reading the global instead of itself |

These need a null-guarded `uPlayerNero*` taken from the grab context, **not** from a player index plus downcast.

## 2. Guarded downcasts: Nero check on mpPlayer, then Nero fields

| Function | Check | Then reads |
|---|---|---|
| `uEm013::setGrabLong` 0x5E9080 | strcmp | `mpDevilStand->mpRightHand->mRetPos` |
| `uEm035::setGrabFar` 0x720DA0 | strcmp | `mpDevilStand->mpRightHand->mRetPos` (else falls back to `mpPlayer->mPos`) |
| `uEmSample::setGrabFar` 0x72EA50 | strcmp | same as uEm035 |
| `uEm019_00::set_em019_grabbed_far` 0x678D00 | strcmp | `mpDevilStand->mpRightHand` |
| `uEm000Base::grabNear003Air` 0x5559B0 | checkDTI(mpPlayer) | |
| `uEm000Base::grabShortMessage` 0x5584E0 | checkDTI(mpPlayer) + slot 134 | Hand arg available, cached at +0x2680 |
| `uEm000Base::customMessage` | checkDTI(mpPlayer) | |
| `uEm018::thorowOutDownFLoop` / `BLoop` | checkDTI(mpPlayer) | |
| `uEm032::exeEasyBitCatch` 0x716420 | checkDTI-style cast (`sub_4019B0`) on mpPlayer | |
| `uEm008_009Base::setGrabNear` 0x58FAA0 | checkDTI | object register origin not resolved; verify |

Branch-only Nero checks (strcmp, then `isDevilTrigger` picks the DT animation; no Nero fields read):
`uEm015/uEm016::grabShortMessage`, `uEm015/uEm016::customMessage`, `uEm018::setHitThorw`, `uEm018::setThrowOut`.

## 3. Grab message handlers that ignore their grabber argument

The SE signature is `grabShortMessage(uPlWpRightHand*, cCollisionGroup*, cCollisionGroup*)`. All 13
handlers receive the hand, yet read `mpPlayer` for air state (`mActStat & 2`), `isDevilTrigger()`,
position or the Nero check. **Fix: `hand->mpParentPl`.** Ten of them already store the hand on the enemy:

| Class | Hand cached at (byte offset) |
|---|---|
| uEm000Base | +0x2680 |
| uEm005, uEm022, uEm023 (uEmAngelo family) | +0x2174 |
| uEm015 | +0x8C20 |
| uEm016 | +0x20A8 |
| uEm017 | +0x8158 |
| uEm019 | +0x21B0 |
| uEm021 | +0x233C |
| uEm035 | +0x2468 |
| uEm029, uEm030, uEm030Spada | not cached; needs a new field |

These cached pointers are the natural source for the **per-frame grab states** (`grabNear*`,
`grabBlown`, `grabThrow`, `em0xx_grabbed*`, `buster`, `snatch`, …; about 100 functions in
`nero_grab_audit.json`). Those states take no arguments and today read `mpPlayer` every frame for
position, rotation, matrix and `m_delta_time`. Classes without a cache (uEm010, uEm011, uEm029,
uEm030, uEm030Spada, uEm013, uEm018) need one added, or need the grabber passed through the state.

## 4. Other per-player Nero/Dante state read through mpPlayer (not grab, same problem)

- **HUD:** Nero's DT gauge `mOdGaugeCtrl` is read in `uCockpitNero::checkPtr` and `sub_508010`. Dante's `mRgGauge` (+0x14DAC) is read in `sub_505120` and `mPandoraGauge` (+0x151F4) in `sub_504FE0`. These are **unguarded Dante downcasts** in cockpit code.
- **Save:** `sMediator::savePlayerParam` reads `mOdGaugeCtrl` (persists Nero gauge state).
- **Dante type checks on mpPlayer:** `sub_51BD70` (checkDTI uPlayerDante) and `uEm005::hitMessage`.

## Takeaways for the multiplayer design

- **Grab is already a pairwise interaction**, so it never needs "player index → downcast". The grabber is always reachable from the grab context: the hit record's attacker, the `uPlWpRightHand*` argument, or the hand cached on the enemy. Rewriting these sites to use that source fixes the crash class and the wrong-player class together. It is also independent of the dispatcher model chosen in `mpplayer_dispatcher_patch_plan.md`.
- **Redirecting `mpPlayer` alone is unsafe for grab.** Under the global "active player" model, a Dante-active frame during a Nero grab hits the Section 1 crash paths.
- **Data-layout work needed:** a grabber field on enemies that don't cache the hand (Section 3). Use the same tail-extension approach as the `sDevil4Pad` plan, or reuse an existing cache.
