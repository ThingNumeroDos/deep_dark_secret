# cUtil cross-reference: DMC4 SE → DX9

Cross-references the `cUtil` static utility class between the leaked-PDB **Special Edition**
build (port 13339, reference only) and the **DX9** target (port 13337).

## Summary

- SE has **66** `cUtil::` functions (`?...@cUtil@@SA...` mangled), contiguous at **0x5AF170–0x5BD0E0**.
- In DX9, the `cUtil` functions that exist as standalone functions form a **contiguous blob at
  0x45D700–0x462F79** (23 functions). The remaining ~43 SE `cUtil` functions are either inlined,
  absent from this build, or located outside this region in DX9 (the small `changeEndian`
  overloads, `FindEnum`, `easyCurve`, sequence-trigger helpers, `drawTile`/`drawLine`/`drawOBB`/
  `drawHpBar`, the AABB-from-sphere/capsule overloads, etc.).
- The blob is **reordered** relative to SE source order (e.g. `checkCulling` is first in DX9,
  `makeAABB(OBB)` is last).
- Matching was done by **content** (decompiled structure + callee fingerprint + signature),
  not address order, because DX9 is an older build with different layout.

## ⚠️ Mislabel corrected

`cUtil::checkHeight` at **0x45E790** in the DX9 IDB was **wrong**. That function does two
line-sweep `findIntersection` calls (down then up) — it is SE's **`checkGround`** (0x5AF4F0).
The real **`checkHeight`** is the tiny wrapper `sub_45EA70`, which just calls `checkGround` and
returns a height delta (matching SE 0x5AF740). Both have been renamed.

## Cross-reference table (DX9 blob → SE)

| DX9 addr | size | New DX9 name | SE addr | SE size | Notes |
|----------|------|--------------|---------|---------|-------|
| 0x45D700 | 0x108B | `cUtil::checkCulling` | 0x5B4AD0 | 0x1739 | 6 frustum planes via `MtPlane::fromPoints`, sphere-vs-plane test |
| 0x45E790 | 0x2E0  | `cUtil::checkGround` | 0x5AF4F0 | 0x249  | **was mislabeled checkHeight**; 2× line-sweep |
| 0x45EA70 | 0x33   | `cUtil::checkHeight` | 0x5AF740 | 0x39   | wrapper → checkGround |
| 0x45EAB0 | 0x2F   | `cUtil::getRandPlusMinus` | 0x5B06F0 | 0x2F   | returns [-x,+x]; uses MtRandom::nextTable |
| 0x45EAE0 | 0x57   | `cUtil::calcPitch` | 0x5AFE50 | 0x27   | atan2(dy, sqrt(dx²+dz²)) |
| 0x45EB40 | 0x99   | `cUtil::calcAngleXY` | 0x5AF8E0 | 0xAA   | writes yaw(+4), pitch(+0), 0(+8) |
| 0x45EBE0 | 0x7F   | `cUtil::calcAngleYDiff` | 0x5AF990 | 0x84   | yaw delta vs ref, wrapped to [-π,π] |
| 0x45EC60 | 0x115  | `cUtil::calcVectorRotateY` | 0x5B0760 | 0x10F  | rotate vector around Y by angle |
| 0x45ED80 | 0xC2   | `cUtil::checkAngleRange` | 0x5AFA20 | 0x9B   | was placeholder `checkEulerAngleBound`; returns -1/0/1 |
| 0x45EE50 | 0x17E  | `cUtil::moveAngle` | 0x5AFAC0 | 0x118  | already correct |
| 0x45EFD0 | 0xBD   | `cUtil::moveAngleSlowdown` | 0x5AFBE0 | 0xA6   | already correct |
| 0x45F090 | 0x61   | `cUtil::moveValueSlowdown` | 0x5AFC90 | 0x8B   | clamp step, snap within 0.001 |
| 0x45F100 | 0x138  | `cUtil::movePointSlowdown` | 0x5B0870 | 0xD6   | already correct; (Vec3&, Vec3&, float, float) |
| 0x45F240 | 0x10A  | `cUtil::movePointSlowdown_scalar` | 0x5B0950 | 0xC0   | scalar-target overload (Vec3&, f,f,f,f) |
| 0x45F350 | 0x2FF  | `cUtil::checkRange` | 0x5B0060 | 0x11A  | inv-matrix transform → length + atan2 angle |
| 0x45F650 | 0x123  | `cUtil::checkScrCollision` | 0x5B0180 | 0xF3   | CapsuleEdge4 sweep, writeback pos |
| 0x45F780 | 0x8E   | `cUtil::getEfctMtrlFlg` | 0x5B1050 | 0xF9   | already correct; reads JungleWeather |
| 0x45F860 | 0xADE  | `cUtil::meleeEffectQuat` | 0x5B1150 | 0x1927 | orientation + random, no effect-spawn calls |
| 0x4603C0 | 0x62   | `cUtil::setDamageEffect_group` | 0x5B62D0 | 0x6C   | cCollisionGroup overload → forwards to 0x460430 |
| 0x460430 | 0xA19  | `cUtil::setDamageEffect` | 0x5B2A80 | 0x149C | spawns effect: setEffectStay/Const, getJointFromNo |
| 0x460E60 | 0x493  | `cUtil::drawSphere` | 0x5B6AF0 | 0x138F | already correct |
| 0x461300 | 0x1C79 | `cUtil::drawCapsule` | 0x5B7EF0 | 0x2C28 | already correct; calls drawSphere |
| 0x462F80 | 0xBCB  | `cUtil::makeAABB_OBB` | 0x5B3F20 | 0xBAB  | OBB 8-corner min/max → AABB |

## SE↔DX9 helper renames (same role, different symbol)

| DX9 symbol | SE symbol | Role |
|------------|-----------|------|
| `MtRandom::nextTable` | `MtRandom::nrand` | random source |
| `sPrim::getcPrim` / `sPrim::submitLine` | `sPrimitive::getCPrim` / `cPrimBuffer` path | debug-primitive rendering |

## SE cUtil functions NOT found as standalone in the DX9 blob

(present in SE 0x5AF170–0x5BD0E0 but inlined/absent/elsewhere in DX9 — not yet located)

FindEnum, easyCurve, calcVectorCurve, calcVectorCurve2, getSequenceTrgOn/Off,
checkSequenceTrgOnBit/OffBit, calcDifficulty, drawFrustum, changeEndian (all 7 overloads),
checkFloat, calcRateValue, calcAngleX, calcAngleY (both overloads), calcAngleZ,
checkAngleRange variants, isInsideQuadXZ, fillFanRing (both overloads), checkFanRing (4 overloads),
getShadow, getDbgMaterial, ReleaseAssert, makeAABB(Sphere)/makeAABB(Capsule), checkHDTVMode,
Dice, changeEndian(float), getRandRange, modifyShadow, drawSphere(MtSphere overload),
drawTile, drawLine, drawOBB, drawHpBar.

These would need separate content-matching passes if required.
