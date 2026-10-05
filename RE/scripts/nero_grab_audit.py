"""
nero_grab_audit.py — classify every grab/buster/snatch-related function that reads
sMediator::mpPlayer, to decide how each can resolve the *grabbing* player instead.

Run in DX9 via py_exec_file (shared globals). Input: RE/mpplayer_call_sites.json.
Output: RE/nero_grab_audit.json

Per function:
  sig            prototype + SE signature (from the `SE:` function comment)
  grabber_arg    an argument typed uPlWpRightHand* / uPlayer* / uPlayerNero* exists
  nero_strcmp    references the "uPlayerNero" string (runtime class-name check)
  pl_vcall_slots vtable slots called on mpPlayer (pseudocode `mpPlayer->vtable_ptr + N`; 4=getDTI, 134=isDevilTrigger)
  nero_fields    byte offsets >= sizeof(uPlayer)=0x3270 read through mpPlayer (Nero-only state)
  pl_fields      named uPlayer fields read through mpPlayer
  accessor       uses sMediator::getPlayerPos / getPlayerMat
  stores_arg     this-offsets the function stores its 2nd arg into (cached grabber)
Plus a whole-binary sweep of every function referencing "uPlayerNero".
"""
import json, re, idc, idautils, ida_funcs, ida_hexrays, ida_bytes, ida_name, ida_typeinf

ROOT = r"C:\Tools\MCP_dev\test\re-test\RE"
UPLAYER_SIZE = 0x3270
PAT = re.compile(r'Nero|RightHand|Grab|grab|Snatch|snatch|Buster|buster|Catch|catch|Thorw|Throw|throw', re.I)

def nero_string_eas():
    out = []
    for s in idautils.Strings():
        if str(s) == 'uPlayerNero':
            out.append(s.ea)
    return out

def funcs_referencing(eas):
    fs = set()
    for ea in eas:
        for x in idautils.DataRefsTo(ea):
            f = ida_funcs.get_func(x)
            if f:
                fs.add(f.start_ea)
    return fs

def analyse(fea, nero_fs):
    r = {"fn": "0x%X" % fea, "name": ida_name.get_name(fea)}
    r["se"] = None
    c = idc.get_func_cmt(fea, 1) or ''
    m = re.search(r'SE: ([^\n@]+?) @ (0x[0-9a-fA-F]+)', c)
    if m:
        r["se"] = m.group(1).strip()
    r["prototype"] = idc.get_type(fea)
    r["nero_strcmp"] = fea in nero_fs
    try:
        cf = ida_hexrays.decompile(fea)
        txt = str(cf)
    except Exception as e:
        r["error"] = str(e)
        return r
    # variables holding mpPlayer
    pvars = set(re.findall(r'(\w+) = (?:::)?sMediator::mpInstance(?:_\d+)?->mpPlayer', txt))
    pvars |= set(re.findall(r'(\w+) = \w+->mpPlayer;', txt))
    names = '|'.join(re.escape(v) for v in pvars) or r'(?!x)x'
    # Hex-Rays prints `vtable_ptr + N` as a slot index (getDTI shows as +4), not a byte offset
    r["pl_vcall_slots"] = sorted({int(n, 0) for n in re.findall(r'\(\*\((?:%s)->vtable_ptr \+ (\w+)\)\)' % names, txt)})
    offs = set()
    for n in re.findall(r'\(\s*(?:\([^()]*\))?\s*(?:%s)\s*\+\s*(\w+)\s*\)' % names, txt):
        try:
            offs.add(int(n, 0))
        except ValueError:
            pass
    r["raw_offsets"] = sorted(offs)
    r["nero_fields"] = ["0x%X" % o for o in sorted(offs) if o >= UPLAYER_SIZE]
    r["pl_fields"] = sorted(set(re.findall(r'(?:%s)->(m\w+)' % names, txt)))
    r["accessor"] = sorted(set(re.findall(r'sMediator::(getPlayer(?:Pos|Mat))', txt)))
    r["grabber_arg"] = bool(re.search(r'uPlWpRightHand|uPlayerNero|uPlayer \*', (r["se"] or '') + ' ' + (r["prototype"] or '').split('(', 1)[-1]))
    r["stores_arg"] = sorted(set(re.findall(r'\*\(\w*this \+ (\d+)\) = a2;', txt)))
    r["mpPlayer_vars"] = sorted(pvars)
    return r

def run():
    sites = json.load(open(ROOT + r"\mpplayer_call_sites.json"))
    sites = sites['sites'] if isinstance(sites, dict) and 'sites' in sites else sites
    nero_eas = nero_string_eas()
    nero_fs = funcs_referencing(nero_eas)
    cand = {}
    for s in sites:
        fn = int(s['fn'], 16)
        if s.get('category') == 'nero-grab' or PAT.search(s.get('fn_name') or ''):
            cand.setdefault(fn, []).append(s['ea'])
    # every function doing the runtime "uPlayerNero" check is in scope too
    for f in nero_fs:
        cand.setdefault(f, [])
    out = []
    for fn, eas in sorted(cand.items()):
        r = analyse(fn, nero_fs)
        r["mpplayer_sites"] = eas
        out.append(r)
    res = {"uPlayer_size": "0x%X" % UPLAYER_SIZE, "nero_string_eas": ["0x%X" % e for e in nero_eas],
           "nero_strcmp_funcs": len(nero_fs), "functions": out}
    json.dump(res, open(ROOT + r"\nero_grab_audit.json", "w"), indent=1)
    print({"funcs": len(out), "nero_strcmp_funcs": len(nero_fs), "nero_strings": res["nero_string_eas"]})

run()
