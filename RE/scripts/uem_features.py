"""
uem_features.py — dump per-function matching features for a family of classes (default uEm*).

Optional config: OUT_DIReatures_cfg.json = {"prefix": "uPl", "tag": "pl"} selects the class
prefix and output file tag (se_<tag>_features.json / dx9_<tag>_features.json).

Runs in either IDB (detects which by root filename) via py_exec_file:
  * SE  (DevilMayCry4SpecialEdition.exe): every function whose demangled name starts with uEm*
  * DX9 (DevilMayCry4_DX9.exe): every function in the contiguous uEm code span (derived from
    the uEm vtables), plus all uEm vtables with slot lists.

Output JSON: {"side", "vtables": {cls: {"ea", "slots": [[i, ea, name], ...]}}, "funcs": {ea: feat}}
feat = {name, size, nbb, ninsn, strs, callees[[ea,name]], callers[ea], gl[names], imms, flts, vt[[cls,slot]]}

SE is reference-only: this script never writes to the database.
"""
import idautils, idc, idaapi, ida_funcs, ida_name, ida_bytes, ida_segment, ida_ua, ida_gdl, json, re, struct

OUT_DIR = r"C:\Users\Home\AppData\Local\Temp\claude\c--Tools-MCP-dev-test-re-test\44865d16-522b-4fef-aa4c-ace8a730064e\scratchpad"
AUTO = ('sub_', 'off_', 'dword_', 'word_', 'byte_', 'qword_', 'unk_', 'loc_', 'flt_', 'dbl_', 'asc_', 'stru_', 'j_', 'nullsub_', 'xmmword_', 'a')
import os
_cfg_path = os.path.join(OUT_DIR, 'features_cfg.json')
_cfg = json.load(open(_cfg_path)) if os.path.exists(_cfg_path) else {}
PREFIX, TAG = _cfg.get('prefix', 'uEm'), _cfg.get('tag', 'uem')
CLS_RE = re.compile(r"^(%s[A-Za-z0-9_]*)(?:::|$)" % PREFIX)
VT_RE = re.compile(r"^(?:const )?(%s[A-Za-z0-9_]*(?:::[A-Za-z0-9_]+)?)::(?:`vftable'|vftable(?:_0)?$)" % PREFIX)

def dem(n):
    return idc.demangle_name(n, idc.get_inf_attr(idc.INF_SHORT_DEMNAMES)) or n

def seg_kind(ea):
    s = ida_segment.getseg(ea)
    return (s.type, ida_segment.get_segm_name(s)) if s else (None, None)

def is_code(ea):
    return seg_kind(ea)[0] == ida_segment.SEG_CODE

def is_auto(n):
    return (not n) or n.startswith(AUTO[:-1]) or re.match(r'^a[A-Z0-9]', n) is not None

def walk_vtable(ea):
    slots, p = [], ea
    while True:
        v = ida_bytes.get_dword(p)
        if not is_code(v):
            break
        if p != ea and ida_name.get_name(p):
            break
        slots.append([len(slots), hex(v), dem(ida_name.get_name(v))])
        p += 4
    return slots

def features(fea, vt_index):
    f = ida_funcs.get_func(fea)
    strs, callees, gl, imms, flts = [], [], set(), set(), set()
    ninsn = 0
    for h in idautils.FuncItems(fea):
        ninsn += 1
        insn = ida_ua.insn_t()
        if not ida_ua.decode_insn(insn, h):
            continue
        for x in idautils.XrefsFrom(h, 0):
            t = x.to
            if x.iscode:
                if insn.get_canon_mnem() == 'call' and x.type in (idaapi.fl_CN, idaapi.fl_CF):
                    callees.append([hex(t), dem(ida_name.get_name(t))])
                continue
            st = idc.get_str_type(t)
            if st is not None and ida_bytes.is_strlit(ida_bytes.get_flags(t)):
                s = idc.get_strlit_contents(t, -1, st)
                if s:
                    strs.append(s.decode('latin-1')[:80])
                continue
            n = ida_name.get_name(t)
            if n and not is_auto(n):
                gl.add(dem(n))
            elif seg_kind(t)[1] in ('.rdata', '.data'):
                fl = ida_bytes.get_flags(t)
                if ida_bytes.is_float(fl):
                    flts.add(round(struct.unpack('<f', struct.pack('<I', ida_bytes.get_dword(t)))[0], 4))
                elif ida_bytes.is_double(fl):
                    flts.add(round(struct.unpack('<d', struct.pack('<Q', ida_bytes.get_qword(t)))[0], 4))
        for op in insn.ops:
            if op.type == ida_ua.o_void:
                break
            if op.type == ida_ua.o_imm:
                v = op.value & 0xFFFFFFFF
                if ida_segment.getseg(v):
                    continue
                if v >= 0x10 and v not in (0xFFFFFFFF, 0xFF, 0xFFFF):
                    if 0x3C000000 <= v <= 0x4F000000 or 0xBC000000 <= v <= 0xCF000000:
                        flts.add(round(struct.unpack('<f', struct.pack('<I', v))[0], 4))
                    else:
                        imms.add(v)
    try:
        nbb = sum(1 for _ in ida_gdl.FlowChart(f))
    except Exception:
        nbb = -1
    callers = sorted({hex(ida_funcs.get_func(x).start_ea) for x in idautils.CodeRefsTo(fea, 0) if ida_funcs.get_func(x)})
    return {"name": dem(ida_name.get_name(fea)), "size": f.end_ea - f.start_ea, "nbb": nbb, "ninsn": ninsn,
            "strs": sorted(set(strs)), "callees": callees, "callers": callers, "gl": sorted(gl),
            "imms": sorted(imms)[:80], "flts": sorted(flts)[:80], "vt": vt_index.get(fea, [])}

def run():
    side = 'SE' if 'Special' in idaapi.get_root_filename() else 'DX9'
    vtables = {}
    for ea, n in idautils.Names():
        m = VT_RE.match(dem(n))
        if m:
            vtables.setdefault(m.group(1), {"ea": hex(ea), "slots": walk_vtable(ea)})
    vt_index = {}
    for c, v in vtables.items():
        for i, fea, _ in v["slots"]:
            vt_index.setdefault(int(fea, 16), []).append([c, i])
    if side == 'SE':
        scope = [ea for ea in idautils.Functions() if CLS_RE.match(dem(ida_name.get_name(ea)))]
    else:
        # span of functions referenced only by this family's vtables (exclude shared base-class
        # impls), widened to cover already-named family functions. No percentile trimming: that
        # cut real uEm000/uEmSample code off both ends of the uEm run.
        own = [ea for ea, refs in vt_index.items() if is_code(ea) and len(refs) <= 3]
        own += [ea for ea in idautils.Functions() if CLS_RE.match(dem(ida_name.get_name(ea)))]
        if 'span' in _cfg:
            lo, hi = int(_cfg['span'][0], 16), int(_cfg['span'][1], 16)
        else:
            lo, hi = min(own), max(own)
        scope = [ea for ea in idautils.Functions(lo, hi + 1)]
    funcs = {hex(ea): features(ea, vt_index) for ea in scope}
    path = OUT_DIR + ("\\se_%s_features.json" if side == 'SE' else "\\dx9_%s_features.json") % TAG
    json.dump({"side": side, "vtables": vtables, "funcs": funcs}, open(path, 'w'))
    rng = (hex(min(scope)), hex(max(scope))) if scope else None
    print({"side": side, "vtables": len(vtables), "funcs": len(funcs), "range": rng, "path": path})

run()
