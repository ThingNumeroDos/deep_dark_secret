# Player Instance Pointer (sMediator::mpPlayer) — Findings

## Location

`sMediator::mpPlayer` lives at offset **+0x24** inside the sMediator singleton.  
The singleton itself is accessed via the global pointer `sMediator::mpInstance` at `0xE558B8`.

Access pattern everywhere in the codebase:
```asm
mov eax, [sMediator::mpInstance]   ; load singleton ptr
mov ecx, [eax+24h]                 ; load uPlayer*
```

---

## Player Creation

Player instantiation happens in **`sub_44A910`** (a large room/game-state machine, ~13 KB).  
A jump table at `0x44BE4B` switches on a character enum (values 0–6):

```asm
0x44be52:  ; case N — allocate + construct player type
  mov ecx, UnitAllocator
  push 10h                          ; alignment
  push 0D690h                       ; size
  call UnitAllocator->vtable->memAlloc
  call uPlayerNeroTutorial__ctor
  ; then: sUnit::addBottom(player, 0xD)
```

Known character slots: Nero, Dante, NeroTutorial, and variants.

### Factory chain

Both concrete player types expose a static `newInstance` factory accessed through their DTI vtable slot +4:

| Function | DTI vt addr | Alloc size |
|----------|-------------|------------|
| `uPlayerNero::newInstance` | `0xBE5280` | 54 912 B (0xD680) |
| `uPlayerDante::newInstance` | `0xBE3FC8` | 86 768 B (0x15290) |

Both allocate via `UnitAllocator->vtable->memAlloc`, then call into the concrete constructor.

### Constructor chain

```
uPlayerNero::uPlayerNero / uPlayerDante::uPlayerDante
  └── uPlayer::uPlayer           (base: sets vtable, inits all embedded components)
        └── uActor::uActor       (engine actor base)
```

---

## Self-Registration

Once fully constructed, the player registers itself with the singleton via a dedicated vtable method:

**`sub_7A91C0`** (called via vtable — appears at vtable offsets for all player types):
```cpp
int __thiscall sub_7A91C0(uPlayer *this)
{
    sMediator::mpInstance->mpPlayer = this;  // the only write of mpPlayer to a live value
    return sub_4A5AA0();
}
```

This is the single point where `mpPlayer` is assigned a non-null value.

### Teardown

On room transition/cleanup, `sub_44A910` calls vtable[+0x30] on the live player (likely `kill()`), then zeros the field:
```asm
mov dword ptr [edx+24h], 0    ; mpPlayer = nullptr
```

---

## uPlayer Struct Layout (base class, from constructor)

uPlayer inherits **uActor**. Known embedded sub-objects (set in `uPlayer::uPlayer` at `0x7A5B30`):

| Offset | Component | Notes |
|--------|-----------|-------|
| +0x00 | vtable (`uPlayer::vftable` @ `0xBE30E0`) | |
| +0x1340 (4928) | sub-object (off_BE3408) | |
| +0x1408 (5128) | sub-object (off_BE33B4) | |
| +0x1474 (5236) | `cProcSpdCtrl` | speed control |
| +0x1484 (5252) | `cHitSlowCtrl` vtable | hit-stop control |
| +0x1704 (5892) | sub-object (off_B9AD40) | |
| +0x1720 (5920) | sub-object (off_B9AD40) | second instance |
| +0x17A0 (6048) | `cLegIkCtrl` [0] | IK for left leg |
| +0x19B0 (6576) | `cLegIkCtrl` [1] | IK for right leg (stride 528) |
| +0x1BC0 (7104) | `cFootprintCtrl` [0] | footstep VFX |
| +0x1BE0 (7136) | `cFootprintCtrl` [1] | |
| +0x1D88 (7560) | `cWeaponCtrl` vtable | weapon management |
| +0x1DD4 (7636) | `cMotCancel` [0] (vtable_uPlayer_cMotCancel) | motion cancel |
| +0x1DF8 (7672) | `cMotCancel` [1] | (stride 36) |
| +0x20EC (8428) | `uGetItem` [0] vtable | item pickup |
| +0x2120 (8480) | `uGetItem` [1] vtable | |
| +0x28AC (10412+) | 7× sub-objects (off_B9AA5C, stride 60) | |
| +0x30C0 (12480+) | 8× sub-objects (off_BE66EC, stride ~44) | |

The struct extends to at least **+0x3258 (12888)** in the base class.  
uPlayerNero adds ~41 KB on top; uPlayerDante adds ~73 KB.

---

## Consumer Surface — Who Reads mpPlayer

**Re-verified 2026-06-28 against the live DB.** Direct `sMediator::mpInstance` → `+0x24`
deref pairs, grouped by containing function:

| Scan window | Unique functions | Sites |
|-------------|------------------|-------|
| 6 instructions | **707** | 942 |
| 10 instructions | 745 | 1011 |
| 20 instructions | 778 | 1082 |

Total raw xrefs to `sMediator::mpInstance` = **2721** (most are other-field accesses, not `+0x24`).

This supersedes the earlier "685+ unique functions / previously observed 731" figure — the
6-instruction-window count is now **707 functions / 942 sites** (more code has been defined since
the original scan). The named-function subset (47 functions) is unchanged in membership; some
per-class *site* counts have dropped because the original table folded in indirect
`getPlayerPos`/`getPlayerMat` reads and cached-member accesses that the strict 6-insn scan does
not count (see the corrected table below).

---

### Named subsystems (47 functions)

**Site counts re-verified 2026-06-28** (strict 6-insn direct-deref scan). Where the live count
differs from the original, the live value is shown and the original in parentheses. Drops are
because the original counts bundled indirect `getPlayerPos`/`getPlayerMat` and cached-member reads.

| Class | Fns | Sites (live / orig) | Role |
|-------|-----|---------------------|------|
| `cCameraPlayer` | 11 | 14 (17) | Camera — tracks player for orientation, mode, throw/buster checks |
| `uEm000Base` | 9 | 14 (28) | Enemy base — grab/near targeting against player |
| `uEnemy` | 3 | 3 (4) | Enemy base — setup, per-frame move, target-pos query |
| `uEm010` | 3 | 6 | Enemy type 010 — grab/throw chains |
| `uCameraCtrl` | 2 | 2 (6) | Camera control sync and box-check |
| `uDamage` | 2 | 2 (5) | Damage calc — player-to-enemy correction and final calc |
| `uActor` | 2 | 2 | Actor base — homing angle, SE routing |
| `uCockpit` / `uCockpitDante` / `uCockpitNero` | 3 | 3 (4) | HUD — null-pointer guard before rendering |
| `aRoom` | 3 | 3 (6) | Room lifecycle — cleanRoom, pause checks, event pause |
| `sGameState::player_spawn_state` | 1 | 12 (75) | Spawner/game-state machine; orig 75 folded in all mpPlayer-derived accesses |
| `sMediator::savePlayerParam` | 1 | 1 | Save/restore player params to sSave |
| `sStylishCount::main` | 1 | 2 | Style rank tracking |
| `uDevilCamera::checkPlayerJumpPoint` | 1 | 1 | Devil-trigger camera — jump-point check |
| `uCollisionMgr::move` | 1 | 1 | Per-frame collision manager tick |
| `uPlNeroShl001::setup` | 1 | 2 | Nero projectile — init targeting |
| `uPlayer::registerWithMediator` | 1 | 1 | Writes `mpPlayer = this` (the single assignment) |
| `uPlayerDanteBoss::checkBeforeAction` | 1 | 1 | Dante-as-boss pre-action check |
| `cPeripheral::update` | 1 | 1 | Input routing — maps pad to player |

---

### Unnamed subsystems — by address range (638 confirmed)

Address ranges are the primary classification signal; named anchor functions in each range
confirm the resident class where available.

| Range | Fns | Sites | Likely class / subsystem | Evidence |
|-------|-----|-------|--------------------------|----------|
| `0x40xxxx` | 5 | 10 | `aRoom` / game-loop helpers | `aRoom::move`, `aRoom::main` are callers |
| `0x41xxxx` | 11 | 11 | Camera & action-control helpers | `uPlayer::isActAtck` at `0x416AD0`; callers `sub_41A740`, `sub_41B540` |
| `0x42xxxx` | 16 | 31 | Camera & action-control helpers | Called by action-mgr chain from 0x41xxxx |
| `0x44xxxx` | 6 | 31 | Game-state support (near `sGameState`) | `sGameState::player_spawn_state` at `0x44A910` |
| `0x45–4Bxxxx` | ~37 | ~50 | Combat utilities (`cUtil`, `kAttackStatus`, `kDefendStatus`, `sCollisionGame` area) | Named: `cUtil::checkHeight` `0x45E790`, `sCollisionGame::checkAttackObj` `0x47C300` |
| `0x4Cxxxx` | 14 | 17 | Session / sub-mediator components | No named fns; called from 0x4D cluster |
| `0x4Dxxxx` | 18 | 40 | Session / sub-mediator components | 18 fns all rooted at `sub_4D0B10` |
| `0x4Exxxx` | 13 | 48 | Session / sub-mediator components | 13 fns all rooted at `sub_4E0FF0`; highest per-fn site density |
| `0x50–53xxxx` | ~15 | ~20 | Collision utilities | `sCollision::*` at `0x50–53xxxx` |
| `0x54–5Dxxxx` | ~60 | ~100 | Enemy classes (multiple, small–medium) | Address range consistent with mid-tier enemies |
| `0x5E–63xxxx` | ~40 | ~60 | Enemy classes (batch 1; `uEm*`) | sUnit doc: `sub_5EE690`, `sub_631FD0` on line 15 |
| `0x64–65xxxx` | 20 | 61 | Unidentified enemy class | All 20 fns share parent `sub_64DF60`; no named fns in range |
| `0x66–6Cxxxx` | ~60 | ~90 | Enemy classes (multiple) | Scattered mid-range enemy addresses |
| `0x6D–6Exxxx` | 31 | 77 | Unidentified enemy class (large, with model ops) | `j_uModel::draw` at `0x6D86D0`; all 31 fns share parent `sub_6DB860`/`sub_6DB190` |
| `0x7Cxxxx` | 24 | 41 | **`uPlayerDante`** (confirmed) | Named: `uPlayerDanteBoss::checkBeforeAction` `0x7C0360`, `uPlayerDante::moveActionLower` `0x7C9670`, `uPlayerDante::moveActAtckL` `0x7CD190` |
| `0x80–85xxxx` | ~12 | ~20 | `uPlayerNero` methods | `uPlayerNero::uPlayerNero` at `0x7E1B30`; 0x80–85 are its extended methods |
| `0x86–88xxxx` | 29 | 42 | Stage interactive objects (`uStageSet*`, `uSeGenerator`) | Named: `uSeGenerator::init` `0x854FC0`, `uStageSetLaser::uStageSetLaser` `0x8825F0` |

---

### Multiplayer categorisation

| Category | Classes | Refactor strategy |
|----------|---------|-------------------|
| **Per-player** (must fan out to N players) | `cCameraPlayer`, `uCameraCtrl`, `uDevilCamera`, `uCockpit/*`, `cPeripheral`, `sStylishCount`, `sMediator::savePlayerParam` | Replace singleton read with per-slot pointer; caller receives player index |
| **Enemy targeting** (need nearest/indexed player query) | `uEm000Base`, `uEm010`, `uEnemy`, unnamed 0x64–65xxxx and 0x6D–6Exxxx clusters | Wrap in `getTargetPlayer(this)` helper; avoids touching every call site |
| **Game state** (score, damage, mission) | `uDamage`, `sGameState::player_spawn_state`, unnamed 0x4C–4Exxxx cluster | Thread player index through state-machine calls |
| **Player self** | `uPlayer::registerWithMediator`, `uPlayerDante` (0x7Cxxxx), `uPlayerNero` (0x80–85xxxx) | Already per-instance; register multiple players in mpPlayer[N] |
| **Passive / position queries** | `uActor`, unnamed 0x86–88xxxx stage objects | Single `getAnyPlayer()` or nearest-player query sufficient |
| **Room / infrastructure** | `aRoom`, 0x40–42xxxx helpers | Low priority; reads are lifecycle guards, not per-frame |

---

## Cached `mpPlayer` Members — Init-Slot Survey

Beyond direct singleton reads, **14 classes cache `mpPlayer` into a member field** inside their
vtable `+0x14` (`init()`) method. These are a separate hazard for multiplayer: the cached pointer
is set once at init time and never refreshed, so it will be stale if the player pointer changes
(respawn, character swap) and wrong-player if a second player is added.

Detected via pattern: `mov rX, [sMediator::mpInstance+24h]` followed within 20 instructions by
`mov [this+offset], rX` inside a function that sits at vtable slot `+0x14`.

### Group A — Player-owned components (fix: pass owner's `mPlayerIndex` at construction)

These are sub-objects embedded inside a player-owned unit. They should never query the singleton
independently — the owning player's index is the right source.

| vtable | `init()` | Cached at | Class (DTI string evidence) |
|--------|----------|-----------|------------------------------|
| `0xBC74A0` | `0x506D90` | `+0x00C` | IK / joint-constraint component (`aMparentjntno`, `aMchildjntno`) |
| `0xBC74EC` | `0x504FE0` | `+0x014` | IK / joint-constraint component (same cluster) |
| `0xBC74F4` | `0x5052D0` | `+0x014` | IK / joint-constraint component (same cluster) |
| `0xBC9574` | `0x53B7B0` | `+0x02C` | Effect-camera component (`aUefctcam`, `aEfcamParmeter`) |
| `0xBE46E0` | `0x7C0EA0` | `+0x1FFC` | `uPlayerDanteBoss` sub-object (`aUplayerdantebo`, `aCollisionEmDan`) |
| `0xBE4724` | `0x7C7ED0` | `+0x00C` | `uPlayerDanteBoss` sub-object (same cluster) |
| `0xBE487C` | `0x7C8FD0` | `+0x1C28` | `uPlayerDanteBoss` sub-object (same cluster) |

Large offsets (`+0x1FFC`, `+0x1C28`) indicate `this` is a sub-object embedded deep inside
`uPlayerDante`; the root object starts 0x1FFC / 0x1C28 bytes earlier.

### Group B — Enemy / stage targeting (fix: resolve `uPlayer*` from player index at runtime)

These units cache `uPlayer*` to read both spatial data (`uCoord` fields: +0x030 world pos,
+0x060 world matrix) **and** character-specific animation flags that only exist on `uPlayer`.
Because animation flags are player-type–specific they cannot be sourced from `uCoord*` or
`uActor*` alone — the type must stay `uPlayer*`.

The fix is to **not cache the pointer at init**. Instead the class should store a `uint8_t mPlayerIndex`
(set at spawn, not init) and resolve `sMediator::getPlayer(mPlayerIndex)` at the call site each frame.
A fixed pointer set at init is also semantically wrong even in single-player: the player can die and
respawn, producing a new `uPlayer` instance at a different address.

| vtable | `init()` | Cached at | Class (DTI string evidence) |
|--------|----------|-----------|------------------------------|
| `0xBD04B0` | `0x5F9120` | `+0x14B4` | Enemy AI — behavior timers (`aMfallingtimer`, `aMbesiegingtime`, `aMsameactiontim`) |
| `0xBD0518` | `0x603950` | `+0x00C` | **[Nero-exclusive]** Enemy grab mechanics (`aMgrabtimer`, `aMgrabdmgtype`, `aMgrabreleasety`) |
| `0xBD0BD0` | `0x60E7E0` | `+0x14B4` | Enemy commander behavior (`aAppear`, `aMexcmndroutety`) |
| `0xBD0C38` | `0x614EE0` | `+0x00C` | Enemy commander behavior (same cluster) |
| `0xBD88AC` | `0x726B00` | `+0x14B4` | `pl022` model component (`aModelGamePl022_1/2/3`) |
| `0xBF525C` | `0x879970` | `+0x018` | Stage enemy `em025` (`aUstagesetem025`) |
| `0xBF7C84` | `0x88FB40` | `+0x084` | **[Nero-exclusive]** `uStageSetSnatc*` — snatch/grab trigger (`aSnatchparam`, `aMeventhit`) |

Note: the three `+0x14B4` entries (vtables `0xBD04B0`, `0xBD0BD0`, `0xBD88AC`) share the same
member offset despite being different classes — they likely inherit from a common enemy base that
declares the player-cache field at that offset.

**Nero grab mechanic caveat:** Nero's grab (Devil Bringer / Snatch) has its own dedicated collision
flag. Any method that touches this flag or references grab/snatch behavior is Nero-exclusive —
these classes cache `uPlayerNero*` specifically, not a generic `uPlayer*`. The two confirmed
Nero-exclusive entries above (`0xBD0518`, `0xBF7C84`) must not be given a generic player-index
resolution path; they need an explicit `uPlayerNero*` obtained by index + downcast, with a null
guard for when the active player is Dante. The remaining entries in this table are unconfirmed
and should be audited individually before refactoring.

---

## `sMediator::getPlayerPos` / `getPlayerMat` — Indirect Player Accessors

Beyond direct `mpPlayer` reads and cached-member patterns, two sMediator methods abstract the
player position and world matrix for the rest of the engine. These are the highest-volume
indirect coupling points.

### Signatures

```c
// 0x493240 — 43 bytes
float * __usercall sMediator::getPlayerPos(float *result@<eax>, sMediator *this@<ecx>)
// Reads this+0x24 (mpPlayer), returns player+0x30..+0x38 as XYZ in result[0..2].
// Returns zero-vector if mpPlayer is null.

// 0x493350 — 450 bytes
float * __usercall sMediator::getPlayerMat(float *result@<eax>, sMediator *this@<ecx>)
// Reads this+0x24 (mpPlayer), copies 16 floats from player+0x60..+0x9C into result[0..15].
// Returns MtMatrix::Identity if mpPlayer is null.
```

These also confirm two uPlayer field offsets:
- `uPlayer+0x030` — world position (3 floats, XYZ)
- `uPlayer+0x060` — world matrix (MtMatrix, 64 bytes)

### Call site summary

Re-verified 2026-06-28 (live = code `call`/`jmp` refs inside defined functions):

| Method | Call sites (live / orig) | Unique callers (live / orig) |
|--------|--------------------------|------------------------------|
| `sMediator::getPlayerPos` | 59 (60) | 35 (54) |
| `sMediator::getPlayerMat` | 45 (46) | 24 (42) |

Site counts are stable (±1). The unique-caller drop reflects a stricter caller-counting method
here (defined-function `call`/`jmp` only); the **site** count is the load-bearing metric and holds.

### Caller breakdown — `getPlayerPos`

| Caller class / range | Representative functions | Notes |
|----------------------|--------------------------|-------|
| Camera | `uCameraCtrl::sync`, `uCameraCtrl::getInitNowArea` | Per-player: need camera owner's index |
| Game state (0x4D–4Exxxx) | `sub_4D4300`, `sub_4EA020`, `sub_4ECA30` | Session management |
| Enemy AI (0x55–0x71xxxx) | `sub_5A1C80`, `sub_5E0FF0`, `sub_6A6270`, `sub_6DF490`, `sub_6E1660`, `sub_70CF70` | Targeting: nearest-player query |
| uPlayerDante (0x7Cxxxx) | `sub_7C2AA0`, `sub_7C3EE0` | Owner's own position — already correct |
| Stage / Nero area (0x86–0x89xxxx) | `sub_869F00`, `sub_879970`, `sub_88FB40`, `sub_890D90` | Stage traps / Nero actions |

### Caller breakdown — `getPlayerMat`

| Caller class / range | Representative functions | Notes |
|----------------------|--------------------------|-------|
| Camera/action (0x42xxxx) | `sub_429350`, `sub_429750`, `sub_42A330`, `sub_42A9D0` | Camera orientation against player matrix |
| `uCollisionMgr::move` | `0x50CC40` | Per-frame grab collision |
| `uEm000Base` grab chain | `setGrabNear`, `grabNear`, `setGrabNearDevil`, `grabNearDevil`, `setGrabNear003`, `grabNear003`, `setGrabNear003Air`, `grabNear003Air` | 30+ sites — enemy grabs orient to player world matrix |
| Enemy mid-range (0x55–0x6Fxxxx) | `sub_55E250`, `sub_590680`, `sub_6762A0`, `sub_6F2BE0` | General enemy targeting |
| Player-adjacent (0x72–0x73xxxx) | `sub_720640`, `sub_734B60`, `sub_736410` | Player component / animation |

### Multiplayer fix

Because `getPlayerPos` and `getPlayerMat` are already clean wrappers, fixing them is
mechanical compared to inline reads:

1. Add a `uint8_t playerIndex` parameter to both methods.
2. Change the internal read from `mpPlayer` → `mpPlayer[playerIndex]`.
3. Update all 106 call sites — most can derive the correct index from their context:
   - Camera / HUD callers: pass owner's slot index.
   - Enemy grab callers: pass result of nearest-player query (already computed by grab logic).
   - Player-self callers (0x7Cxxxx): pass `this->mPlayerIndex`.

This is the lowest-effort multiplayer change in the player-reference surface because the
indirection already exists — only the signature changes.

---

## Camera Subsystem — Player-Reference Deep Dive (session 2026-06-28)

The camera surface is the cleanest per-player cluster: **15 unique functions** across three
classes touch the player. All are camera-owner-keyed (each player needs its own camera), and two
carry Nero-exclusive branches. The three classes form one object hierarchy: `cCameraPlayer` holds
the per-player follow/lock-on logic; `uCameraCtrl`/`uDevilCamera` are the concrete camera unit
(`uCameraCtrl::sync` is typed `uDevilCamera*` and tail-calls `uDevilCamera::sync`).

Confirmed this session: **`mPlayerID` 0 = Dante, 1 = Nero** (from `moveRightStickAxisY` selecting
`sSave::mNero.mBtn` when `mPlayerID==1`, else `sSave::mDante.mBtn`). This pins down the
Nero-exclusive `mPlayerID==1` gate in `checkThrow`.

### Direct mpPlayer reads (14 functions / 17 sites)

| Function | Addr | What it reads from the player | MP class |
|----------|------|-------------------------------|----------|
| `cCameraPlayer::initialize` | `0x417390` | `mPos` (seed camera pos/target at spawn) | per-player |
| `cCameraPlayer::initialize_0` | `0x417690` | (init variant) | per-player |
| `cCameraPlayer::checkThrow` | `0x418770` | `mDamage.type` (BLITZ_ELECTRIGGER), **`mPlayerID==1` (NERO)**, `mActionNo`, `mAtckId` | **Nero-exclusive branch** |
| `cCameraPlayer::checkMode` | `0x4188E0` | `mPos`, `mLockOn.mLockOnMode`, vtbl[170] (lock-on target) | per-player |
| `cCameraPlayer::checkBusterType` | `0x419110` | vtbl[134] (polymorphic buster query) | per-player |
| `cCameraPlayer::main00` | `0x419130` | `mPos`, `mActionNo==12`, `mRotY`, vtbl[152] | per-player |
| `cCameraPlayer::main01` | `0x419840` | `mPos` (×4), `mActStat & 2` — drives mEndTar/mEndPos/angle-hosei | per-player (hot) |
| `cCameraPlayer::correctPlOver` | `0x41F120` | `mPos` (camera occlusion/over-player correction) | per-player |
| `cCameraPlayer::moveRightStickAxisY` | `0x4223B0` | **`mPlayerID`** → `sSave.mNero`/`mDante` keybinds, `mRotY` | **per-player + per-character input** |
| `cCameraPlayer::moveRightStickAxisY_SixAxis` | `0x422AC0` | (SixAxis variant of above) | **per-player + per-character input** |
| `cCameraPlayer::cameraAngleYHosei` | `0x4255B0` | `mPos` (x/z) for Y-angle height correction | per-player |
| `uCameraCtrl::check_box` | `0x4F7C50` | `mPos` — point-in-polygon vs camera area boxes | per-player |
| `uCameraCtrl::sync` | `0x4F90B0` | `mpInstance->mSnatchJumpCamera` (**NERO**), `mpPlayer` null-guard, `mMissionNo==80`, `getPlayerPos` | **per-player + Nero branch** |
| `uDevilCamera::checkPlayerJumpPoint` | `0x532430` | `mActStat & 2` (air), `mPos` — cache jump-off point | per-player |

### Indirect reads via accessors (2 functions)

| Function | Addr | Accessor |
|----------|------|----------|
| `uCameraCtrl::sync` | `0x4F90B0` | `getPlayerPos` (also in direct list above) |
| `uCameraCtrl::getInitNowArea` | `0x4F9D50` | `getPlayerPos` + `mpInstance->mSnatchJumpCamera` (**NERO**) |

### Camera multiplayer refactor notes

- **All 15 are per-player.** A camera belongs to exactly one player; the singleton read must
  become "this camera's owning player." The right fix is to give each `cCameraPlayer`/`uDevilCamera`
  a `mPlayerIndex` (set when the camera is bound to its player) and resolve `getPlayer(mPlayerIndex)`
  instead of `mpInstance->mpPlayer`.
- **Nero-exclusive hazards (3 sites):** `checkThrow` (`mPlayerID==1` Devil-Bringer throw cam),
  `uCameraCtrl::sync` and `getInitNowArea` (both read `mSnatchJumpCamera`). Per the CLAUDE.md Nero
  caveat, these need an explicit `uPlayerNero*` (index + downcast) with a null guard when the owning
  player is Dante — a generic `uPlayer*` resolution is insufficient for the snatch/throw paths.
  Note `mSnatchJumpCamera` currently lives on the **singleton** (`sMediator+`), so it is also a
  per-player field that must be decoupled, not just read per-index.
- **Input is per-character, not just per-player:** `moveRightStickAxisY*` reads the player's own
  `mPlayerID` to pick that player's `sSave` keybinding block (`mNero` vs `mDante`). Two players
  sharing one save's keybinds would cross-wire camera input — each player's camera must read its
  own pad + its own keybind slot.

All 14 sites above carry an inline `[MP/camera] …` comment in the IDB as of this session.

---

## Enemy Grab-Interaction Tables → mpPlayer / uPlayerNero (session 2026-06-28)

Beyond direct reads and cached members, enemy classes reach the player through **two kinds of
function-pointer tables** holding grab-interaction (Devil Bringer / Snatch) handlers. Every handler
that resolves the player does so against `mpInstance->mpPlayer`, and the Nero-specific ones perform
a **runtime `strcmp(getDTI()->name, "uPlayerNero")` downcast** rather than caching a pointer.

### A. The `uEm000Base` grab-callback table (48 slots, replicated per enemy class)

The same logical table is embedded into multiple enemy-class data blocks. Four copies were found
(at `0xBCA110`, `0xBCA620`, `0xBCAD08`, `0xBCB2D8`); slots 0–38 and 41–47 are byte-identical across
all four — they differ **only at slots 39–40**, the per-class hook
(`sub_558B80` / `nullsub_2` / `sub_55F5E0` / `sub_5602A0`). So this is one shared
grab-behavior dispatch vector with a small per-class patch.

**12 of 48 slots read the player** (all confirmed against the live scan):

| Slot | Function | Player access |
|------|----------|---------------|
| 4 | `uEm000Base::setGrabBlown` (`0x552B40`) | mpPlayer |
| 7 | `uEm000Base::setGrabNear` (`0x552F00`) | mpPlayer + getPlayerMat |
| 8 | `uEm000Base::grabNear` (`0x5532F0`) | mpPlayer + getPlayerMat (reads `mPos`, `mQuat`) |
| 9 | `uEm000Base::setGrabNearDevil` (`0x553A70`) | mpPlayer + getPlayerMat |
| 10 | `uEm000Base::grabNearDevil` (`0x553DF0`) | mpPlayer + getPlayerMat |
| 11 | `uEm000Base::setGrabNear003` (`0x554780`) | mpPlayer + getPlayerMat |
| 12 | `uEm000Base::grabNear003` (`0x554B00`) | mpPlayer + getPlayerMat |
| 13 | `uEm000Base::setGrabNear003Air` (`0x555630`) | mpPlayer + getPlayerMat |
| 14 | `uEm000Base::grabNear003Air` (`0x5559B0`) | mpPlayer + getPlayerMat |
| 37 | `sub_556AB0` (`0x556AB0`) | mpPlayer + getPlayerPos |
| 38 | `sub_557530` (`0x557530`) | mpPlayer |
| 46 | `sub_55E250` (`0x55E250`) | mpPlayer + getPlayerMat |

These orient/position the grabbed enemy relative to the player's world matrix; they are **not
Nero-gated** (any player can be grabbed-onto), so a per-index `getPlayer()`/`getPlayerMat(index)`
resolution is sufficient — the index must be the player that initiated/owns the grab.

### B. Enemy grab-MESSAGE vtables — Nero-exclusive handlers (the `strcmp "uPlayerNero"` set)

Two enemy-class **message-dispatch vtables** (the `0xBD0518` and `0xBD0C38` classes the cached-member
survey already flagged) contain grab-message handlers at fixed slots that do the Nero downcast:

| Handler | Table slot | Class vtable | Behavior |
|---------|-----------|--------------|----------|
| `sub_603950` | `0xBD052C` (slot 8) | `0xBD0518` | grab message (case 21): `strcmp "uPlayerNero"` + `vtbl[134]==1` → grab Devil-Bringer joint |
| `sub_6037D0` | `0xBD05A4` (slot 38) | `0xBD0518` | reads `mActStat&2` (air) then `uPlayerNero` downcast → Nero vs non-Nero action |
| `sub_614EE0` | `0xBD0C4C` | `0xBD0C38` | commander-class grab handler, `uPlayerNero` downcast |
| `sub_614DF0` | `0xBD0CC4` | `0xBD0C38` | commander-class grab handler, `uPlayerNero` downcast |

### C. Directly-called Nero grab handlers (non-table) in other enemy classes

The full set of functions referencing the `"uPlayerNero"` string (`0xBCF654`, excluding
`uPlayerNero::DTI::init` which merely registers the name) is **10 handlers**. The 4 above are
table-dispatched; the remaining **6 are reached by direct `call`** in their owning enemy class:

`sub_5E9080`, `sub_640540`, `sub_640F00`, `sub_678D00`, `sub_720DA0`, `sub_72EA50`
(spanning enemy ranges 0x5E, 0x64, 0x67, 0x72xxxx).

### Multiplayer implication

All handlers in B and C are **Nero-exclusive**: they read `mpInstance->mpPlayer`, confirm it is a
`uPlayerNero` by runtime DTI-name compare, then read Nero-only grab state. In a multiplayer refactor
each must obtain an explicit `uPlayerNero*` via **player index + downcast**, with a null guard for
when the relevant player is Dante (the `strcmp` already encodes "skip if not Nero" — the refactor
replaces the singleton read with the indexed player but keeps the type guard). The table-A handlers
are player-type-agnostic and only need an indexed `getPlayerMat`/`getPlayerPos`.

All 10 Nero handlers carry an inline `[MP/grab][Nero] …` comment in the IDB as of this session.
This extends the cached-`mpPlayer` survey's two confirmed Nero-exclusive entries (`0x603950`,
`0x88FB40`) — the grab-table route surfaces **8 additional** Nero-exclusive player-resolution sites.

---

## Key Addresses

| Symbol | Address |
|--------|---------|
| `sMediator::mpInstance` (global ptr) | `0xE558B8` |
| `sMediator::mpPlayer` field offset | `+0x24` |
| `uPlayer::registerWithMediator` — self-register (sets mpPlayer) | `0x7A91C0` |
| `sGameState::player_spawn_state` — game-state / player spawner | `0x44A910` |
| Jump table (character select) | `0x44BE4B` |
| `uPlayer::uPlayer` ctor | `0x7A5B30` |
| `uPlayerNero::uPlayerNero` ctor | `0x7E1B30` |
| `uPlayerDante::uPlayerDante` ctor | `0x7B2150` |
| `uPlayerNero::newInstance` | `0x7E1A70` |
| `uPlayerDante::newInstance` | `0x7B2130` |
| `uPlayer::vftable` | `0xBE30E0` |
| `uPlayerNero::vftable` | `0xBE4FA0` |
| `uPlayerDante::vftable` | `0xBE3C50` |
| `uPlayer::MtDTI` | `0xE5A360` |
| `MtDTI_uPlayerNero` | `0xE5A4A0` |
| `MtDTI_uPlayerDante` | `0xE5A3E0` |
| `cCameraPlayer::main01` (lock-on cam, hot) | `0x419840` |
| `cCameraPlayer::checkThrow` (Nero throw cam) | `0x418770` |
| `cCameraPlayer::moveRightStickAxisY` (per-char input) | `0x4223B0` |
| `uCameraCtrl::sync` (master cam-area sync) | `0x4F90B0` |
| `uDevilCamera::checkPlayerJumpPoint` | `0x532430` |

---

## uActor Vtable — Newly Defined Functions

Slots 0–1 of `uActor::vftable` (`0xBC4B78`, 79 slots) were undefined; defined and named via SE cross-reference:

| Address | Name | Notes |
|---------|------|-------|
| `0x4A7250` | `uActor::scalar_deleting_destructor` | Slot 0 — calls dtor, conditionally frees via UnitAllocator |
| `0x4A6E50` | `uActor::newInstance` | Slot 1 — allocs 0x31C bytes, calls ctor |
| `0x4A7280` | `uActor::dtor` | Called by scalar_deleting_destructor |

---

## uPlayer Vtable — Newly Defined Functions

`uPlayer::vftable` at `0xBE30E0` (181 slots) + 6 nested class vtables.

| Address | Name | Notes |
|---------|------|-------|
| `0x7A6640` | `uPlayer::scalar_deleting_destructor` | Main vtable slot 0 |
| `0x7A66F0` | `uPlayer::dtor` | Called by sdd |
| `0x7A5950` | `uPlayer::cInterface::newInstance` | cInterface vtable slot 1 |
| `0x7B1360` | `cSECtrl::scalar_deleting_destructor` | cSECtrl vtable slot 0 |
| `0x7B1390` | `cSECtrl::dtor` | |
| `0x7A5A80` | `cSECtrl::newInstance` | cSECtrl vtable slot 1 |
| `0x7A5AE0` | `cProcSpdCtrl::newInstance` | cProcSpdCtrl vtable slot 1 |
| `0x7A5920` | `uPlayer::cPeripheral::newInstance` | cPeripheral vtable slot 1 |
| `0x7A5A50` | `uPlayer::cParamTblCtrl::newInstance` | cParamTblCtrl vtable slot 1 |
| `0x7B0E20` | `cWeaponCtrl::scalar_deleting_destructor` | cWeaponCtrl vtable slot 0 |
| `0x7B0E50` | `cWeaponCtrl::dtor` | |
| `0x7A5A00` | `cWeaponCtrl::newInstance` | cWeaponCtrl vtable slot 1 |

---

## uPlayer Struct — Gap Analysis and Fills

DX9 `uPlayer` is **12916 bytes (0x3274)** vs SE's **15040 bytes (0x3AC0)**. SE has 2124 extra bytes
distributed unevenly; the delta grows from +0x530 near offset 0x1494 to +0x680 by 0x2194.

Fields identified via equal-span cross-reference with SE (delta constant across the span = field exists in DX9):

| DX9 Offset | Field | Type | Notes |
|------------|-------|------|-------|
| `0x1558` | `mActStatOld` | `uPlayer::ACT_STAT` | Was 4×undefined. SE has mActStatOld at 0x1a88. |
| `0x155c` | `mpActionTbl` | `unsigned int[2]` | Was 1B+7B undefined. Fixed to 8B (2 pointer slots). kActionTbl type doesn't exist in DX9 IDB. |
| `0x16ac` | `mActCtr` | `int` | Was 4×undefined. SE has mActCtr at 0x1c08. |
| `0x1e82` | `mWJumpCnt` | `char` | Was undefined. SE at 0x2490. |
| `0x1e83` | `mWallJumpCnt` | `char` | |
| `0x1e84` | `mWallHikeJumpCnt` | `char` | |
| `0x1e85` | `mNoDeath` | `bool` | |
| `0x1f3c` | `mIsProvoke` | `bool` | Was `member_0x1f38`. SE at 0x2548. Adjacent to mProvokeTimer@0x1f38. |

**SE-only fields not present in DX9 (DO NOT apply):**
- `mProvokeMtnDebugId`, `m_bExCostume`, `m_bExCostume2`, `mCostumeID` — DX9 has no costume system
- `mWeaponChangeRsrv` (SE 0x2488) — delta shifts at this point (+2), field is SE-only
- `mFallMoveRateXZ` (SE 0x2498) — delta shifts around 0x1e88; 0x1e88 in DX9 is a bool (confirmed by checkProvoke reading it as BYTE==1), not a float
- `mIsProvoke` was renamed correctly; SE's `mIsProvoke` and DX9's match by equal span

**Remaining undefined runs** (all confirmed alignment padding — SE has no named fields there either):
`0x1498-0x14a0`, `0x1513-0x1520`, `0x1551-0x1554`, `0x1730-0x1734`, `0x1dd0-0x1dd8`,
`0x1e2c-0x1e34`, `0x1e45-0x1e54`, `0x1e87`, `0x1e8e-0x1e8f`, `0x1ec8-0x1ed4`, `0x1f26-0x1f28`,
`0x1f3d-0x1f43`, `0x1f55-0x1f57`, `0x1f5c-0x1f63`, `0x1ff5-0x1ff7`, `0x200a-0x200b`,
`0x2010-0x2013`, `0x20a5-0x20a7`, `0x20b5-0x20b7`, `0x20bd-0x20c3`, `0x20cf`, `0x2170-0x2173`,
`0x2186-0x2193`, `0x2a3d-0x2a3f`, `0x2a5f`, `0x3068-0x3073`, `0x3268-0x3273`.
