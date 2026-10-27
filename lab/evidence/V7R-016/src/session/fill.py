# fill.py <log> <arm> <raw_observation> <v8_read> <frame_summary_file> — fills TODOs of the arm's entries (val_V8_<arm>, <arm>) with feature, raw_observation and ai_read.
import sys, re, json
log, arm, raw, v8read, frames = sys.argv[1:6]
fr = open(frames).read().strip().replace('"', "'")
s = open(log).read()
blocks = re.split(r'(?m)^(?=  - test_id:)', s)
out = []
for b in blocks:
    m = re.search(r'arm: "([^"]+)"', b)
    if m and m.group(1) in ('val_V8_' + arm, arm) and 'feature: "TODO"' in b:
        v8 = m.group(1).startswith('val_V8')
        b = b.replace('feature: "TODO"', 'feature: "%s"' % ('V8 contact check: I2C decode, address trigger 0x6B write, 20 us/div' if v8 else 'D6 frame, SDA V_OL bits 5/3/R-W (i2c_frame.py), 10 us/div'))
        b = b.replace('raw_observation: "TODO"', 'raw_observation: %s' % json.dumps(raw))
        png = re.search(r'"([^"]+\.png)"', b).group(1)
        read = v8read if v8 else fr
        b = b.replace('    source: "tools/lab/capture.py"', '    ai_read:\n      - capture: %s\n        values_seen: {summary: %s}\n        mismatch: none\n    source: "tools/lab/capture.py"' % (png, json.dumps(read)), 1)
    out.append(b)
open(log, 'w').write(''.join(out))
