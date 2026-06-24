# MT Framework Vertex Format / Vertex Declaration (DX9)

How DMC4 DX9 turns a model's packed vertex-element codes into a D3D9
`IDirect3DVertexDeclaration9`. Reached from the material record
(`rModelMaterial.mPVDecl` / `mPVDeclBase`, record +0x14 / +0x10 — see
[cMaterialStandard.md](cMaterialStandard.md)).

> The community MOD v153 `.ksy` labels these fields `pvdecl`/`pvdeclbase` and tags the
> *vertex-format enumeration* as guesswork. The decode below is derived from the binary
> (`cTrans::VertexDecl::build` + two lookup tables), not from that spec — and it bottoms
> out in real D3D9 enum values fed straight to `CreateVertexDeclaration`, so the enum
> identities are by-construction, not inference.

## Classes / functions

| Symbol | Addr | Role |
|--------|------|------|
| `cTrans::VertexDecl::vftable` | `0xC08240` | the decl wrapper class |
| `cTrans::VertexDecl::build` | `0xA555E0` | parse element codes → `D3DVERTEXELEMENT9[]` → `CreateVertexDeclaration` |
| `cTrans::VertexDecl::create` | `0x8F0DB0` | cache/factory: dedupe by element array, else `build` |
| `VertexDecl_typeLUT` | `0xC07AD0` | code → `D3DDECLTYPE` (stride 4) |
| `VertexDecl_usageLUT` | `0xC07B38` | code → `D3DDECLUSAGE` (stride 4) |
| `VertexDecl_sizeLUT` | `0xC07BC0` | code → element **byte size** (DWORD/entry) |

`cTrans::VertexDecl` object layout (from `build`): `+0x00` vftable, `+0x08` refCount,
`+0x10` mpVertexDecl (the D3D9 object, written by `CreateVertexDeclaration` into `a2+4`…
i.e. slots 4/5 hold device decl ptr + element count), `+0x14` element count,
`+0x18` pointer to the copied u32 element array.

## Element encoding (one u32 per vertex element)

`cTrans::VertexDecl::build` walks the input array until it hits a `0` dword, decoding
each entry into one `D3DVERTEXELEMENT9`:

```
bits  0–1   stream        = elem & 3
bits  2–9   offset(bytes) = (elem >> 2)  & 0xFF        // byte offset within the stream
bits 10–14  type code     = (elem >> 10) & 0x1F        // -> VertexDecl_typeLUT -> D3DDECLTYPE
bits 15–18  usage code    = (elem >> 15) & 0xF         // -> VertexDecl_usageLUT -> D3DDECLUSAGE
bits 19–21  usageIndex    = (elem >> 19) & 7
            method        = 0 (D3DDECLMETHOD_DEFAULT, always)
```

The declaration array is terminated with `{Stream=0xFF, Type=0x11}` = `D3DDECL_END()`
(`D3DDECLTYPE_UNUSED` = 17 = `0x11` — the in-binary anchor confirming these are D3D9
decls).

**usageIndex auto-increment:** when usage **code == 8** (`elem & 0x78000 == 0x40000`),
a per-declaration counter (`v13`) is incremented; usage codes **7 and 8** emit
`usageIndex = ((elem>>19)&7) - counter`. This lets consecutive TEXCOORD streams get
auto-assigned increasing indices.

## Type table (`VertexDecl_typeLUT`, code → D3DDECLTYPE)

Generated mechanically from the LUT bytes composed with the D3DDECLTYPE enum. Codes
whose LUT byte is `0` are zero-fill / unused slots (shown as `—`), not genuine FLOAT1.

| code | value | D3DDECLTYPE |
|------|-------|-------------|
| 2  | 1  | FLOAT2 |
| 3  | 2  | FLOAT3 |
| 4  | 3  | FLOAT4 |
| 7  | 8  | UBYTE4N |
| 8  | 5  | UBYTE4 |
| 9  | 6  | SHORT2 |
| 10 | 9  | SHORT2N |
| 13 | 7  | SHORT4 |
| 14 | 10 | SHORT4N |
| 17 | 15 | FLOAT16_2 |
| 18 | 16 | FLOAT16_4 |
| 19 | 4  | D3DCOLOR |
| 25 | 8  | UBYTE4N |
| 28 | 3  | FLOAT4 |
| 29 | 6  | SHORT2 |
| 30 | 2  | FLOAT3 |
| 31 | 1  | FLOAT2 |

(codes 0,1,5,6,11,12,15,16,20–24,26,27 → LUT byte 0 → unused/default)

## Usage table (`VertexDecl_usageLUT`, code → D3DDECLUSAGE)

Usage field is 4 bits (codes 0–15), but only 14 LUT entries precede an unrelated string
in `.rdata` at `+0x38`; **codes 14–15 are out of the validated range** — do not treat as
defined.

| code | value | D3DDECLUSAGE |
|------|-------|--------------|
| 2  | 3  | NORMAL |
| 3  | 6  | TANGENT |
| 4  | 2  | BLENDINDICES |
| 5  | 1  | BLENDWEIGHT |
| 6  | 10 | COLOR |
| 7  | 5  | TEXCOORD |
| 8  | 5  | TEXCOORD (auto usageIndex) |
| 9  | 7  | BINORMAL |
| 10 | 7  | BINORMAL |
| 11 | 3  | NORMAL |
| 13 | 7  | BINORMAL |

(codes 0,1,12 → LUT byte 0 → POSITION/unused)

## Vertex stride

Stride is **not stored as a single field** — it is computed by summing per-element byte
sizes from a third table, `VertexDecl_sizeLUT` (`0xC07BC0`, one DWORD per type code,
indexed by the same `(elem>>10)&0x1F`). The canonical loop (appears in `sShader::initialize`
and `sub_904B00`) walks the element array and accumulates only **stream-0** elements:

```c
stride = 0;
for (e in elements)
    if ((e & 3) == 0)                       // stream 0 only
        stride += VertexDecl_sizeLUT[(e >> 10) & 0x1F];
```

Element-size table (code → bytes; cross-checked against the type table):

| code | type | bytes |
|------|------|-------|
| 1 | FLOAT1 | 4 |
| 2 | FLOAT2 | 8 |
| 3 | FLOAT3 | 12 |
| 4 | FLOAT4 | 16 |
| 7 | UBYTE4N | 4 |
| 8 | UBYTE4 | 4 |
| 9 | SHORT2 | 4 |
| 10 | SHORT2N | 4 |
| 13 | SHORT4 | 8 |
| 14 | SHORT4N | 8 |
| 17 | FLOAT16_2 | 4 |
| 18 | FLOAT16_4 | 8 |
| 19 | D3DCOLOR | 4 |

(`VertexDecl_sizeLUT` defaults unmapped codes to 4; code 0 = 0 = terminator. This stride
sum is independent of `rModel::PRIMITIVE_INFO.vertexStride/vertexStride2`, which are
separate per-primitive on-disk stride bytes — reconciling the two is the remaining
follow-up below.)

## Built-in declarations (`sShader::initialize`, 0x8FC9B0)

The engine constructs ~20 fixed vertex declarations at shader-system init from inline
arrays of these element codes (the `v98[]`/`v115[]` blocks) and caches them in the
`sShader` singleton (offsets +26752…+26816). This is independent confirmation of the
element encoding above, and `sub_904B00` shows the codes also drive procedural geometry
generation (the `(elem>>15)&0xF` usage switch fills POSITION/NORMAL/TANGENT/TEXCOORD).

## Caching (`cTrans::VertexDecl::create`)

Maintains a list of already-built `cTrans::VertexDecl` instances. For an incoming element
array it scans the list (matching DTI == `cTrans::VertexDecl`), compares element arrays
dword-by-dword up to the `0` terminator, and on a full match returns the cached decl with
`refCount++`. On miss it allocates a 28-byte wrapper and calls `cTrans::VertexDecl::build`.
So identical vertex layouts across materials/models share one D3D9 declaration object.

## Open follow-ups

- **Resolved:** stride derivation (sum of `VertexDecl_sizeLUT` over stream-0 elements);
  type/usage/size decode; the cache/dedup path; built-in decl construction.
- **Still open — the rModel-from-file path.** All the functions traced here build decls
  from *engine-internal* code arrays (`sShader::initialize`, procedural geometry). The
  path that reads `mPVDecl`/`mPVDeclBase` (record +0x10/+0x14) as on-disk ids/pointers
  during model deserialization, and feeds them to `cTrans::VertexDecl::create`, was not
  located in this pass — the rModel loader (writer of `rModel.member_0x78` /
  `mPrimitiveInfo`) still needs to be found. Until then, `pvdeclbase` vs `pvdecl`
  (base-layout vs per-primitive override?) and their relation to
  `rModel::PRIMITIVE_INFO.vertexStride/vertexStride2` remain unconfirmed.
