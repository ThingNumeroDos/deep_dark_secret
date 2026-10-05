"""
uem_merge.py — merge per-group RE/uem_map/<G>.json into RE/uem_map/uem_se_dx9_map.json and
check consistency. Runs with plain Python (not IDA):  python RE/scripts/uem_merge.py

Checks:
  * every SE uEm function (from se_uem_features.json) appears in exactly one group's `methods`
  * no DX9 address is claimed by two different SE functions (within or across groups)
"""
import json, glob, os, sys, collections

ROOT = os.path.join(os.path.dirname(__file__), '..', 'uem_map')
SE_FEATS = sys.argv[1] if len(sys.argv) > 1 else None

groups = {}
for p in sorted(glob.glob(os.path.join(ROOT, '[A-Z].json'))):
    groups[os.path.basename(p)[0]] = json.load(open(p))

rows, by_se, by_dx = [], collections.defaultdict(list), collections.defaultdict(list)
for g, d in groups.items():
    for m in d.get('methods', []):
        m = dict(m, group=g)
        rows.append(m)
        by_se[m['se_ea']].append(m)
        if m.get('dx9_ea') and m.get('confidence') in ('high', 'medium'):
            by_dx[m['dx9_ea'].lower()].append(m)

dup_se = {k: [r['group'] for r in v] for k, v in by_se.items() if len(v) > 1}
dup_dx = {k: [(r['group'], r['se_name'], r['confidence']) for r in v]
          for k, v in by_dx.items() if len(v) > 1}
missing = []
if SE_FEATS:
    se = json.load(open(SE_FEATS))['funcs']
    missing = sorted(set(se) - set(by_se))

stats = collections.defaultdict(lambda: collections.Counter())
for r in rows:
    cls = r['se_name'].split('::')[0]
    stats[cls]['se'] += 1
    stats[cls][r.get('confidence') or 'none'] += 1
    stats[cls]['act_' + (r.get('action') or 'none')] += 1

out = {'groups': sorted(groups), 'classes': {}, 'methods': rows,
       'checks': {'dup_se': dup_se, 'dup_dx9': dup_dx, 'missing_se': missing}}
for g, d in groups.items():
    for c, v in d.get('classes', {}).items():
        out['classes'][c] = dict(v, group=g, stats=dict(stats.get(c, {})))
json.dump(out, open(os.path.join(ROOT, 'uem_se_dx9_map.json'), 'w'), indent=1)

tot = collections.Counter()
for c in stats.values():
    tot.update(c)
print('groups', sorted(groups), 'rows', len(rows))
print('totals', dict(tot))
print('dup_se', len(dup_se), 'dup_dx9', len(dup_dx), 'missing_se', len(missing))
for k, v in list(dup_dx.items())[:40]:
    print('  DUP', k, v)
