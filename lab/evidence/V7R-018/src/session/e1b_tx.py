# e1b_tx.py <csv> — V7R-018 E1b counting rule (card: Predictions). Burst = falling 1.65 V crossings on
# CH1 after the trigger with CH2 > 1.65 V at each; V_TX = median of CH1 samples < 1.65 V that are
# >= 2 samples from any CH1 1.65 V crossing and >= 1 ms after the trigger.
import csv, statistics, sys
rows = list(csv.reader(open(sys.argv[1])))
hdr = rows[0]; data = [r for r in rows[1:] if r and r[0][0] in '-0123456789']
t = [float(r[0]) for r in data]; c1 = [float(r[1]) for r in data]; c2 = [float(r[2]) for r in data]
TH = 1.65
cross = [i for i in range(1, len(c1)) if (c1[i-1] >= TH) != (c1[i] >= TH)]
fall = [i for i in cross if c1[i] < TH and t[i] > 0]
fall_ok = [i for i in fall if c2[i] > TH]
near = set(j for i in cross for j in range(i-2, i+3))
low = [c1[i] for i in range(len(c1)) if c1[i] < TH and i not in near and t[i] >= 1e-3]
print('header', hdr[:3], 'points', len(t), 'dt', t[1]-t[0])
print('falling crossings after trigger:', len(fall), ' with CH2 > 1.65 V:', len(fall_ok))
if fall:
    print('first fall t=%.3f ms, last fall t=%.3f ms' % (t[fall[0]]*1e3, t[fall[-1]]*1e3))
print('V_TX: n=%d median %.1f mV  min %.1f  max %.1f  sd %.1f' % (len(low), statistics.median(low)*1e3, min(low)*1e3, max(low)*1e3, statistics.pstdev(low)*1e3) if low else 'V_TX: no samples')
print('CH2 min after 1 ms: %.3f V' % min(c2[i] for i in range(len(t)) if t[i] >= 1e-3))
