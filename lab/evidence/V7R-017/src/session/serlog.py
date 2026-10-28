# serlog.py <port> <logfile> [cmdfile] — session helper (V7R-012/-013 logger, plus commands for V7R-014).
# Appends timestamped serial lines to <logfile>; reopens the port if it drops (reset, upload).
# If [cmdfile] exists, its text is written to the port, echoed into the log as ">>> <text>", and the file is deleted.
# Run with the PlatformIO python (has pyserial): ~/.platformio/penv/bin/python serlog.py ...
# Stop it (pkill -f "serlog.py <port>") before any upload on the same port.
import datetime, os, sys, time
import serial

port, path = sys.argv[1], sys.argv[2]
cmd = sys.argv[3] if len(sys.argv) > 3 else None
stamp = lambda: datetime.datetime.now().strftime('%H:%M:%S.%f')[:-3]
while True:
    try:
        with serial.Serial(port, 115200, timeout=0.2) as s, open(path, 'a', buffering=1) as f:
            buf = b''
            while True:
                if cmd and os.path.exists(cmd):
                    text = open(cmd).read().strip()
                    os.remove(cmd)
                    s.write(text.encode())
                    f.write('%s >>> %s\n' % (stamp(), text))
                buf += s.read(512)
                while b'\n' in buf:
                    line, buf = buf.split(b'\n', 1)
                    f.write(stamp() + ' ' + line.decode('utf-8', 'replace').rstrip('\r') + '\n')
    except (serial.SerialException, OSError):
        time.sleep(0.5)
