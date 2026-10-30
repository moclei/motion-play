# stopwatch.py <serial_log> <mode> <delay_s> [timeout_s] — V7R-018 session helper.
# Waits for an event in the v7 serial log, then <delay_s> later sends :STOP to the scope and
# appends "=== STOP sent (<mode>)" to the log. Modes: reboot (a diag line whose t= is below the
# previous one, or the first t= line after a gap of > 3 s), pca (any diag row with PCA:.).
import re, socket, sys, time
log, mode, delay = sys.argv[1], sys.argv[2], float(sys.argv[3])
timeout = float(sys.argv[4]) if len(sys.argv) > 4 else 600
stamp = lambda: time.strftime('%H:%M:%S') + '.000'
f = open(log); f.seek(0, 2)
last_t, last_wall, t0 = None, time.time(), time.time()
hit = None
while time.time() - t0 < timeout and not hit:
    line = f.readline()
    if not line:
        time.sleep(0.1); continue
    m = re.search(r't=\s*(\d+)', line)
    if mode == 'reboot' and m:
        t = int(m.group(1))
        if (last_t is not None and t < last_t) or (time.time() - last_wall > 3 and last_t is not None):
            hit = line.strip()
        last_t, last_wall = t, time.time()
    if mode == 'pca' and 'PCA:.' in line:
        hit = line.strip()
with open(log, 'a') as g:
    if not hit:
        g.write('%s === stopwatch timeout (%s), no STOP sent\n' % (stamp(), mode)); sys.exit(1)
    g.write('%s === stopwatch hit (%s): %s\n' % (stamp(), mode, hit))
time.sleep(delay)
s = socket.create_connection(('192.168.50.2', 5555), timeout=5); s.sendall(b':STOP\n'); time.sleep(0.5); s.close()
with open(log, 'a') as g:
    g.write('%s === STOP sent (%s, %.0f s after hit)\n' % (stamp(), mode, delay))
