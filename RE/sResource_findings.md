# sResource::create — Analysis Findings

## Function: `sResource::create` @ `0x8DF530`

Signature (reconstructed):
```c
cResource * __userpurge sResource::create(
    sResource *this @<eax>,
    int        name_or_id,   // path string pointer or raw ID
    char      *mode,         // file extension / type string (e.g. "tex")
    uint       flags         // creation flags bitmask
)
```

Returns a `cResource*` on success, `nullptr` on failure.

---

## High-level flow

```
1. Hash the filename → 64-bit ID  (filename_hash)
2. Lock the resource table         (CRITICAL_SECTION at this+0x4, guarded by this+0x1C or cSystem::mJobSafe)
3. findTable(this, id)
   ├── HIT  → addref, _stricmp(cached_path, mode) [result discarded — see below], unlock, return existing cResource*
   └── MISS → unlock, check flags:
               bit 7 (0x80) set  → return nullptr immediately (no-create flag)
               else apply two flag modifiers (this+0x903E, this+0x903F),
               then dispatch by bits 0 and 1:
               bit 0 → sub_8DF980 (file-load path)
               bit 1 → sub_8DF760 (in-memory / pre-loaded path)
               if result non-null AND flag bit 8 (0x100) set → mark cResource::mAttr |= 0x800
```

---

## Hash table layout (`sResource` struct)

| Offset | Field | Notes |
|--------|-------|-------|
| `+0x00` | vtable | |
| `+0x04` | `CRITICAL_SECTION` (24 B) | guards table access |
| `+0x1C` | `char mJobUnsafe` | non-zero → always lock (bypass `cSystem::mJobSafe` shortcut) |
| `+0x1038` | `cResource* mpTable[8192]` | **inline array**, 32768 bytes; NOT a pointer |
| `+0x903E` | `char mFlagForceAsync` | if set, OR flags with `0x04` before dispatch (forces async/cached load) |
| `+0x903F` | `char mFlagForce0x20` | if set, OR flags with `0x20` before dispatch |
| `+0x904E` | `char` | checked in `sub_8DF980` (file-load path only); if set AND flags has bit 2, enables alternate stream path |
| `+0xA050` | `uint mTableUsed` | running count of inserted entries (used in `sub_8DF760`) |

The table is a **closed-address hash map with open addressing and linear probing**:
- Bucket index = `(id >> shift) & 0x7FF` — 2048 primary buckets × 4 slots each
- Collision: shift increments by 1 (0 → 16), probing a wider key window
- `findTable` (`0x8DF6E0`): lookup only, returns null if not found after shift 16
- `sub_8DFC30` (`0x8DFC30`): insert — finds first empty slot in the same bucket chain, writes the pointer

---

## `cResource` struct (confirmed from IDA type `cResource`, ordinal 187)

| Offset | Field | Type | Notes |
|--------|-------|------|-------|
| `+0x00` | vtable | `void*` | |
| `+0x04` | `mPath` | `char[64]` | null-terminated path/name |
| `+0x44` | `mRefCount` | `uint` | incremented on cache hit (`++*(this+0x44)`) |
| `+0x48` | `mAttr` | `uint` | attribute/flag bits; `0x800` = "no-free" marker; `0x40` = async-cached; `0x100`/`0x200` = priority |
| `+0x4C` | `mState` | `uint` | priority tier encoded in bits 16–18 (`n4 << 16`), masked with `0x70000` |
| `+0x50` | `mSize` | `uint` | file size in bytes (populated on open) |
| `+0x54` | *(4 bytes unknown)* | | |
| `+0x58` | `mID` | `uint` (struct) + 4 bytes after = **8-byte key** | `findTable` compares `*(_QWORD*)&result->mID` against the full 64-bit hash |

> **Note:** The IDA struct declares `mID` as `uint` at `+0x58` with 4 undefined bytes at `+0x5C`. In practice `mID` is a **64-bit field** — `findTable` loads it as a QWORD and `sub_8DF980` writes `*(_QWORD*)(param_4+88)` = `*(param_4+0x58)`. The struct declaration is wrong; `mID` should be `ulonglong` (8 bytes), making `cResource` size = 96 bytes confirmed.

---

## Creation flag bitmask

| Bit | Hex | Meaning |
|-----|-----|---------|
| 0 | `0x01` | File-load path (`sub_8DF980`) |
| 1 | `0x02` | In-memory / pre-loaded path (`sub_8DF760`) |
| 2 | `0x04` | Async/cached load; forces alternate file stream in `sub_8DF980` |
| 4 | `0x10` | Priority modifier (passed to file open) |
| 5 | `0x20` | Priority modifier (OR'd when `this+0x903F` is set) |
| 7 | `0x80` | **No-create**: return null immediately on miss |
| 8 | `0x100` | Post-create: set `cResource::mAttr |= 0x800` |
| 11–12 | `0x800`, `0x1000` | Priority tier bits (decoded to n4 = 2/1) |
| 13 | `0x2000` | Priority tier n4 = 1 |
| 14 | `0x4000` | Priority tier n4 = 3 |
| 15 | `0x8000` | Priority tier n4 = 4 (highest) |

Priority tier `n4` is written to `cResource::mState` bits 16–18 (`n4 << 16`, masked `0x70000`).

---

## `sub_8DF980` — file-load path

Allocates a new `cResource` via vtable+4 (factory/alloc method), populates:
- Sets 64-bit ID at `+0x58`
- Sets priority tier in `mState`
- Copies path into `mPath` (`strcpy`)
- Opens file via `sub_8DF190` (constructs an `MtFileStream` on the stack)
- Reads file size via `GetFileSize`
- Calls vtable+32 (load/parse method) with the stream
- On success: sets `mState |= 0x0001` (loaded)
- On failure: sets `mState |= 0x0010` (error)
- Inserts into hash table via `sub_8DFC30` and then re-calls `findTable` under lock to handle races

## `sub_8DF760` — in-memory / pre-loaded path

Allocates via same factory. Differences from file-load:
- Takes a pre-computed 64-bit ID directly (no filename hashing)
- No file I/O — marks flags directly from the `flags` argument (`0x40`, `0x100`, `0x200`)
- Inserts into table via `sub_8DFC30`, increments `mTableUsed` at `this+0xA050`
- If a duplicate is found by the inner `findTable` call, increments its refcount and frees the just-allocated entry instead

---

## Notable quirks

**`_stricmp` result discarded on cache hit (0x8DF58C):**
On a cache hit, `_stricmp(cached_entry->mPath, mode)` is called but its return value in EAX is immediately destroyed by `add dword ptr [esi+44h], 1`. This is a dead comparison — almost certainly a debug-build assertion (`ASSERT(stricmp(...)==0)`) that the release compiler reduced to a no-op call. The mode string is **not validated** at runtime; a mismatched extension silently returns the wrong resource type.

**Both paths call `findTable` a second time under lock:**
`sub_8DF980` acquires the lock, calls `findTable` again after file-open completes, and if another thread raced in the same resource, it discards its own allocation and bumps the winner's refcount. This is a double-checked locking pattern around file I/O.

**Table is inline, not a pointer:**
`sResource::mpTable` (at `+0x1038`) is declared as `cResource*[8192]` — an embedded array, not an indirection. The full `sResource` singleton is at minimum `0x1038 + 0x8000 = 0x9038` bytes plus trailing fields.
