# kTHINKDATA Table Mapping — All Enemy Types

## Summary

All 26 enemy types with kTHINKDATA tables have been located in the DX9 binary and annotated
with PDB-derived symbol names from the SE reference IDB.

**Total names applied: 4359** (4350 kTHINKDATA entries + 9 follow-up fixes)  
**Types applied: 1645** (kTHINKDATA[N] arrays and kTHINKDATA *[5] ptr tables)

## kTHINKDATA Struct

The struct is 104 bytes per entry, declared as `kTHINKDATA` in the DX9 IDB (previously named
`Em000ActionGuardTbl` — renamed during this session).

Fields (from prior session):
- `+0x00`: `flg_lo` (uint32) — action flags low
- `+0x04`: `flg_hi` (uint32) — action flags high  
- `+0x08..+0x24`: 8 floats — range/angle parameters
- `+0x28`: `actionNo` (int32) — action number
- `+0x2C`: `pThinkData*` — pointer to sub-table
- `+0x30..+0x34`: two callbacks
- `+0x38..+0x67`: bit, fsys_param[5], fusr_param[4]

## DX9 Chain Start Addresses

| Enemy | Chain Start (DX9) | Notes |
|-------|------------------|-------|
| Em036 | `0xC79D5C` | ptr table (20 bytes) + data |
| Em032 | `0xC7A5DC` | ptr table (20 bytes) + SetAndGoPos ptr + data at +92 |
| Em030 | `0xC7AE2C` | ptr table (20 bytes) + DamageEffect(112) + WarpRandTbl(16) + data at +148 |
| Em029 | `0xC94654` | ptr table (20 bytes) + DamageEffect(112) + WarpRandTbl(16) + data at +148 |
| Em026 | `0xCA8290` | first data entry (Em026ThinkTbl, 416 bytes) |
| Em025 | `0xCAA060` | first data entry |
| Em023 | `0xCBAFE0` | first data entry |
| Em022 | `0xCC6EC4` | ptr table (20 bytes) + data at +20 |
| Em021 | `0xCE8038` | first data entry |
| Em019 | `0xD283C4` | ptr table (20 bytes) + data at +20 |
| Em018 | `0xD3B8B4` | ptr table (20 bytes, already 20 in SE) + data at +20 |
| Em017 | `0xD44340` | first data entry |
| Em016 | `0xD4C678` | first data entry |
| Em015 | `0xD4D5B8` | first data entry (no ptr table) |
| Em014 | `0xD4E484` | ptr table (20 bytes) + DamageEffect(112) + data at +132 |
| Em013 | `0xD4F198` | first data entry |
| Em012 | `0xD52AE8` | first data entry |
| Em011 | `0xD627D0` | first data entry |
| Em010 | `0xD6D8C8` | first data entry |
| Em009 | `0xD7A244` | ptr table (20 bytes) + data at +20 |
| Em008 | `0xD88988` | first data entry |
| Em006 | `0xD95ED8` | first data entry (no ptr table in SE or DX9) |
| Em005 | `0xDABF94` | ptr table (20 bytes) + FloatArr1(80) + FloatArr2(80) + data at +180 |
| Em003 | `0xDB6F1C` | ptr table (20 bytes) + data at +20 |
| Em001 | `0xDC0A3C` | ptr table (20 bytes) + data at +20 |
| Em000 | `0xDCC3B8` | first data entry (no leading ptr table) |

## Ptr Table Layout

Ptr tables in DX9 are always 20 bytes (5 × DWORD), typed as `kTHINKDATA *[5]`.  
In SE, most ptr tables are 4 bytes (1 × DWORD) — the extra 4 slots are DX9-specific.  
Em018 and Em030 already had 20-byte ptr tables in SE.

## Fingerprinting Method

Each chain was located by scanning `.data` for the `(flg_lo, flg_hi, actionNo)` triple of the
first distinctive data entry, then verifying a second entry at the expected cumulative offset.
Where the first entry was non-unique (Em001/Em003 both start with `(0, 1, 141)`), deeper entries
with distinctive flag patterns were used for disambiguation.

## CSV Reference

Full SE extraction: `C:\Tools\MCP_dev\test\re-test\.ida-mcp\se_all_enemy_tables.csv`  
Format: `em,se_addr,se_sz,actionNo,flg_lo,flg_hi,demangled_name` (6606 entries)

## Known Issues / Caveats

- The SE CSV for some enemies (Em001, Em003, Em019, Em023, etc.) includes trailing entries that
  belong to adjacent enemies or unrelated audio/library globals. These are filtered by the
  chain boundary check (each chain ends where the next chain starts).
- Em005 and Em006 share identical flag patterns for their first 4+ data entries; they are
  distinguished by entry[5] size (`air_sidemove_tbl` is 728 bytes in Em005, 832 in Em006).
- Em008 and Em009 share identical first 3 entries; distinguished by entry[3] `flg_lo`
  (Em008: `0x5D0`, Em009: `0x590`).
