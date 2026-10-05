# sDevil4Pad / sPad — struct layout & multiplayer blocker

DX9 target. Sizes from DTI `mSizeAndPage`, offsets from constructor writes, names from SE PDB
(re-verified against DX9 code — DX9 is a cut-down version of the SE layout).

## Class hierarchy / sizes

| Class | DTI | Parent | Size | Ctor |
|---|---|---|---|---|
| `sPad` | `0xEAD4E0` | `cSystem` | 0x5D0 | `sPad::sPad` `0x8E3D60` (stdcall this) |
| `sPad::Pad` | `0xEAD520` | `MtObject` | 0x2C0 | `sPad::Pad::Pad` `0x8E2350` |
| `sPad::Map` | `0xEAD500` | `MtObject` | 0x12C | `sPad::Map::Map` `0x8E3A10` (embedded, no vtable write of its own) |
| `sDevil4Pad` | `0xE57E58` | `sPad` | 0x9E8 | `sDevil4Pad::sDevil4Pad` `0x484CF0` (esi=this) |
| `sDevil4Pad::cPadInfo` | `0xE57E78` | `MtObject` | 0x200 | inlined in `sDevil4Pad` ctor |

Singleton: `sDevil4Pad::mpInstance` `0xE559C4` (written inside `sPad::sPad`, now typed `sDevil4Pad*`).

## sPad (0x5D0) — `struct sPad : cSystem`

| Off | Field | Notes |
|---|---|---|
| 0x000 | `cSystem` (vftable, `mCS`, `mThreadSafe`@0x1C) | |
| 0x020 | `bool mActive` | gate in `readPad` |
| 0x028 | `u64 mPrevTimer` | |
| 0x030 | `u32 mDeltaTime` | |
| 0x034 | `sPad::Pad mPad[2]` | **2** physical slots (SE: 4); stride 0x2C0 |
| 0x5B4 | `u32 mDecideButton` | init 0x4000 (`DECIDE_Abutton`) |
| 0x5B8 | `bool mXInput` | set if OS ≥ XP (VerifyVersionInfo) |
| 0x5B9 | `bool mResetJoyPad` | |
| 0x5BC | `IDirectInput8A* mpDInput` | |
| 0x5C0 | `IDirectInputDevice8A* mpJoystick[2]` | indexed by `Info.Socket_no` |
| 0x5C8 | `int mTickTimer[2]` | init -1024; `open` re-probe throttle (1000 ms) |

DX9 lacks SE's `mSysRepeadStDefault/NxDefault` and `mCancelButton`.

## sPad::Pad (0x2C0)

| Off | Field | Notes |
|---|---|---|
| 0x000 | `__vftable` | |
| 0x004 | `PAD_INFO Info` | `Kind` @+0x7 is `sPad::KIND` (u8), `Socket_no` @+0x10 |
| 0x014 | `PAD_FREE Free` | deadzones |
| 0x01A | `PAD_REPEAT Repeat` | |
| 0x050 | `PAD_VIB Vib` | |
| 0x15C | `PAD_DATA Data` | raw On/Old/Trg/Rel/Chg/Rep, sticks, triggers |
| 0x188 | `bool mTriggerVibLow / mTriggerVibHigh` | |
| 0x18A | `u16 mVibStartValue / mVibEndValue / mVibTime` | |
| 0x190 | `sPad::Map mMap` | |
| 0x2BC | `u8 mRequestVib` | `sPad::Pad::REQUEST_VIB` (1 = STOP written by `move`) |

DX9 has no `mToolData`.

## sPad::Map (0x12C)

`__vftable` / `DIJOYSTATE2 mJS` @0x4 (filled by `GetDeviceState(0x110)` in `readPad`) /
`u8 mMap[20]` @0x114 (DX9 has 20 = `MAP_A..MAP_RSTICK_HORZ`, SE has 32) / `u32 mTriggerType` @0x128.

## sDevil4Pad::cPadInfo (0x200)

`__vftable`, `sPad::Pad* mpPad`@4, `mIsEnable`@8, `mIsVibEnable`@9, `mIsFake`@0xA, `mDecideBtn`@0xC,
`mCancelBtn`@0x10, `kBtnInfo mBtn`@0x14, `kAnlgInfo mAnlg[2]`@0x24, `kPressInfo mPress`@0x34,
`kSensorInfo mSensor`@0x70, `kVibInfo mVibInfo[16]`@0x80. (SE's trailing vib-curve floats are absent.)

## sDevil4Pad (0x9E8) — `struct sDevil4Pad : sPad`

| Off | Field |
|---|---|
| 0x5D0 | `cPadInfo mPadInfo[2]` |
| 0x9D0 | `int mUserPadId` |
| 0x9D4 | `bool mIsFixUserPadId` |
| 0x9D5 | `bool mOldActive` (app-active last frame) |
| 0x9D8 | `u64 mPrevTimer` (0x9D6–7 alignment pad) |
| 0x9E0 | `u32 mDeltaTime` (was mistyped `float`; it's an int ms delta fed to `tick_vib_info`) |

0x9E4–0x9E7 is tail padding (8-byte alignment from the u64). There are no accesses to 0x9D6/7/0x9E4 in any of the 151 pad-related functions.

## KIND (DX9-specific)

`sPad::Pad::open_xinput` (`0x8E48E0`) sets `Kind` = index into table `0xE16B20` whose entries hold `XINPUT_CAPABILITIES.SubType`:
3→sub 1 (gamepad), 4→sub 3 (arcade), 5→0, 6→sub 2 (wheel), 7→0. `Kind==2` = DirectInput (`readPad` uses `mpJoystick`).
Declared as `KIND_NONE/UNKNOWN/JOYPAD/X360PAD/ARCADE_STICK/kind_xinput_5/WHEEL/kind_xinput_7`; this ordering differs from SE.

---

## Where the single-player constraint lives

Hardware layer is already **2-pad capable** (`mPad[2]`, `mpJoystick[2]`, `mPadInfo[2]`, per-slot `open`/`readPad`/`moveVib`).
The constraint is entirely in the logical layer, at three levels:

### 1. Producer — `sDevil4Pad::move` (`0x485050`)
Only `mPadInfo[0]` is ever written:
- `mIsFixUserPadId == 1`: checks `mPad[mUserPadId]` is live, then `cPadInfo::update(&mPadInfo[0])`, which reads `mPadInfo[0].mpPad`.
- `mIsFixUserPadId == 0`: **ORs every live pad** (`Data.On/Trg/Rel/Rep`) into `mPadInfo[0].mBtn` and sets `mIsFake`. Two controllers become one.
- `mPadInfo[1]` is constructed (`mpPad = &mPad[1]`) but never updated.

### 2. Selection — one claimed pad ("press START")
Writers of `mUserPadId`:
- `sDevil4Pad::claim_user_pad_on_start` (`0x485320`, called from `uTitle::waitStart`): first live `mPad[i]` with `Data.Trg & 8` (START) →
  `mUserPadId=i; mIsFixUserPadId=1; mPadInfo[0].mpPad=&mPad[i]`. **This join mechanism is the model for N-player join.**
- `aGame::game_start_init` (`0x4041E0`, aGame vslot 6): fallback, used only if no pad was claimed → pad 0.
- `sDevil4Pad::reset` (`0x485040`, vslot 5) → unclaims (`mIsFixUserPadId=0`, `mUserPadId=0`).

Reader: `sDevil4Pad::get_user_pad_id` (`0x485380`) returns the claimed id, or the first live pad. It is used by `aRoom::init`, `aRoom::pauseInChk`, `sub_49A970` and `checkRestrainSleepWindowsOS` to index `mPadInfo[]`. Since `[1]` is never filled, those reads are only correct for id 0.
The SE `mDebugPadId` and `m_PadID` fields are not present.

### 3. Consumers — offsets hardcoded to `mPadInfo[0]`

#### `mpInstance` xref audit (complete)
Per-function data is in `RE/sdevil4pad_mpinstance_xrefs.json` (script: `RE/scripts/sdevil4pad_xref_audit.py`, which uses the Hex-Rays ctree and follows aliases, indexed slots and pass-through calls).

- **Coverage:** 172 IDA xrefs to `0xE559C4` = 172 raw byte hits. All are in defined functions (137), none are in undefined code, and all 137 decompile.
- **Slot indexing:** `mPadInfo[0]` constant ×156, `mPad[0]` ×8 (pad-internal loops). Constant `mPadInfo[1]` appears only as a loop end pointer in `sub_8AB020`.
- **Variable-index sites (all of them):** `stopVibration` (`padInfoIdx`, always 0), `aRoom::pauseInChk` (via `get_user_pad_id`), `play_vib_preset` (table column always 0), `sub_494F90` (`a1`), `readPad` / `sub_8E2F90` / `sub_8E5640` / `sub_8E5740` (`mpJoystick[Socket_no]`), `uFreeCamera::move` (`mPad[mControlPad]`, debug camera).
- **Hidden accessors that take the pad in a register** (these were the 9 functions the first pass couldn't resolve):
  - `sDevil4Pad::getTrigger` `0x4013D0` (trg, 20 callers), `get_btn_on` `0x449170`, `get_btn_rep` `0x4B1B20`: all `eax=this`, all read `mPadInfo[0]`.
  - `get_rstick_deadzoned` `0x485460` and `set_vib_pair_pad0` `0x796A90`: also `mPadInfo[0]`.
  - `sPad::request_stop_vib_all` `0x8E4770`: loops over 2 pads.
- **Second owner pointer:** `sDevil4Main::mpPad` (`+0x1035C`). It is written in `sDevil4Main::sDevil4Main` and used only for lifecycle vcalls: the dtor, `reset` (`sub_8AED20`), `move` (`sDevil4Main::move`) and vslot 7 (`sub_8AF180`). There are no field reads through it.
- **Mislabel fixed:** `0xE559DC` was named `sDevil4Pad::mpInstance_0`, but it is **`sMouse::mpInstance`** (DTI `sMouse`, 0xA8, ctor `sub_A51890`, 110 xrefs). It is not a pad consumer, but it is another global input singleton (mouse/cursor) to account for in multiplayer.

Earlier register-tracker histogram (raw displacement, constant `[0]`): `mBtn.on` 58, `mBtn.rel` 58, `mXInput` 16, `mBtn.trg` 12, `mDecideButton` 8, `mCancelBtn` 8, `mDecideBtn` 7, sticks 12, `mSensor` 4, …

Key consumers:

| Function | What | Per-player? |
|---|---|---|
| `cPeripheral::update` `0x7AFD10` | **Gameplay input**: copies `mPadInfo[0]` btn/press/anlg into `uPlayer::cPeripheral` | Owner is per-player, source is not. Keyboard binds also use `sMediator::mpPlayer->mPlayerID` instead of the owning player. Called from `uPlayer::main`, `uPlayerDante::main`, `uPlayerNero::main`, `uPlayer::setInterface` |
| `uPlayer::setPadVibration` `0x7AC130` | rumble → `mPadInfo[0]` | needs player→pad index |
| `sDevil4Pad::getTrigger` `0x4013D0` | returns `mPadInfo[0].mBtn.trg` (20 call sites) | no index param |
| `sDevil4Pad::cPadInfo::stopVibration` `0x401AE0` | **already index-aware** (`eax`), all 15 callers pass 0 | trivially patchable |
| `cCameraPlayer::moveRightStickAxisX/Y` | `mPadInfo[0].mAnlg[1]` | camera is shared (decide policy) |
| ~80 menu/UI funcs (`uTitle::*`, `sub_73xxxx`, `sub_84xxxx`, `sub_8Axxxx`…) | `mBtn.on/rel` edge tests | global UI. Can stay on merged pad 0 |

## Scaling beyond 2 players

### Hard limits
| Limit | Where |
|---|---|
| 2 physical slots embedded: `sPad::mPad[2]` (+0x34), `mpJoystick[2]` (+0x5C0), `mTickTimer[2]` (+0x5C8); `mPadInfo[2]` (+0x5D0) | struct layout |
| Allocation size `0x9E8` | **`sDevil4Main::sDevil4Main` `0x8AE280`** (`push 9E8h`, the real creation site, stored to `sDevil4Main::mpPad`), `sDevil4Pad::MyDTI::newInstance` `0x484C9D`, DTI `mSizeAndPage` @ `0xE57E70` |
| XInput user indices probed: 0..1 (`sPad::open` loop `< 2`) | `0x8E4210` |
| DirectInput devices stored: 2 (`sub_8E5640` enum callback, `Pad_no < 2`) | `0x8E5640` |
| XInput API maximum (`XUSER_MAX_COUNT`) is 4. Beyond 4 players needs DirectInput or Raw Input slots | OS |

### Count-2 loops / stride sites (everything that iterates slots)
Pad subsystem: `sPad::sPad` (Pad ctor loop, `Pad_no` loop, `open` loop, `mTickTimer[1]` init), `sPad::release_devices` `0x8E4120`, `sPad::open`,
`sPad::move`, `sPad::Pad::readPad` (free-slot search), `sPad::request_stop_vib_all` `0x8E4770`, `sub_8E5300`, `sub_8E5640`,
`sDevil4Pad::sDevil4Pad` (3 loops), `sDevil4Pad` dtor `0x484E90` (`ecx=1` countdown), `sDevil4Pad::move` (Input_attr loops ×2, user-id bound, merge loop),
`claim_user_pad_on_start`, `get_user_pad_id`, `set_vib_enable_all`.
Outside: `sub_796F00`, `sub_798250`, `sub_8AB020`, `sub_8F0FC0` (vib-enable / Input_attr / vib-stop loops over both slots).
Full instruction list: rerun the stride/const scan, or see `RE/scripts/sdevil4pad_xref_audit.py`.

### Option A: resize in place (rejected)
Growing `mPad[]` shifts `mDecideButton`…`mTickTimer` and the whole `sDevil4Pad` tail. That means re-encoding every constant `mPadInfo[0]` access (156 ctree sites, about 300 instructions across 137 functions), plus the `mXInput` and `mDecideButton` sites, the `+0x9D0..` fields, and all the alloc sites. That is too much patch surface for a binary.

### Option B: tail extension (recommended)
Change the two `push 9E8h` sites and the DTI size to `0x9E8 + ext`, and place the new slots **after** `+0x9E8`. No existing offset moves.
```
+0x9E8  sPad::Pad              mPadEx[N-2];          // 0x2C0 each; slots 2..N-1
        sDevil4Pad::cPadInfo   mPlayerPadInfo[N];    // 0x200 each; one logical pad per player
        IDirectInputDevice8A*  mpJoystickEx[N-2];
        int                    mTickTimerEx[N-2];
        int                    mPlayerPadId[N];      // player -> physical slot (-1 = unclaimed)
```
- `pad(i) = i < 2 ? &mPad[i] : &mPadEx[i-2]`. Only the slot loops listed above need rewriting to use it.
- **Keep `mPadInfo[0]` as the merged system/UI pad.** All 156 constant `[0]` consumers (menus, title, pause) stay untouched.
- The game's per-pad routines take the object in a register, so they can be reused on the extension slots:
  - `readPad(eax=Pad*)`: the XInput path only needs `Info.Kind=3`, `Be_flag=1` and `Socket_no=0..3`.
  - `cPadInfo::update(esi=cPadInfo*)`, `tick_vib_info(ecx, edx=dt)`, `clear_vib_info(ecx)`.
  - `moveVib(edi=Pad*, this, padNo)`: need to verify whether it indexes 2-slot arrays by `padNo`.
  - Caveat: the DirectInput path of `readPad` indexes `mpInstance->mpJoystick[Socket_no]` (5 sites). Either limit DirectInput to slots 0–1 or patch those sites to use the accessor.
- **Join:** generalise `claim_user_pad_on_start`. Each START on an unclaimed live slot assigns the next free `mPlayerPadId[p]`.
- **Per-player feed:**
  - `cPeripheral::update` reads `mPlayerPadInfo[player->padIdx]` and gets its keyboard map from the owning `uPlayer`, not `sMediator::mpPlayer`.
  - `setPadVibration` and the player-originated `stopVibration` calls use the same index.
- Lifecycle: the ctor must construct the extension `Pad`s (`sPad::Pad::Pad`) and `cPadInfo`s. The dtor and `release_devices` must release `mpJoystickEx`.
- Separate input singletons to consider: `sKeyboard` and `sMouse` (one keyboard+mouse player at most).

## Renames applied (DX9)
`sPad::Pad::Pad`, `sPad::Map::Map`, `sDevil4Pad::reset`, `sDevil4Pad::cPadInfo::{update,clear_vib_info,tick_vib_info}`,
`sDevil4Pad::set_vib_enable_all` (`0x485570`), `sPad::Pad::{readPad,setVibList,open_xinput}`, `aGame::game_start_init`, `aGame::DTI` (`0xE55CE8`).
Also: `sDevil4Pad::{claim_user_pad_on_start,get_user_pad_id,play_vib_preset,get_btn_on,get_btn_rep,get_rstick_deadzoned,set_vib_pair_pad0}`,
`sDevil4Pad::cPadInfo::pause_vib`, `sPad::{release_devices,request_stop_vib_all,scalar_deleting_dtor}`, `sDevil4Pad::{MyDTI::newInstance,scalar_deleting_dtor}`,
`sMouse::mpInstance` (`0xE559DC`, was mislabelled `sDevil4Pad::mpInstance_0`).
Note: `sPad::Pad` is declared with explicit tail padding (`_pad2BD[3]`). Something in the session rewrote it as `align(1)` / 0x2BD, which shifted the whole `sPad` tail by 4. Re-check its size if the type is ever regenerated.
Types renamed from the wrong `sDevil4Pad::` namespace to `sPad::*` / `sDevil4Pad::cPadInfo::k*` to match DTI names.
