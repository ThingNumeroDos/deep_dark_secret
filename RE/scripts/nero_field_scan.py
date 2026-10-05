"""
nero_field_scan.py — find every read of *subclass-only* player state through sMediator::mpPlayer.

Hex-Rays mangles accesses past sizeof(uPlayer) (mpPlayer is typed uPlayer*), so this works at the
instruction level. For each function in RE/mpplayer_call_sites.json:
  * taint the register written by each mpPlayer load (site `deref_ea` / `deref_dst`)
  * linear sweep in address order, propagating taint through reg-reg moves and stack spills
    (stack slots keyed by IDA's stack-var operand text, e.g. [esp+30h+var_14])
  * record [tainted+disp] with disp >= 0x3270 (uPlayer size) -> subclass-only field
  * follow pointer loads one/two levels: mov r2,[tainted+disp] taints r2 with that chain
  * resolve each step to a member name using the IDB struct types (uPlayerNero first, then
    uPlayerDante), so chains read e.g. mpDevilStand->mpRightHand->mRetPos
Linear sweep ignores control flow: good enough to flag functions; verify before patching.

Also records every `strcmp(..., "uPlayerNero")` user and every mPlayerID read (+0x? from type).
Run in DX9 via py_exec_file. Output: RE/nero_field_scan.json
"""
import json, re, idc, idautils, ida_funcs, ida_ua, ida_typeinf, ida_name

ROOT = r"C:\Tools\MCP_dev\test\re-test\RE"
UPLAYER_SIZE = 0x3270
TIL = ida_typeinf.get_idati()

def udt(name):
    t = ida_typeinf.tinfo_t()
    if not t.get_named_type(TIL, name):
        return None
    d = ida_typeinf.udt_type_data_t()
    t.get_udt_details(d)
    return d

TYPES = {n: udt(n) for n in ('uPlayer', 'uPlayerNero', 'uPlayerDante')}

def member_at(tname, off):
    """-> (member path, pointed-to type name or None)"""
    d = TYPES.get(tname) or udt(tname)
    if d is None:
        return ('+0x%X' % off, None)
    TYPES[tname] = d
    for m in d:
        lo, hi = m.offset // 8, (m.offset + m.size) // 8
        if lo <= off < hi:
            name = m.name if off == lo else '%s+0x%X' % (m.name, off - lo)
            tgt = None
            if m.type.is_ptr():
                p = m.type.get_pointed_object()
                tgt = p.get_type_name()
            return (name, tgt)
    return ('+0x%X' % off, None)

def scan(fea, starts):
    """starts: {insn_ea: reg_name} where reg receives mpPlayer"""
    f = ida_funcs.get_func(fea)
    taint = {}   # location -> (chain list, type name)
    hits = []
    for ea in idautils.FuncItems(fea):
        insn = ida_ua.insn_t()
        if not ida_ua.decode_insn(insn, ea):
            continue
        mn = insn.get_canon_mnem()
        op0, op1 = idc.print_operand(ea, 0), idc.print_operand(ea, 1)
        # memory read through a tainted base: any operand of form [reg+disp]
        for i in (0, 1):
            op = insn.ops[i]
            if op.type in (ida_ua.o_displ, ida_ua.o_phrase):
                base = ida_idp_reg(op)
                if base in taint and not is_stack(idc.print_operand(ea, i)):
                    chain, tname = taint[base]
                    disp = op.addr & 0xFFFFFFFF if op.type == ida_ua.o_displ else 0
                    if len(chain) == 0 and disp < UPLAYER_SIZE:
                        continue          # plain uPlayer field: fine for any player
                    mem, tgt = member_at(tname if len(chain) else 'uPlayerNero', disp)
                    hits.append({"ea": "0x%X" % ea, "chain": chain + [mem], "insn": idc.generate_disasm_line(ea, 0)})
        # taint propagation (mov only)
        if mn == 'mov':
            dst, src = op0, op1
            if ea in starts:
                taint[starts[ea]] = ([], 'uPlayer')
                continue
            m = re.match(r'(?:dword ptr )?\[(e\w\w)\+?([0-9A-Fa-f]*)h?\]$', src)
            if m and m.group(1) in taint:
                chain, tname = taint[m.group(1)]
                disp = int(m.group(2), 16) if m.group(2) else 0
                if len(chain) < 3 and (chain or disp >= UPLAYER_SIZE):
                    mem, tgt = member_at(tname if chain else 'uPlayerNero', disp)
                    taint[dst] = (chain + [mem], tgt)
                    continue
            if src in taint:
                taint[dst] = taint[src]
                continue
            if dst in taint:
                del taint[dst]
        elif op0 in taint and mn in ('lea', 'xor', 'pop', 'add', 'sub', 'movzx', 'movsx', 'and', 'or'):
            del taint[op0]
        elif mn == 'call':
            for r in ('eax', 'ecx', 'edx'):
                taint.pop(r, None)
    return hits

def ida_idp_reg(op):
    import ida_idp
    return ida_idp.get_reg_name(op.reg, 4)

def is_stack(optxt):
    return 'esp' in optxt or 'ebp' in optxt

def run():
    sites = json.load(open(ROOT + r"\mpplayer_call_sites.json"))
    sites = sites['sites'] if isinstance(sites, dict) and 'sites' in sites else sites
    byfn = {}
    for s in sites:
        if s.get('deref_ea') and s.get('deref_dst'):
            byfn.setdefault(int(s['fn'], 16), {})[int(s['deref_ea'], 16)] = s['deref_dst']
    nero_str = [s.ea for s in idautils.Strings() if str(s) == 'uPlayerNero']
    strcmp_fns = {ida_funcs.get_func(x).start_ea for e in nero_str for x in idautils.DataRefsTo(e) if ida_funcs.get_func(x)}
    out = []
    for fn, starts in sorted(byfn.items()):
        hits = scan(fn, starts)
        if hits or fn in strcmp_fns:
            out.append({"fn": "0x%X" % fn, "name": ida_name.get_name(fn), "nero_strcmp": fn in strcmp_fns,
                        "chains": sorted({' -> '.join(h['chain']) for h in hits}), "hits": hits})
    json.dump({"functions": out}, open(ROOT + r"\nero_field_scan.json", "w"), indent=1)
    print({"scanned": len(byfn), "flagged": len(out), "with_fields": sum(1 for o in out if o['chains'])})

run()
