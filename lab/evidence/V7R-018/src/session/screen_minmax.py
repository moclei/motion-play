# screen_minmax.py <out_prefix> — V7R-018 session helper (roll arms, option B check).
# Reads the stopped scope's screen data (:WAVeform:MODE NORMal, 1000 pts per channel, ASCII) and
# VMAX/VMIN per channel; writes <out_prefix>_screen.csv and prints min/max per channel vs VMAX/VMIN.
import socket, sys, time
H, P = "192.168.50.2", 5555
def q(cmd, wait=1.5):
    s = socket.create_connection((H, P), timeout=10); s.sendall((cmd + "\n").encode())
    if "?" not in cmd:
        time.sleep(0.3); s.close(); return ""
    buf = b""; t0 = time.time()
    s.settimeout(wait)
    try:
        while True:
            d = s.recv(65536)
            if not d: break
            buf += d
            if buf.endswith(b"\n"): break
    except socket.timeout:
        pass
    s.close(); return buf.decode().strip()
out = sys.argv[1]
cols = {}
for n in (1, 2):
    q(":WAVeform:SOURce CHANnel%d" % n); q(":WAVeform:MODE NORMal"); q(":WAVeform:FORMat ASCii")
    pre = q(":WAVeform:PREamble?").split(",")
    txt = q(":WAVeform:DATA?", 4)
    if txt.startswith("#"):
        txt = txt[2 + int(txt[1]):]
    v = [float(x) for x in txt.split(",") if x.strip()]
    cols[n] = (v, float(pre[4]), float(pre[5]))
    vmax = q(":MEASure:ITEM? VMAX,CHANnel%d" % n); vmin = q(":MEASure:ITEM? VMIN,CHANnel%d" % n)
    print("CH%d points %d dt %.3g s  screen min %.4f max %.4f V | VMAX %s VMIN %s" % (n, len(v), float(pre[4]), min(v), max(v), vmax, vmin))
with open(out + "_screen.csv", "w") as f:
    f.write("t_s,CH1_V,CH2_V\n")
    (v1, dt, t0), (v2, _, _) = cols[1], cols[2]
    for i in range(min(len(v1), len(v2))):
        f.write("%.6f,%.5f,%.5f\n" % (t0 + i * dt, v1[i], v2[i]))
print("wrote", out + "_screen.csv")
