# Enemy Class Hierarchy — DX9

Analysis date: 2026-07-03. All DTI globals emulated; sizes/parents are runtime-accurate.

> The **Game name** column was not derived from code and is unverified (e.g. uEm031 vs uEm029 for Agnus is disputed).

## Inheritance Chain

```
MtObject → cUnit → uCoord → uModel → uDevil4Model → uActor → uEnemy → uEm* / uEmAngelo
                                                              ↘ uEmAngelo → uEm005 / uEm006 / uEm022 / uEm023
```

Special sub-trees:
- `uEm000Base` inherits `uEnemy`; `uEm000` and `uEm001` and `uEm003` inherit `uEm000Base`
- `uEm008_009Base` inherits `uEnemy`; `uEm008` and `uEm009` inherit `uEm008_009Base`
- `uEm031` inherits `uEm016Ctrl`

## Class Roster — DX9 DTI globals

DX9 DTIs are at `0xE58xxx`; SE's are at `0x1492xxx`, so the addresses differ. Per-method SE→DX9 mapping, corrected vtable addresses and ctors: see `uem_se_dx9_map.md`.

| Class | DTI addr | Parent | alloc_size | Game name |
|-------|----------|--------|------------|-----------|
| `uEnemy` | `0xE596C8` | `uActor` | `0x1500` | base enemy |
| `uEm000` | `0xE589F8` | `uEm000Base` | `0x137F0` | Scarecrow (Bianco/Angelo) |
| `uEm000Base` | `0xE58A18` | `uEnemy` | `0x29E0` | Scarecrow base |
| `uEm001` | `0xE58A38` | `uEm000Base` | `0x10560` | Scarecrow (Alto) |
| `uEm003` | `0xE58A58` | `uEm000Base` | `0xB0F0` | Scarecrow (variant) |
| `uEm003Shl` | `0xE58A78` | *(shell)* | `0x17F0` | Scarecrow projectile |
| `uEm005` | `0xE58A98` | `uEmAngelo` | `0x5050` | Angelo Agnus / Credo Angelo |
| `uEm005GenkiShl` | `0xE58AD8` | *(shell)* | `0x18C0` | Angelo energy shot |
| `uEm006` | `0xE58AF8` | `uEm005` | `0x5070` | Angelo variant |
| `uEm006Coop` | `0xE58B18` | `uActor` | `0x1740` | Angelo coop sub-object |
| `uEm008` | `0xE58B38` | `uEm008_009Base` | `0x17D40` | Blitz |
| `uEm008_009Base` | `0xE58B58` | `uEnemy` | `0x26D0` | Blitz/Faust base |
| `uEm009` | `0xE58B78` | `uEm008_009Base` | `0x2E6E0` | Faust |
| `uEm009Shl` | `0xE58B98` | *(shell)* | `0x1C40` | Faust projectile |
| `uEm010` | `0xE58BB8` | `uEnemy` | `0x9D20` | Frost |
| `uEm010CrawShl` | `0xE58BD8` | *(shell)* | `0x17E0` | Frost claw shot |
| `uEm010Ice` | `0xE58BF8` | `uEnemy` | `0x1F70` | Frost ice field |
| `uEm010ShlCtrl` | `0xE58C18` | *(ctrl)* | `0x13F0` | Frost shot controller |
| `uEm010Warp` | `0xE58C38` | `uActor` | `0x13A0` | Frost warp effect |
| `uEm011` | `0xE58C58` | `uEnemy` | `0xB9F0` | Mephisto |
| `uEm011Shl` | `0xE58C78` | *(shell)* | `0x17C0` | Mephisto projectile |
| `uEm011Test` | `0xE58C98` | `uEnemy` | `0x4D80` | Mephisto (test variant) |
| `uEm012` | `0xE58CB8` | `uEnemy` | `0x2580` | Gladius |
| `uEm012Dodge` | `0xE58CD8` | `uActor` | `0x13D0` | Gladius dodge sub |
| `uEm012Shl` | `0xE58CF8` | *(shell)* | `0x18A0` | Gladius projectile |
| `uEm013` | `0xE58D18` | `uEnemy` | `0xA6F0` | Basilisk / Assaulter |
| `uEm013SeedJimen` | `0xE58D58` | `uActor` | `0x1380` | Basilisk ground seed |
| `uEm013SeedShell` | `0xE58D38` | *(shell)* | `0x2080` | Basilisk seed shell |
| `uEm014` | `0xE58D78` | `uEnemy` | `0xBD60` | Cutlass |
| `uEm015` | `0xE58D98` | `uEnemy` | `0xA280` | Mega-Scarecrow / Sloth |
| `uEm015Ctrl` | `0xE58E08` | `uEnemy` | `0x15D0` | Sloth controller |
| `uEm015::uEm015LeftBody` | — | — | — | Sloth left body part |
| `uEm016` | `0xE58E28` | `uEnemy` | `0x2200` | Chimera Assaulter |
| `uEm016Ctrl` | `0xE58E78` | `uEnemy` | `0x27C0` | Chimera controller |
| `uEm017` | `0xE58E98` | `uEnemy` | `0x8920` | Alto Angelo |
| `uEm017HeadShl` | `0xE58EB8` | *(shell)* | `0x1870` | Alto Angelo head shot |
| `uEm018` | `0xE58ED8` | `uEnemy` | `0x5BC0` | Sanctus Diabolica / Savior |
| `uEm018BreakHouse` | `0xE58F18` | `uStageSet` | `0x11180` | Savior breakable scenery |
| `uEm018FireShl` | `0xE58F38` | *(shell)* | `0x17E0` | Savior fire shot |
| `uEm019` | `0xE58F58` | `uEnemy` | `0x13FA0` | The Savior (main boss) |
| `uEm019_lure` | `0xE58F78` | `uActor` | `0x8C80` | Savior lure |
| `uEm019_string` | `0xE58F98` | `uActor` | `0x2470` | Savior string |
| `uEm019_00` | `0xE58FB8` | `uEnemy` | `0xC010` | Savior sub-form |
| `uEm019_00Shl` | `0xE58FD8` | *(shell)* | `0x1870` | Savior shot |
| `uEm019_00_Yoke` | `0xE58FF8` | `uActor` | `0x1850` | Savior yoke |
| `uEm019_hair` | `0xE59018` | `uActor` | `0x3570` | Savior hair |
| `uEm019_ice` | `0xE59038` | *(shell)* | `0x1870` | Savior ice |
| `uEm019ShlLand` | `0xE59058` | *(shell)* | `0x18D0` | Savior landing shot |
| `uEm021` | `0xE59098` | `uEnemy` | `0x25B0` | Bianco Angelo (mounted) |
| `uEm021_Snake` | `0xE59078` | `uEnemy` | `0x2CD0` | Bianco snake part |
| `uEm021_Leaf` | `0xE590D8` | `uEnemy` | `0x23D0` | Bianco leaf |
| `uEm021_Pipe` | `0xE590B8` | `uEnemy` | `0x1CC0` | Bianco pipe |
| `uEm021_Hand` | `0xE590F8` | `uEnemy` | `0x1BF0` | Bianco hand |
| `uEm021Shell` | `0xE59118` | `uEnemy` | `0x1BA0` | Bianco shell |
| `uEm022` | `0xE59158` | `uEmAngelo` | `0x4DB0` | Alto Angelo (combat) |
| `uEm022EngelShl` | `0xE59178` | *(shell)* | `0x1790` | Alto shell |
| `uEm022JavelinShl` | `0xE59198` | *(shell)* | `0x18D0` | Alto javelin |
| `uEm022SpearShl` | `0xE591B8` | `uEnemy` | `0x1990` | Alto spear |
| `uEm023` | `0xE591D8` | `uEmAngelo` | `0x6800` | Credo Angelo |
| `uEm023Shl` | `0xE591F8` | *(shell)* | `0x17C0` | Credo shot |
| `uEm023ShlCutlass` | `0xE59218` | *(shell)* | `0x1880` | Credo cutlass shot |
| `uEm023ShlGladius` | `0xE59238` | *(shell)* | `0x17C0` | Credo gladius shot |
| `uEm025` | `0xE59258` | `uEnemy` | `0x4460` | Berial |
| `uEm025Core` | `0xE59278` | `uEnemy` | `0x1A00` | Berial core |
| `uEm025Shl00`–`Shl04` | — | *(shells)* | ~`0x18xx` | Berial projectiles |
| `uEm026` | `0xE59378` | `uEnemy` | `0x30C0` | Bael / Dagon |
| `uEm027` | `0xE59398` | `uEnemy` | `0x12010` | Echidna |
| `uEm029` | `0xE593D8` | `cPopeCommon` | `0x18A60` | Agnus boss |
| `uEm030` | `0xE593F8` | `cPopeCommon` | `0x1E150` | Gloria boss |
| `uEm030GroundCtrl` | `0xE59438` | `uActor` | `0x1820` | Ground ctrl sub |
| `uEm030GroundParts` | `0xE59458` | `uActor` | `0x1390` | Ground parts sub |
| `uEm030Shl` | `0xE59478` | *(shell)* | `0x18A0` | Gloria shot |
| `uEm030Spada` | `0xE59498` | `uEnemy` | `0x1A60` | Gloria spada |
| `uEm031` | `0xE594D8` | `uEm016Ctrl` | `0x44B0` | Credo (boss) |
| `uEm032` | `0xE594F8` | `uEnemy` | `0x21B0` | Sanctus (human) |
| `uEm032BitCtrl` | `0xE59518` | `uActor` | `0x13E0` | Sanctus bit ctrl |
| `uEm033` | `0xE59538` | `uEnemy` | `0x1BF0` | Nelo Angelo (SE-equivalent?) |
| `uEm033Shl` | `0xE59558` | *(shell)* | `0x17B0` | shot |
| `uEm035` | `0xE59578` | `uEnemy` | `0x8C40` | Dante (boss fight) |
| `uEm036` | `0xE59598` | `uEnemy` | `0xF2D0` | Nero (boss?) / outro enemy |
| `uEmAngelo` | `0xE595D8` | `uEnemy` | `0x3890` | Angelo archetype base |
| `uEmAppear` | `0xE595F8` | `uCoord` | `0xF0` | Appear effect |
| `uEmBombShl` | `0xE59618` | *(shell)* | `0x1F80` | Generic bomb shell |
| `uEmPushShl` | `0xE59638` | *(shell)* | `0x17A0` | Generic push shell |
| `uEmRange` | `0xE59658` | `cUnit` | `0xF0` | Range trigger |
| `uEmSample` | `0xE596A8` | `uEnemy` | `0x20E0` | Debug/sample enemy |

**Note on `uEm002`**: A class name string `uEm002` exists in the binary (addr `0xBCEFC4`) but no `getDTI` function or vtable was found — this class appears to be unused/removed in the shipped binary.

## `uEnemy` vtable layout (84 slots, addr `0xBD91F0`)

Key slots (comparison against `uActor`/`uDevil4Model`/`uModel` baseline):

| Slot | Offset | Function | Role |
|------|--------|----------|------|
| 0 | +0x00 | `loc_72FA80` | destructor |
| 1 | +0x04 | `sub_718C00` | shared alloc stub |
| 2 | +0x08 | `cUnit::isEnable` | inherited |
| 3 | +0x0C | `sub_72FCC0` | `createProperty` |
| 4 | +0x10 | `uEnemy::getDTI` | returns `uEnemy::DTI` |
| 5 | +0x14 | `uEnemy::setup` | init from create-data (quaternion, position) |
| 6 | +0x18 | `uEnemy::move` | per-frame tick (calls `uActor::move`) |
| 7 | +0x1C | `nullsub_2` | draw (null — subclass overrides) |
| 8 | +0x20 | `nullsub_2` | draw_shadow? (null) |
| 9 | +0x24 | `nullsub_1` | slot9 (null) |
| 10 | +0x28 | `uModel::getBoundary` | inherited |
| 11 | +0x2C | `uModel::getName` | inherited |
| 12 | +0x30 | `sub_72FB50` | **kill/die** — clears state pointers at +5248/+5252/+5188, transitions unit flags |
| 13–29 | | `uModel`/`uDevil4Model` methods | inherited (matrix/material/camera-transparency) |
| 30 | +0x78 | `nullsub_2` | **main (behaviour)** — null at enemy base, overridden per-class |
| 31 | +0x7C | `sub_72FAC0` | **validate-target pointers** — nulls stale `uActor*` cached refs at +5248,+5252,+5184 if unit is dead |
| 32 | +0x80 | `uActor::getCenterPos2` | inherited |
| 33 | +0x84 | `uActor::getCenterPos` | inherited |
| 34 | +0x88 | `sub_7A56B0` | getTargetPos? (shared with `uPlayer`) |
| 35 | +0x8C | `uActor::getPullType` | inherited |
| 36–39 | +0x90–0x9C | `nullsub_3` | attack-type callbacks (all null at base) |
| 40 | +0xA0 | `nullsub_8` | |
| 41 | +0xA4 | `nullsub_1` | |
| 42–43 | +0xA8–0xAC | `nullsub_8` | |
| 44 | +0xB0 | `nullsub_3` | |
| 45 | +0xB4 | `sub_603780` | shared (uActor-level?) |
| 46–50 | +0xB8–0xC8 | `nullsub_8`/`nullsub_3` | |
| 51 | +0xCC | `uPlayer::hitStopMessage` | **hitStop handler** — inherited from uPlayer namespace (shared impl) |
| 52 | +0xD0 | `sub_735010` | `setHitStop(int)` — writes `+5172` |
| 53 | +0xD4 | `sub_735030` | related hitStop |
| 54 | +0xD8 | `nullsub_3` | |
| 55 | +0xDC | `uEnemy::grabMessage` | grab message handler |
| 56 | +0xE0 | `nullsub_3` | |
| 57 | +0xE4 | `nullsub_9` | |
| 58 | +0xE8 | `nullsub_2` | |
| 59 | +0xEC | `sub_521BF0` | (`uDevil4Model` method) |
| 60–63 | +0xF0–0xFC | `nullsub_3`/`nullsub_9` | |
| 64 | +0x100 | `sub_7334C0` | **damageMessage** — dispatch on damage type; locates nearest collision sub-joint, routes to vtable sub-handlers |
| 65 | +0x104 | `sub_733950` | **damageMessage2** — handles HP-threshold death burst (calls vtable+0x18C = slot 99?) |
| 66 | +0x108 | `sub_734490` | damageMessage3 |
| 67 | +0x10C | `sub_7345B0` | damageMessage4 |
| 68 | +0x110 | `sub_7346B0` | damageMessage5 |
| 69 | +0x114 | `nullsub_8` | |
| 70 | +0x118 | `sub_734990` | damageMessage6 |
| 71 | +0x11C | `uActor::SEMessage` | inherited SE (sound effect) message |
| 72 | +0x120 | `nullsub_8` | |
| 73 | +0x124 | `uActor::setHomingAngleXY` | inherited |
| 74 | +0x128 | `uActor::isMotionEnd` | inherited |
| 75 | +0x12C | `uActor::isMotionEndAll` | inherited |
| 76 | +0x130 | `uActor::getEffectElementMessage` | inherited |
| 77 | +0x134 | `sub_718870` | shared (uModel-level?) |
| 78 | +0x138 | `sub_455A90` | |
| 79 | +0x13C | `sub_455AA0` | **respawn/relocate** — called from `uEnemy::move` when Y distance > 50000 |
| 80 | +0x140 | `sub_735FB0` | |
| 81–83 | +0x144–0x14C | `sub_455AB0` | |

## `uEnemy` field layout (offsets from struct base)

Derived from constructor `uEnemy::uEnemy` @ `0x72F890` cross-referenced against SE PDB struct (61 named members).
Verified: all 19 ctor write sites match the declared offsets. Total size `0x1500`; own fields span `0x1370`–`0x14FF`.
Declared in IDA Local Types as `struct uEnemy : uActor { ... }`.

Base chain sizes: `uCoord=0xE0`, `uModel=0xCF0`, `uDevil4Model=0xEA0`, `uActor=0x1370`.

| Offset (abs) | uEnemy+  | Type | Name | Notes |
|--------------|----------|------|------|-------|
| `0x1370` | `+0x0000` | `cEnemyCreateData` | `mEnemyCreateData` | 0x90 bytes embedded |
| `0x1400` | `+0x0090` | `uEnemySetCtrl*` | `mpEnemySetCtrl` | |
| `0x1404` | `+0x0094` | `bool` | `mBattle` | init=1 |
| `0x1405` | `+0x0095` | `bool` | `mActive` | init=1 |
| `0x1406` | `+0x0096` | `bool` | `mAutoKill` | init=1 |
| `0x1408` | `+0x0098` | `float` | `mAutoKillTimer` | |
| `0x140C` | `+0x009C` | `int` | `mEnemyLv` | |
| `0x1410` | `+0x00A0` | `uint` | `mEnemyID` | ENEMY_ID enum |
| `0x1414` | `+0x00A4` | `uint` | `mBloodGroup` | ENEMY_BLOOD_GROUP enum |
| `0x1418` | `+0x00A8` | `kEmDamageEffect*` | `mpEmDamageEffect` | init=0 |
| `0x141C` | `+0x00AC` | `void*` | `mpDamageNearestBone` | uModel::Joint* |
| `0x1420` | `+0x00B0` | `MtMath::MtVector3` | `mShrinkHitPos` | 0x10 bytes |
| `0x1430` | `+0x00C0` | `int` | `mHitBone` | |
| `0x1434` | `+0x00C4` | `float` | `mEmHitStopTimer` | init=0 |
| `0x1438` | `+0x00C8` | `bool` | `mEmHitStop` | init=0 |
| `0x143C` | `+0x00CC` | `int` | `mParasiteNum` | init=0 |
| `0x1440` | `+0x00D0` | `uEm014*` | `mpParasiteEm014` | init=0 |
| `0x1444` | `+0x00D4` | `uEmAppear*` | `mpEmAppear` | init=0 |
| `0x1448` | `+0x00D8` | `cEmAppearMove` | `mEmAppearMove` | 0x14 bytes; vtable written by ctor |
| `0x145C` | `+0x00EC` | `bool` | `mEffCheckCameraRange` | |
| `0x1460` | `+0x00F0` | `float` | `mEffCheckCameraRangeMiddle` | init=1000.0f |
| `0x1464` | `+0x00F4` | `float` | `mEffCheckCameraRangeFar` | init=2000.0f |
| `0x1468` | `+0x00F8` | `bool` | `mGrapTrish` | init=0 |
| `0x1469` | `+0x00F9` | `bool` | `mGrapTrish_Air` | init=0 |
| `0x1470` | `+0x0100` | `MtMath::MtVector3` | `mLockOnTargetPos` | 0x10 bytes |
| `0x1480` | `+0x0110` | `uDevil4Effect*` | `mpDTEff` | init=0 |
| `0x1484` | `+0x0114` | `uDevil4Effect*` | `mpDTSignEff` | init=0 |
| `0x1488` | `+0x0118` | `float` | `mDevilTriggerTimer` | init=-1.0f |
| `0x148C` | `+0x011C` | `bool` | `mDevilTriggerOK` | init=0 |
| `0x148D` | `+0x011D` | `bool` | `mDevilTriggerTimerEnable` | init=1 |
| `0x148E` | `+0x011E` | `bool` | `mDevilTrigger` | init=0 |
| `0x148F` | `+0x011F` | `bool` | `mDevilTriggerSign` | init=0 |
| `0x1490` | `+0x0120` | `float` | `mFloatMoveAngleMax` | |
| `0x1494` | `+0x0124` | `float` | `mFloatMoveAngleSpd` | |
| `0x1498` | `+0x0128` | `float` | `mFloatMoveAddSpd` | |
| `0x149C` | `+0x012C` | `float` | `mFloatMoveSubSpd` | |
| `0x14A0` | `+0x0130` | `float` | `mFloatMoveWaitTime` | |
| `0x14A4` | `+0x0134` | `float` | `mFloatMoveWaitTimer` | |
| `0x14A8` | `+0x0138` | `float` | `mFloatMoveStopRnage` | sic (SE typo preserved) |
| `0x14AC` | `+0x013C` | `float` | `mFloatMoveSubSpdRange` | |
| `0x14B0` | `+0x0140` | `bool` | `mbFloatMoveAdd` | |
| `0x14B1` | `+0x0141` | `bool` | `mTargetEnemyPlayer` | |
| `0x14B2` | `+0x0142` | `bool` | `mRaundTripHit` | sic (SE typo) |
| `0x14B4` | `+0x0144` | `float` | `mRaundTripHitresetTimer` | |
| `0x14B8` | `+0x0148` | `bool` | `mV_DividerHit` | init=0 |
| `0x14BC` | `+0x014C` | `float` | `mV_DividerHitresetTimer` | |
| `0x14C0` | `+0x0150` | `uint` | `mHitEffNum` | init=0 |
| `0x14C4` | `+0x0154` | `uActor*` | `mpTargetEnemy` | init=0; validated by slot 31 |
| `0x14D0` | `+0x0160` | `MtMath::MtVector3` | `mTgtPos` | 0x10 bytes; zero init |
| `0x14E0` | `+0x0170` | `float` | `mTgtLeng` | |
| `0x14E4` | `+0x0174` | `float` | `mTgtXZLeng` | |
| `0x14E8` | `+0x0178` | `float` | `mTgtHeight` | |
| `0x14EC` | `+0x017C` | `float` | `mTgtKakudo` | |
| `0x14F0` | `+0x0180` | `MtMath::MtVector3` | `mGrabLongGravity` | 0x10 bytes; last field |

DX9 does **not** have SE's trailing fields (`mEnemyEffectType`, `mVergilAirTrickTimer`, `mMotionSeqPrev`, `mEnableStabSword`, `mPushShlTimer`) — SE `uEnemy` is `0x1A50` (own=`0x1D0`) vs DX9 `0x1500` (own=`0x190`).

uActor fields written by `uEnemy::uEnemy` (not part of uEnemy's own range):
- `uActor+0x0CF8` (`mActorType`?) = 21
- `uActor+0x0EA4` (`mActorType`) = 3

## `uEnemy::move` key behaviour

1. Calls `cWorkRate::tick` on embedded workrate object (`this->mWorkRate`)
2. Updates hit-stop timer at `+0x14AC` (float) via `sDevil4Main::mpInstance->mDeltaTime`
3. Handles turbo mode scaling via `sMediator::mpInstance->mTurboMode` / `mTurboCancel`
4. References `sMediator::mpInstance->mGameDifficulty` and `mMissionNo` for Bloody Palace (BP) Berserk check
5. Reads `sMediator::mpInstance->mSecretMissionFlag`
6. Validates cached actor pointer at `+0x1290` (cleared if unit is dead)
7. Calls `uActor::move(this)` for base tick
8. Decrements two cooldown floats at `+0x14D5` and `+0x14D6` (×4 = `+0x1534`, `+0x1538`)
9. Y-distance-to-player check: if `|enemy.mPos.y - player.mPos.y| > 50000`, accumulates and calls vtable slot 79 (relocate)
10. All player access goes through `sMediator::mpInstance->mpPlayer` — single-player assumption

## Vtable override pattern (compared to `uEnemy` baseline)

Legend: `OVR` = class overrides this slot, blank = inherits uEnemy's impl.

```
Class          |setup|move|draw|s8|s9|s12|main|s31|s34|s36|s37|s40|s41|s44|s47|s48|s49|s50|hitSt|grab|s57|s58|d1|d2|d3|d4|d5|d6|s77|s79
uEm000         | OVR | -- | OVR|OV|OV|OVR|OVR|OVR|OVR|OVR|OVR|-- |OVR|OVR|OVR|OVR|OVR|-- |-- |-- |-- |OVR|--|--|--|--|--|--|OVR|OVR
uEm000Base     | OVR | -- | OVR|OV|OV|OVR|OVR|OVR|OVR|OVR|OVR|-- |OVR|OVR|OVR|OVR|OVR|-- |-- |-- |-- |OVR|--|--|--|--|--|--|OVR|OVR
uEm001         | OVR | -- | OVR|OV|OV|OVR|OVR|OVR|OVR|OVR|OVR|-- |OVR|OVR|OVR|OVR|OVR|-- |-- |-- |-- |OVR|--|--|--|--|--|--|OVR|OVR
uEm003         | OVR | -- | OVR|OV|OV|OVR|OVR|OVR|OVR|OVR|OVR|-- |OVR|OVR|OVR|OVR|OVR|-- |-- |-- |-- |OVR|--|--|--|--|--|--|OVR|OVR
uEm005 (Angelo)| OVR |OVR | -- |--|--|OVR|OVR|-- |-- |-- |-- |-- |-- |-- |-- |-- |-- |OVR|OVR|OVR|OVR|OVR|OV|OV|OV|OV|OV|OV|OVR|OVR
uEm006         | OVR | -- | OVR|OV|OV|OVR|OVR|OVR|OVR|OVR|OVR|-- |-- |OVR|OVR|OVR|OVR|-- |-- |-- |-- |OVR|--|--|--|--|--|--|OVR|OVR
uEm008 (Blitz) | OVR | -- | OVR|OV|OV|OVR|OVR|OVR|OVR|-- |OVR|OVR|-- |-- |OVR|OVR|OVR|-- |OVR|OVR|OVR|OVR|OV|OV|OV|OV|OV|OV|OVR|OVR
uEm009 (Faust) | OVR | -- | OVR|OV|OV|OVR|OVR|OVR|OVR|-- |OVR|OVR|-- |-- |OVR|OVR|OVR|-- |OVR|OVR|OVR|OVR|OV|OV|OV|OV|OV|OV|OVR|OVR
uEm010 (Frost) | OVR | -- | OVR|OV|OV|OVR|OVR|OVR|OVR|OVR|OVR|-- |OVR|-- |OVR|OVR|OVR|OVR|-- |-- |-- |OVR|--|--|--|--|--|--|OVR|OVR
uEm011(Mephisto)| OVR| -- | OVR|OV|OV|OVR|OVR|OVR|OVR|OVR|OVR|-- |OVR|OVR|OVR|OVR|OVR|OVR|--|-- |--|OVR|--|--|--|--|--|--|OVR|OVR
uEm012(Gladius) | OVR| -- | OVR|OV|OV|OVR|OVR|OVR|OVR|OVR|-- |OVR|OVR|-- |OVR|OVR|OVR|OVR|OVR|--|--|OVR|--|--|--|--|--|--|OVR|OVR
uEm013(Basilisk)| OVR| -- | OVR|OV|OV|OVR|OVR|OVR|OVR|OVR|OVR|-- |-- |-- |OVR|OVR|OVR|--|--|--|--|OVR|--|--|--|--|--|--|OVR|OVR
uEm014(Cutlass) | OVR| -- | OVR|OV|OV|OVR|OVR|OVR|OVR|-- |-- |-- |OVR|OVR|OVR|OVR|OVR|OVR|OVR|--|--|OVR|OV|OV|OV|OV|OV|OV|OVR|--
uEm015(Sloth)   | OVR|OVR | -- |--|OV|OVR|OVR|OVR|OVR|OVR|OVR|-- |-- |-- |-- |-- |-- |--|--|--|--|--|--|--|--|--|--|--|--|--
uEm016(Chimera) | OVR| -- | OVR|OV|OV|OVR|OVR|OVR|OVR|-- |OVR|OVR|-- |OVR|OVR|OVR|OVR|OVR|OVR|OVR|OVR|OVR|OV|OV|OV|OV|OV|OV|OVR|OVR
uEm017(AltAnglo)| OVR| -- | OVR|OV|OV|OVR|OVR|-- |OVR|OVR|-- |-- |OVR|-- |OVR|OVR|OVR|--|--|--|--|OVR|--|--|--|--|--|--|OVR|OVR
uEm018(Sanctus) | OVR| -- | OVR|--|OV|OVR|OVR|-- |-- |-- |OVR|-- |OVR|-- |-- |OVR|--|--|--|--|--|OVR|--|--|--|--|--|--|OVR|OVR
uEm019(Savior)  | OVR| -- | OVR|OV|OV|OVR|OVR|-- |OVR|-- |OVR|-- |OVR|OVR|-- |OVR|--|--|--|--|--|OVR|--|--|--|--|--|--|OVR|--
uEm022(AltAnglo2)| OVR|OVR|OVR|OV|OV|OVR|OVR|OVR|OVR|OVR|OVR|OVR|OVR|OVR|OVR|OVR|OVR|OVR|OVR|OVR|OVR|OVR|OV|OV|OV|OV|OV|OV|OVR|OVR
uEm023(CredoAng)| OVR| -- | OVR|OV|OV|OVR|OVR|OVR|OVR|-- |OVR|-- |OVR|OVR|OVR|OVR|OVR|OVR|OVR|OVR|OVR|OVR|OV|OV|OV|OV|OV|OV|OVR|OVR
uEm025(Berial)  | OVR| -- | OVR|OV|OV|OVR|OVR|OVR|OVR|-- |OVR|-- |OVR|-- |-- |OVR|--|--|--|--|--|OVR|--|--|--|--|--|--|OVR|OVR
uEm026(Bael)    | OVR| -- | OVR|--|OV|OVR|OVR|-- |-- |-- |OVR|OVR|-- |OVR|-- |-- |--|--|--|--|--|OVR|--|--|--|--|--|--|OVR|--
uEm027(Echidna) | OVR|OVR | -- |OV|OV|OVR|OVR|OVR|OVR|OVR|OVR|OVR|OVR|OVR|OVR|OVR|OVR|OVR|OVR|OVR|OVR|OVR|OV|OV|OV|OV|OV|OV|OVR|OVR
uEm029(Agnus)   | OVR| -- | OVR|OV|OV|OVR|OVR|-- |OVR|OVR|-- |OVR|-- |OVR|-- |OVR|--|--|--|--|--|OVR|--|--|--|--|--|--|OVR|OVR
uEm030(Gloria)  | OVR| -- | OVR|OV|OV|OVR|OVR|-- |OVR|OVR|-- |OVR|-- |OVR|-- |OVR|--|--|--|--|--|OVR|--|--|--|--|--|--|OVR|OVR
uEm031(Credo)   | OVR|OVR | -- |OV|OV|OVR|--|  |-- |-- |-- |-- |-- |-- |-- |-- |--|--|--|--|--|--|--|--|--|--|--|--|--|--
uEm032(Sanctus2)| OVR| -- | OVR|--|OV|OVR|OVR|-- |OVR|--|OVR|-- |OVR|-- |OVR|OVR|OVR|--|OVR|--|--|--|--|--|--|--|--|--|--|--
uEm033          | OVR| -- | OVR|OV|OV|OVR|OVR|-- |-- |-- |-- |-- |-- |-- |-- |-- |--|--|--|--|--|--|--|--|--|--|--|--|--|--
uEm035(DanteBoss)| OVR| -- | OVR|--|OV|OVR|OVR|-- |-- |-- |OVR|-- |OVR|OVR|-- |OVR|--|--|--|--|--|--|--|--|--|--|--|--|--|--
uEm036          | OVR| -- | OVR|OV|OV|OVR|OVR|-- |-- |-- |OVR|-- |OVR|-- |OVR|OVR|OVR|OVR|OVR|--|--|OVR|--|--|--|--|--|--|OVR|--
```

## Key observations

### `uEmAngelo` archetype (`uEm005`, `uEm006`, `uEm022`, `uEm023`)
- Angelo enemies override `move` (slot 6) unlike most enemies — they have their own per-frame logic rather than using `uEnemy::move`.
- They all override slots 36–41 (attack-type callbacks) which most other enemies leave null.
- Heavy combat message overrides (slots 64–70).

### Scarecrow group (`uEm000`, `uEm000Base`, `uEm001`, `uEm003`)
- All share identical override pattern — `uEm000Base` carries the implementation, `uEm000`/`uEm001`/`uEm003` refine it.
- Override slot 37 (attack-back callback?) and slot 40.
- `uEm000::alloc_size = 0x137F0` (~79KB) — largest in the roster by far, suggesting complex internal state.

### Large bosses (`uEm019` Savior, `uEm029` Agnus, `uEm030` Gloria)
- `uEm019` alloc = `0x13FA0` (~81KB)
- `uEm029` alloc = `0x18A60` (~100KB)
- `uEm030` alloc = `0x1E150` (~123KB) — largest overall
- `uEm029`/`uEm030` inherit `cPopeCommon` (DTI `0xE57350`, parent `uEnemy`, size `0x28A0`; not covered by the DTI emulation pass).

### `uEm031` (Credo boss)
- Inherits `uEm016Ctrl` (Chimera controller), not `uEnemy` directly.
- Only overrides slots 0,3,4,5,6,7,8,9 — very minimal; relies heavily on `uEm016Ctrl` implementation.
- `alloc_size = 0x44B0` — compact for a boss.

### Slot 51 (`hitStopMessage`)
- Points to `uPlayer::hitStopMessage` (`0x7AE350`) — shared implementation between players and enemies for hit-stop response.
- Most enemies inherit this; some override with class-specific hit-stop behaviour.

### Slot 31 (`sub_72FAC0` — validate-target pointers)
- Nulls out stale `uActor*` cached refs at `+0x1480`, `+0x1484`, `+0x1444`, `+0x1400` when the pointed-to units are no longer alive (state bits `& 7 != 1 and != 2`).
- `sMediator` refactor relevance: these cached `uActor*` pointers include player references — each would become `uPlayer*[player_index]` lookups.

### Slot 12 (`sub_72FB50` — die/kill)
- Clears dynamic pointers at `+0x1494`, `+0x149C`, `+0x143C` (appear-move controllers).
- Transitions unit state flag at `+0x04` bits 0–2 → `3` (dead).

## Named DX9 methods on `uEnemy`

| Function | Addr | Purpose |
|----------|------|---------|
| `uEnemy::getDTI` | `0x72F860` | returns `&uEnemy::DTI` |
| `uEnemy::uEnemy` | `0x72F890` | constructor |
| `uEnemy::setup` | `0x72FDC0` | init from create-data; computes quaternion from orientation matrix; reads `sMediator::mpInstance->mpPlayer` for facing dir |
| `uEnemy::move` | `0x7308B0` | per-frame tick; references `sMediator`, `sDevil4Main`, `sArea` |
| `uEnemy::grabMessage` | `0x734EE0` | grab interaction handler |
| `uEnemy::setPushShlEx` | `0x735270` | spawn push shell |
| `uEnemy::setBombShl` | `0x735370` | spawn bomb shell |
| `uEnemy::initGrabLong` | `0x735400` | initialize long grab state |
| `uEnemy::getTargetEnemyPos` | `0x7360C0` | query target enemy position |

## Named DX9 methods on `uEm010` (Frost — most complete)

| Function | Addr | Purpose |
|----------|------|---------|
| `uEm010::getDTI` | `0x5A3E30` | |
| `uEm010::newInstance` | `0x5A3F60` | factory — `new uEm010()` |
| `uEm010::uEm010` | `0x5A3F90` | constructor: embeds `uDamage`, `uMotionSE`, `uCollisionMgr`, `cLockOnTarget`×2, `cThinkMgr`, `cActionMgr`, `cFootprintCtrl`×2, `kMdlHead`, 7×animation slots, ice-related structs |
| `uEm010::setMotion` | `0x5A54F0` | |
| `uEm010::setAction` | `0x5A5990` | |
| `uEm010::main` | `0x5A5A90` | behaviour at vtable slot 30 |
| `uEm010::appear` | `0x5A66D0` | |
| `uEm010::jumpAppear` | `0x5A6790` | |
| `uEm010::setGrabThrow` | `0x5AA660` | setup grab throw |
| `uEm010::grabThrow` | `0x5AA700` | execute grab throw |
| `uEm010::checkGrabThrowHit` | `0x5AAB20` | |
| `uEm010::setGrabThrowBlown` | `0x5AAE80` | |
| `uEm010::grabThrowBlown` | `0x5AAEE0` | |
| `uEm010::setGrabThrowBlownShort` | `0x5AB130` | |
| `uEm010::grabThrowBlownShort` | `0x5AB190` | |
| `uEm010::grabBlown` | `0x5AA280` | |
| `uEm010::setRecoverHand` | `0x5498D0` | |
| `uEm010::setAttackIceMC` | `0x58C770` | |
| `uEm010::setAttackIceShooter` | `0x58C8E0` | |
| `uEm010::setGrabBlown` | `0x5D5420` | |
| `uEm010::setAttackNailRecover` | `0x5D6CC0` | |

## `sMediator` coupling in enemy classes

`uEnemy::move` accesses `sMediator::mpInstance` for:
- `->mpPlayer` — target player position (single-player assumption)
- `->mMissionNo` — mission number (BP check)
- `->mGameDifficulty` — difficulty level (Berserk on DMD = 3)
- `->mSecretMissionFlag` — secret mission active
- `->mTurboMode` / `->mTurboCancel` — turbo mode timing

`uEnemy::setup` accesses:
- `->mpPlayer` — initial facing direction

All grab message / damage dispatch paths ultimately resolve the attacking player via `sMediator` or through the damage packet's `uActor*` back-reference.

For multiplayer refactor: the `->mpPlayer` dereferences in `uEnemy::move` and `::setup` need to become `->mpPlayer[nearest_player_index]` or target-locked lookups, since each enemy independently targets one player.
