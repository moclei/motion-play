# crop.py <in.csv> <out.csv> [t0_us t1_us] — keep rows with t0 <= Time <= t1 (default -30..+40 us); original untouched
import csv, sys
src, dst = sys.argv[1], sys.argv[2]
t0, t1 = (float(sys.argv[3]), float(sys.argv[4])) if len(sys.argv) > 4 else (-30.0, 40.0)
rows = list(csv.reader(open(src)))
keep = [r for r in rows[1:] if t0 * 1e-6 <= float(r[0]) <= t1 * 1e-6]
csv.writer(open(dst, 'w', newline='')).writerows([rows[0]] + keep)
print("crop %s: %d -> %d rows, %g..%g us" % (src, len(rows) - 1, len(keep), t0, t1))
