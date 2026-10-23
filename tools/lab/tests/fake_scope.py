"""A local fake DHO804 SCPI server for capture.py tests.

Replies come from recorded bench files in scope_fixtures/ (copied from
lab/inbox/phase6/, W4 S4/S5 and W4b S10 on fw 00.01.05):
  s4_queries.txt       query -> reply table (W4 S4)
  lan_raw_ascii.txt    RAW ASCii :WAVeform:DATA? at 10 kpts (W4b S10)
  lan_raw_preamble.txt its :WAVeform:PREamble? (W4b S10)
  lan_shot.tmc         :DISPlay:DATA? PNG, TMC block as received (W4 S5)
  lan_setup.tmc        :SYSTem:SETup?, TMC block as received (W4 S5)

Like the real scope it never closes the socket after a reply, so a client that
waits for EOF hangs (and times out). Replies are sent in small, uneven pieces.
"""
import socket
import threading
import time
from pathlib import Path

FIX = Path(__file__).resolve().parent / "scope_fixtures"


def load_s4():
    table = {}
    for line in (FIX / "s4_queries.txt").read_text().splitlines():
        if not line.strip():
            continue
        # columns: command padded to 35, then reply
        cmd, reply = line[:35].strip(), line[35:].strip()
        table[cmd.upper()] = reply
    return table


class FakeScope:
    def __init__(self, idn="RIGOL TECHNOLOGIES,DHO804,DHO8A282M00872,00.01.05",
                 mdepth=10000, displayed=(1,), late_terminator=False, meas=None,
                 drop_queries=()):
        self.table = load_s4()
        self.table["*IDN?"] = idn
        self.table[":ACQUIRE:MDEPTH?"] = "%.4E" % mdepth
        self.mdepth = mdepth
        self.displayed = set(displayed)
        self.late_terminator = late_terminator
        self.meas = meas or {}                    # "VAMP,CHANNEL2" -> reply
        self.drop_queries = {d.upper() for d in drop_queries}   # never answered (timeout)
        self.raw = (FIX / "lan_raw_ascii.txt").read_text().strip().split(",")
        self.preamble = (FIX / "lan_raw_preamble.txt").read_text().strip()
        self.png_block = (FIX / "lan_shot.tmc").read_bytes()
        self.setup_block = (FIX / "lan_setup.tmc").read_bytes()
        self.commands = []
        self.date, self.time = "2013-01-18", "09:52:08"
        self.status = "TD"
        self.start, self.stop = 1, 1000
        self.errors = []
        self.sock = socket.socket()
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(4)
        self.port = self.sock.getsockname()[1]
        self._stop = False
        threading.Thread(target=self._serve, daemon=True).start()

    def close(self):
        self._stop = True
        try:
            self.sock.close()
        except OSError:
            pass

    # ------------------------------------------------------------------
    def _serve(self):
        while not self._stop:
            try:
                conn, _ = self.sock.accept()
            except OSError:
                return
            threading.Thread(target=self._client, args=(conn,), daemon=True).start()

    def _send(self, conn, data):
        # uneven pieces, never a close
        i, sizes = 0, [1, 7, 4096, 13, 65536]
        k = 0
        while i < len(data):
            n = sizes[k % len(sizes)]
            conn.sendall(data[i:i + n])
            i += n
            k += 1

    def _client(self, conn):
        buf = b""
        while True:
            try:
                b = conn.recv(4096)
            except OSError:
                return
            if not b:
                return
            buf += b
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                cmd = line.decode("ascii").strip()
                self.commands.append(cmd)
                reply = self._handle(cmd)
                if reply is None:
                    continue
                if isinstance(reply, bytes):
                    if self.late_terminator and reply.endswith(b"\n"):
                        self._send(conn, reply[:-1])
                        time.sleep(0.8)          # longer than the client's 0.5 s trailer read
                        conn.sendall(b"\n")
                    else:
                        self._send(conn, reply)
                else:
                    self._send(conn, (reply + "\n").encode("ascii"))

    def _handle(self, cmd):
        u = cmd.upper()
        if u in self.drop_queries:
            return None
        if u.startswith(":SYSTEM:DATE "):
            y, m, d = [int(x) for x in cmd.split(" ", 1)[1].split(",")]
            self.date = "%04d-%02d-%02d" % (y, m, d)
            return None
        if u.startswith(":SYSTEM:TIME "):
            h, m, s = [int(x) for x in cmd.split(" ", 1)[1].split(",")]
            self.time = "%02d:%02d:%02d" % (h, m, s)
            return None
        if u == ":SYSTEM:DATE?":
            return self.date
        if u == ":SYSTEM:TIME?":
            return self.time
        if u == ":SYSTEM:ERROR?":
            return self.errors.pop(0) if self.errors else '0,"No error"'
        if u == ":STOP":
            self.status = "STOP"
            return None
        if u == ":TRIGGER:STATUS?":
            return self.status
        if u.startswith(":CHANNEL") and u.endswith(":DISPLAY?"):
            n = int(u[len(":CHANNEL")])
            return "1" if n in self.displayed else "0"
        if u.startswith(":CHANNEL") and u.endswith("?"):
            key = ":CHANNEL1" + u[len(":CHANNEL1"):]
            return self.table.get(key, "0")
        if u.startswith(":WAVEFORM:START "):
            self.start = int(cmd.split()[1])
            return None
        if u.startswith(":WAVEFORM:STOP "):
            self.stop = int(cmd.split()[1])
            return None
        if u.startswith(":WAVEFORM:") and not u.endswith("?"):
            return None
        if u == ":WAVEFORM:DATA?":
            n = self.stop - self.start + 1
            vals = [self.raw[(self.start - 1 + i) % len(self.raw)] for i in range(n)]
            return ",".join(vals)
        if u == ":WAVEFORM:PREAMBLE?":
            f = self.preamble.split(",")
            f[2] = str(self.mdepth)
            return ",".join(f)
        if u == ":DISPLAY:DATA? PNG":
            return self.png_block
        if u == ":SYSTEM:SETUP?":
            return self.setup_block
        if u.startswith(":MEASURE:ITEM? "):
            arg = u.split(" ", 1)[1]
            if arg in self.meas:
                return self.meas[arg]
            return self.table.get(u, "1.0000E+00")
        if u in self.table:
            return self.table[u]
        if u.endswith("?"):
            return "0"
        return None
