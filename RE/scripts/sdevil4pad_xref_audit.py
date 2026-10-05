import idautils, idc, idaapi, ida_hexrays, ida_lines, json, os, re

INST = 0xE559C4
OUT = r"C:\Users\Home\AppData\Local\Temp\claude\c--Tools-MCP-dev-test-re-test\5e10dd0c-4e1d-4b0a-ad29-ca22ecc44643\scratchpad\pad_xref_audit.json"
PAD_TYPES = ("sDevil4Pad", "sPad", "sDevil4Pad::cPadInfo", "sPad::Pad")


def funcs_with_refs():
    fs = {}
    for r in idautils.DataRefsTo(INST):
        f = idaapi.get_func(r)
        fs.setdefault(f.start_ea, []).append(r)
    return dict(sorted(fs.items()))


def base_type_name(t):
    if t.is_ptr():
        t = t.get_pointed_object()
    return t.get_type_name() or ""


class V(ida_hexrays.ctree_parentee_t):
    def __init__(self, cf):
        super().__init__()
        self.cf = cf
        self.accesses = []
        self.passes = []

    def txt(self, e):
        return ida_lines.tag_remove(e.print1(None))

    def visit_expr(self, e):
        # outermost member chain rooted at a pad-typed pointer
        if e.op == ida_hexrays.cot_memptr and base_type_name(e.x.type) in PAD_TYPES:
            top = e
            i = len(self.parents) - 1
            while i >= 0:
                p = self.parents[i]
                if p.is_expr():
                    pe = p.cexpr
                    if pe.op in (ida_hexrays.cot_memref, ida_hexrays.cot_memptr) and pe.x == top:
                        top = pe; i -= 1; continue
                    if pe.op == ida_hexrays.cot_idx and pe.x == top:
                        top = pe; i -= 1; continue
                    if pe.op == ida_hexrays.cot_ref and pe.x == top:
                        top = pe; i -= 1; continue
                break
            write = False
            if i >= 0 and self.parents[i].is_expr():
                pe = self.parents[i].cexpr
                if pe.op in (ida_hexrays.cot_asg,) + tuple(getattr(ida_hexrays, n) for n in dir(ida_hexrays) if n.startswith("cot_asg")) and pe.x == top:
                    write = True
                if pe.op in (ida_hexrays.cot_preinc, ida_hexrays.cot_predec, ida_hexrays.cot_postinc, ida_hexrays.cot_postdec):
                    write = True
            self.accesses.append((top.ea if top.ea != idaapi.BADADDR else e.ea, self.txt(top), write))
        # pad object passed to a call
        if e.op == ida_hexrays.cot_call:
            for a in e.a:
                if base_type_name(a.type) in PAD_TYPES or (a.op == ida_hexrays.cot_obj and a.obj_ea == INST):
                    self.passes.append((e.ea, self.txt(e.x), self.txt(a)))
        return 0


def normalize(s):
    s = re.sub(r"^&", "", s)
    s = re.sub(r"^.*?->", "", s, count=1)
    return s


def run(start, end):
    res = json.load(open(OUT)) if os.path.exists(OUT) and start > 0 else {}
    items = list(funcs_with_refs().items())[start:end]
    for fea, refs in items:
        name = idc.get_func_name(fea)
        ent = {"ea": hex(fea), "xrefs": [hex(r) for r in refs], "accesses": [], "passes": [], "err": None}
        try:
            cf = ida_hexrays.decompile(fea)
            v = V(cf)
            v.apply_to(cf.body, None)
            seen = set()
            for ea, t, w in v.accesses:
                k = (normalize(t), w)
                if k in seen: continue
                seen.add(k)
                ent["accesses"].append({"ea": hex(ea), "expr": normalize(t), "write": w})
            ent["passes"] = [{"ea": hex(a), "callee": c, "arg": g} for a, c, g in v.passes]
        except Exception as ex:
            ent["err"] = str(ex)
        res[name] = ent
    json.dump(res, open(OUT, "w"), indent=1)
    return len(res)
