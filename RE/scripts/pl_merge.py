"""
pl_merge.py — merge per-group RE/pl_map/P<n>.json (DX9-first player mapping) into
RE/pl_map/pl_dx9_se_map.json and check consistency. Plain Python:
    python RE/scripts/pl_merge.py <dx9_pl_features.json>

Checks:
  * every DX9 function in the feature dump appears in exactly one group's `functions`
  * SE methods claimed by >1 DX9 function (legit when DX9 kept per-class copies of code SE
    hoisted into uPlayer; suspicious otherwise — listed for review)
"""
import json, glob, os, sys, collections

ROOT = os.path.join(os.path.dirname(__file__), '..', 'pl_map')
groups = {os.path.basename(p)[:-5]: json.load(open(p)) for p in sorted(glob.glob(os.path.join(ROOT, 'P[0-9].json')))}

rows, by_dx, by_se = [], collections.defaultdict(list), collections.defaultdict(list)
for g, d in groups.items():
    for f in d.get('functions', []):
        f = dict(f, group=g)
        rows.append(f)
        by_dx[f['dx9_ea'].lower()].append(g)
        if f.get('se_ea') and f.get('confidence') in ('high', 'medium'):
            by_se[f['se_ea'].lower()].append(f)

missing = []
if len(sys.argv) > 1:
    dx = json.load(open(sys.argv[1]))['funcs']
    missing = sorted(set(k.lower() for k in dx) - set(by_dx))
dup_dx = {k: v for k, v in by_dx.items() if len(v) > 1}
multi_se = {k: [(r['group'], r['dx9_ea'], r.get('new_dx9_name'), r['confidence']) for r in v]
            for k, v in by_se.items() if len(v) > 1}

stats = collections.Counter()
for r in rows:
    stats[r.get('confidence') or 'none'] += 1
    stats['act_' + (r.get('action') or 'none')] += 1
per_group = {g: collections.Counter(f.get('confidence') or 'none' for f in d.get('functions', [])) for g, d in groups.items()}

out = {'groups': sorted(groups), 'classes': {}, 'functions': rows,
       'checks': {'missing_dx9': missing, 'dup_dx9': dup_dx, 'multi_dx9_per_se': multi_se}}
for g, d in groups.items():
    for c, v in d.get('classes', {}).items():
        out['classes'].setdefault(c, []).append(dict(v, group=g))
json.dump(out, open(os.path.join(ROOT, 'pl_dx9_se_map.json'), 'w'), indent=1)

print('groups', sorted(groups), 'rows', len(rows))
print('totals', dict(stats))
for g, c in per_group.items():
    print(' ', g, dict(c))
print('missing_dx9', len(missing), 'dup_dx9', len(dup_dx), 'multi_dx9_per_se', len(multi_se))
for k, v in list(multi_se.items())[:40]:
    print('  MULTI', k, v)
