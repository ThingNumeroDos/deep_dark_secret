# sShader name hash (XFUNIQUE IDs) — techniques & parameters

The engine identifies every shader **technique** and **parameter** by a 32-bit ID derived
from its name string. `sShader::getParameterFromName` / `getTechniqueFromName` hash the name
and look the ID up in `mParameterDesc[].mID` / `mTechniqueDesc[].mID` (the `XFUNIQUE` field).

**The full verified ID table is in [`sShader_hash_ids.json`](sShader_hash_ids.json)** —
62 techniques + 425 parameters = 487 names.

## The hash algorithm

It is **not** CRC32. It is a table-driven additive hash over adjacent lowercased character pairs,
where the table is a seeded-PRNG scramble built once at startup.

**Hash function** — `sub_8FF9B0(const char* name)` @ `0x8FF9B0`:

```
i = 0
for pos in 0 .. len-1:
    c0 = (tolower(name[pos])   - 32) & 0xFFFF
    c1 = (tolower(name[pos+1]) - 32) & 0xFFFF      # name[len] == '\0' -> contributes (0-32)
    idx = ((c0 << 6) | c1) & 0xFFF                 # 0 .. 4095
    i = (i + (int32)gHashTable[idx]) & 0xFFFFFFFF  # signed table entry, summed mod 2^32
return i
```

**Scramble table** — `gHashTable` = `dword_E51150[4096]` (in `.data`), built by `sub_8B6CE0` @ `0x8B6CE0`:

- `sub_8BD2A0(seed=321654)` seeds a **MT19937** state (624 words) via the LCG `x = 69069*x + 1`,
  taking `(cur & 0xFFFF0000) | (HIWORD(next))` per word.
- `sub_8BD3B0` is the standard MT19937 twist (`mag01 = {0, 0x9908B0DF}` at `dword_E16A98`).
- For `k = 0 .. 4095`, pull the next MT word `y` and apply this tempering (verbatim from `0x8B6DAB`):
  ```
  a = (((((y>>11) ^ y) & 0xFF3A58AD) << 7)) & 0xFFFFFFFF
  b = (a ^ (y>>11) ^ y) & 0xFFFFFFFF
  c = ((b & 0xFFFFDF8C) << 15) & 0xFFFFFFFF
  d = (c ^ a ^ (y>>11) ^ y) & 0xFFFFFFFF
  table[k] = (d ^ (d >> 18)) & 0xFFFFFFFF
  ```
  (the `sin`/`sqrt` loops earlier in `sub_8B6CE0` fill *unrelated* tables `flt_E4D14C` / `dword_E49150`
  and do not affect the hash table.)

The same hash with an extra `abs()` term is reused as `filename_hash` @ `0x8DFD2A` for resource paths.

> **Statically the table reads `0xFFFFFFFF`** because it is generated at runtime. The IDs in the JSON were
> produced by **emulating the engine's own `sub_8B6CE0` + `sub_8FF9B0` under Unicorn**, then
> **cross-checked against an independent Python reimplementation** of the MT + temper + hash — both agree
> bit-for-bit. Reproduction script: `scratchpad/emu_all_hashes.py`.

## Naming convention (how to tell technique vs parameter)

- `t`-prefix (`tXf…`) → **technique** (e.g. `tXfMaterialStandard` = `0x88367C19`)
- everything else → **parameter**: `g`-prefix globals (`gXf…`), `c`-prefix per-instance (`cXf…`),
  `Xf…` engine params, `…Sampler` texture slots, `mat…`, etc.

## Spot-check values

| Name | Kind | ID |
|------|------|----|
| tXfMaterialStandard | technique | 0x88367C19 |
| tXfPrimStandard | technique | 0xED2827CF |
| tXfFilterStandard | technique | 0x640E8A05 |
| gXfWorld | parameter | 0xAE179D10 |
| gXfViewProj | parameter | 0xC8F2867D |
| ViewZ | parameter | 0x5773A4D3 |
| XfBaseSampler | parameter | 0x4C3FB8D3 |
| gXfPrimType0 | parameter | 0x6357BE60 |
