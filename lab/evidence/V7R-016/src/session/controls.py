import csv, glob, re, sys
arm = sys.argv[1]
for c in sorted(glob.glob('lab/captures/V7R-016/*_V7R-016_%s_0[0-9].csv' % arm)):
    rows = [r for r in csv.reader(open(c))][1:]
    c1 = [float(r[1]) for r in rows]; c2 = [float(r[2]) for r in rows]
    t = [float(r[0]) for r in rows]
    i2 = [c2[i] for i in range(len(t)) if -45e-6 <= t[i] <= -25e-6]
    print('%s CH1 min %.3f max %.3f | CH2 min %.3f max %.3f, idle CH2 -45..-25 us mean %.4f V' % (c.split('/')[-1], min(c1), max(c1), min(c2), max(c2), sum(i2)/len(i2)))
lines = open('lab/captures/V7R-016/2026-10-27_V7R-016_v7_01.txt').read().split('\n')
idx = max(i for i, l in enumerate(lines) if l.startswith('=== %s ' % arm))
sc_all = [l for l in lines[idx:] if '[scope]' in l]; sc = [l for l in sc_all if re.search(r' t=\d+ n=\d+ tca=\d+ ina=\d+ bq=\d+ bq_codes=\d+ sda_drv=\d+ scl_drv=\d+', l)]; print('malformed [scope] lines: %d %s' % (len(sc_all) - len(sc), [l for l in sc_all if l not in sc][:2]))
other = [l for l in lines[idx+1:] if l and '[scope]' not in l and not l.startswith('===')]
def f(l, k): return re.search(k + r'=(\S+)', l).group(1)
ts = [int(f(l, 't')) for l in sc]
print('[scope] lines %d: first %s | last %s' % (len(sc), sc[0][:13] + ' n=' + f(sc[0], 'n') + ' bq=' + f(sc[0], 'bq'), sc[-1][:13] + ' n=' + f(sc[-1], 'n') + ' bq=' + f(sc[-1], 'bq')))
n0, n1, b0, b1 = int(f(sc[0], 'n')), int(f(sc[-1], 'n')), int(f(sc[0], 'bq')), int(f(sc[-1], 'bq'))
print('BQ ACK %d / %d cycles (%.1f %%); t monotonic: %s; codes seen: %s; drv: %s; tca/ina==n all: %s' % (b1-b0, n1-n0, 100.0*(b1-b0)/max(1, n1-n0), all(b > a for a, b in zip(ts, ts[1:])), sorted(set(f(l, 'bq_codes') for l in sc)), sorted(set(f(l, 'sda_drv') + '/' + f(l, 'scl_drv') for l in sc)), all(f(l, 'tca') == f(l, 'n') == f(l, 'ina') for l in sc)))
print('non-scope lines in arm: %d %s' % (len(other), other[:3]))
