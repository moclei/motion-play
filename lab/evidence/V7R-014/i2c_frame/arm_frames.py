# arm.py <ARM> — crop each counted capture of V7R-014 <ARM> (crop.py, -30..+40 us), run i2c_frame.py --expect D6,
# and print per capture: byte, 9th bit, SCL period, the three V_OL bit means; then the arm V_OL (mean of the 9 bit-means).
import glob, re, subprocess, sys, os
arm = sys.argv[1]; here = os.path.dirname(os.path.abspath(__file__))
caps = sorted(glob.glob('lab/captures/V7R-014/*_V7R-014_%s_[0-9][0-9].csv' % arm))
allv = []
for c in caps:
    n = re.search(r'_(\d\d)\.csv$', c).group(1); out = os.path.join(here, '%s_%s_crop.csv' % (arm, n))
    subprocess.run(['python3', 'lab/evidence/V7R-009/i2c_frame/crop.py', c, out], check=True, capture_output=True)
    r = subprocess.run(['python3', 'tools/lab/i2c_frame.py', '--expect', 'D6', out], capture_output=True, text=True).stdout
    open(out.replace('_crop.csv', '_frame.txt'), 'w').write(r)
    bits = re.search(r'SDA at SCL rising: (.*?)\s+->\s+(\S+), 9th bit (\w+)', r)
    per = re.search(r'SCL period ([\d.]+) us', r)
    vol = [float(x) for x in re.findall(r'V_OL (?:address bit [53]|R/W bit 0): ([\d.]+) mV', r)]
    allv += vol
    print('%s_%s byte=%s 9th=%s period=%s us V_OL=%s mV' % (arm, n, bits.group(2) if bits else '?', bits.group(3) if bits else '?', per.group(1) if per else '?', vol))
print('%s: %d captures, V_OL arm mean = %.2f mV (n=%d bit-means)' % (arm, len(caps), sum(allv) / len(allv), len(allv)))
# Contact control (card): CH1 idle-high before the frame, mean of CH1 over -45..-25 us of the uncropped CSV (idle gap between the INA frame, ending ~-52 us, and the D6 START at ~-20 us), >= 3.135 V.
import csv
for c in caps:
    rows = list(csv.reader(open(c)))[1:]
    v = [float(r[1]) for r in rows if r and -45e-6 <= float(r[0]) <= -25e-6]
    print('%s idle CH1 -45..-25 us: mean %.4f V, min %.4f V (n=%d)' % (os.path.basename(c), sum(v) / len(v), min(v), len(v)))
