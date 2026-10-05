# Player pad handling (uPlayer input pipeline)

DX9. Companion to `sDevil4Pad_struct.md`. Covers how a `uPlayer` turns pad and keyboard state into actions, and where that path is tied to a single player.

## Per-player components (embedded in `uPlayer`, 0x3270)

| Off | Member | Size | Notes |
|---|---|---|---|
| `+0x1370` | `uPlayer::cPeripheral mPeripheral` | 0x98 | Raw input: `mPadBtnOn/Trg/Rel`, `mPadBtnPress[15]` (`BTN_PRESS_*`), `kAnlg mAnlgL/mAnlgR/mHoldAnlgL`, `mIsHold`. SE is 0xB0 (adds `mFakeTimer`, `mAutoPadRollFrame[4]`, `mIsFakeData`). |
| `+0x1408` | `uPlayer::cInterface mInterface` | 0x4C | Action layer, identical to SE: `yBtnInfo mBtnOn/Trg/Rel/Old` (`kBtnBit`: atckShort, atckLong, jump, provoke, lockOn, chgLockOn, devilTrg, …, grab, chgStyleTS/RG/GS/SM, chgAtckLong), `kAnlgInfo mAnlg` (`POW_MODE pow`, radian, digital up/down/left/right), `kLockOnInfo`, `mIsSet*` flags, Nero `mOverDriveGauge/Trg`, lock-on timers. |
| `+0x1494` | `uint mPlayerID` | | 0 = Dante, 1 = Nero. Selects the binding set. |
| `+0x1509` | `bool mIsInterfaceSetting` | | Input gate. Set in the ctor and in `sub_7BFC70` (Dante vslot), cleared in `uPlayer::setup`. |
| `+0x150A` | `bool mIsEnableExceptionInput` | | Enables the raw-input fallback in Dante/Nero `main`. |
| `+0x1EB8` | `cParamTblCtrl mPadVibParam` | | Rumble parameter table used by `setPadVibration`. |

All types are declared in the IDB (`uPlayer::cPeripheral*`, `uPlayer::cInterface*`). SE names were used only where a DX9 access of the same width was confirmed at the same offset.

## Frame flow

```
uPlayer::main (0x7A7E54 gate)
 ├─ mIsInterfaceSetting==1 && !mIsDead ─► vcall [vt+0x178] uPlayer::setInterface (0x7A91E0)   ← only caller in the binary
 │     1. cPeripheral::update(&mPeripheral)                         0x7AFD10
 │          pad  : sDevil4Pad::mpInstance->mPadInfo[0]  (btn on/trg/rel, mPress[15], mAnlg[0]/[1])
 │                 sticks: deadzone 0.24, scaled to ±127 (s16)
 │          kbd  : sKeyboard stick emulation, binds = sSave.m{Dante|Nero}.mBtn.mActBtnKB[15..22]
 │                 chosen by sMediator::mpPlayer->mPlayerID   ← NOT the owning player
 │          cPeripheral::updateAnlgInfo(esi=kAnlg*) ×2          0x7B0250  (len, radian, digital 0x10/0x20/0x40/0x80, trg/rel)
 │     2. stick-hold logic (mIsHold / mHoldAnlgL vs this->mCamAngl)
 │     3. uPlayer::setInterfaceAnlgInfo(edx=this)                0x7A9550
 │          requires sMediator::mpCamera; pow = WALK (len ≥ 80) / RUN (≥ 120); radian = stick + this->mCamAngl.now
 │     4. uPlayer::map_pad_btn_to_action(ecx=this, eax=bits, edi=out) ×3 → mBtnOn/Trg/Rel   0x7A96D0
 │          bindings sSave.m{Dante|Nero}.mBtn.mActBtn[] chosen by this->mPlayerID
 │          (style buttons always read the mDante set, grab always reads the mNero set)
 │     5. Nero OverDrive: pressure from mPadBtnPress[idx(mNero.mActBtn[6])] or key mActBtnKB[6] → mOverDriveGauge/Trg
 │     6. uPlayer::setInterfaceInfoKB(this)                      0x7A9870
 │          ORs global sKeyboard on/trg/release into mInterface via mActBtnKB[] (this->mPlayerID)
 └─ else if mActionNo==9 ─► cPeripheral::update + setInterfaceAnlgInfo only (raw)

uPlayerDante::main 0x7B4AA2 / uPlayerNero::main 0x7E3CE9
 └─ !mIsInterfaceSetting && mIsEnableExceptionInput ─► cPeripheral::update, then test raw
    mPeripheral.mPadBtnOn against sSave bindings directly (e.g. Nero mActBtn[2])
```

Downstream gameplay reads `this->mInterface` / `this->mPeripheral`, which are per-instance. **No player code reads `sDevil4Pad` outside `cPeripheral::update` and the vibration calls.** Player-side `sKeyboard` reads exist only in `cPeripheral::update`, `setInterface` and `setInterfaceInfoKB`.

## Output (rumble)

| Site | Target |
|---|---|
| `uPlayer::setPadVibration` `0x7AC130` (6 callers: `sub_7BBA50`, `sub_7C3CC0`, `sub_7E4070`, `sub_7E5640`, `sub_7F0ED0`, `sub_7F10D0`) | `mPadInfo[0]` via `sub_4863D0` / `sub_486440`, params from `this->mPadVibParam` |
| `uPlayer::updateContactInfoSub` `0x7AB770` | `stopVibration(0)` |
| **`uEm023` (Credo Angelo)**: `damageMessage`, `sub_6D01C0`, `sub_6D1630`, `sub_6D1900`, `sub_6D1D70` | `mPadInfo[0]`. Enemy-originated rumble needs a target player. |

## Multiplayer implications (N players)

1. **One input redirect point.** Only `cPeripheral::update` needs a new source: about 5 reads of `mPadInfo[0]` become reads of the player's `cPadInfo`. In the tail-extension plan that is `mPlayerPadInfo[padIdx]`. Everything downstream is already per-instance.
2. **Owner without a new field.** `cPeripheral` is embedded at `uPlayer+0x1370`, so the owner is `(uPlayer*)((char*)this - 0x1370)`. Use that instead of `sMediator::mpPlayer` for the keyboard binding lookup (mpPlayer site `0x7AFEB8`, already in `mpplayer_call_sites.json`). `padIdx` still needs storage, either a side table keyed by `uPlayer*` or a spare field.
3. **Bindings are per character, not per player.** `sSave.mDante/mNero.mBtn.mActBtn[]` and `mActBtnKB[]` are global, so two Dantes share one config. Per-player configs would need `map_pad_btn_to_action`, `setInterfaceInfoKB`, the OverDrive block and the Dante/Nero exception paths to take a binding pointer.
4. **Keyboard and mouse are single.** `sKeyboard` and `sMouse` are global, so at most one KB/M player. For pad-only players, skip `setInterfaceInfoKB` and the KB stick emulation in `cPeripheral::update` (gate on padIdx/KB owner).
5. **Camera.** `setInterfaceAnlgInfo` needs `sMediator::mpCamera` and uses the per-player `mCamAngl`. Camera-relative movement works on a shared screen. Split screen would need a per-player camera.
6. **Rumble.** `setPadVibration` and `updateContactInfoSub` should use the owner's `padIdx`. The `uEm023` sites need the hit or targeted player resolved to a pad.
7. **Gate.** Nothing in the input path checks `this == sMediator::mpPlayer`, so N `uPlayer` instances would each run `setInterface`. Today they would all read pad 0.
