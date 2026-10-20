"""Tests for capture.py, validate_log.py (+ its pre-commit rule) and ingest_usb.py.

Called from run_tests.py. capture.py runs against fake_scope.FakeScope, which replays the
Phase 6 bench recordings in scope_fixtures/. No real scope is needed.
"""
import datetime
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
LAB = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(LAB))

import capture  # noqa: E402
import validate_log  # noqa: E402
from fake_scope import FakeScope, FIX  # noqa: E402

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None

NOW = "2026-11-04T10:42:05"
_results = []


def check(name, ok, detail=""):
    _results.append(ok)
    print("%s %s%s" % ("PASS" if ok else "FAIL", name, "" if ok else "\n  " + str(detail)))


def run(cmd, cwd=None):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       universal_newlines=True, cwd=cwd)
    return p.returncode, p.stdout


def run_capture(root, fake, *extra):
    return run([sys.executable, str(LAB / "capture.py"), "--test", "V7R-012", "--arm", "A1",
                "--host", "127.0.0.1", "--port", str(fake.port), "--root", str(root),
                "--now", NOW] + list(extra))


def payload(tmc):
    n = int(tmc[1:2])
    return tmc[2 + n:2 + n + int(tmc[2:2 + n])]


# ---------------------------------------------------------------- capture.py

def capture_tests(tmp):
    raw = (FIX / "lan_raw_ascii.txt").read_text().strip().split(",")

    # 1. basic capture, with an invalid measurement
    root = tmp / "c1"
    (root / "lab" / "log").mkdir(parents=True)
    f = FakeScope(meas={"VAMP,CHANNEL1": "9.9000E+37"})
    rc, out = run_capture(root, f)
    f.close()
    cap = root / "lab" / "captures" / "V7R-012"
    stem = "2026-11-04_V7R-012_A1_01"
    names = sorted(p.name for p in cap.iterdir()) if cap.is_dir() else []
    check("capture: exit 0 and §4.4 names", rc == 0 and names == sorted(
        [stem + ".png", stem + ".csv", stem + ".setup.bin"]), out + str(names))
    if rc != 0:
        return
    check("capture: PNG = :DISPlay:DATA? payload, TMC header stripped",
          (cap / (stem + ".png")).read_bytes() == payload((FIX / "lan_shot.tmc").read_bytes()))
    check("capture: setup file = :SYSTem:SETup? payload",
          (cap / (stem + ".setup.bin")).read_bytes() == payload((FIX / "lan_setup.tmc").read_bytes()))
    rows = (cap / (stem + ".csv")).read_text().splitlines()
    vals = [r.split(",")[1] for r in rows[1:]]
    check("capture: CSV holds the 10 000 RAW values verbatim", rows[0] == "Time(s),CH1V" and vals == raw,
          "%s / %d values" % (rows[0], len(vals)))
    t0, t1 = float(rows[1].split(",")[0]), float(rows[2].split(",")[0])
    check("capture: CSV time axis = PREamble xorg + i*xinc", abs(t0 + 2e-3) < 1e-12 and abs((t1 - t0) - 4e-7) < 1e-12,
          rows[1:3])

    cmds = [c.upper() for c in f.commands]
    check("capture: never sends :SAVE:SETup / :SAVE:MEMory / :SAVE:STATus?",
          not any(c.startswith((":SAVE:SET", ":SAVE:MEM", ":SAVE:STAT")) for c in cmds))
    check("capture: :STOP before the RAW read; STARt 1 / STOP 10000",
          ":STOP" in cmds and cmds.index(":STOP") < cmds.index(":WAVEFORM:MODE RAW")
          and ":WAVEFORM:START 1" in cmds and ":WAVEFORM:STOP 10000" in cmds)
    check("capture: clock set in comma form from the Mac time",
          ":SYSTEM:DATE 2026,11,4" in cmds and ":SYSTEM:TIME 10,42,5" in cmds)

    log = root / "lab" / "log" / "2026-11-04_s01.yaml"
    data = yaml.safe_load(log.read_text())
    m = data["measurements"][0]
    vamp = [v for v in m["values"] if v["name"] == "VAMP"][0]
    vtop = [v for v in m["values"] if v["name"] == "VTOP"][0]
    check("capture: 9.9E37 recorded as valid: false, no number",
          vamp.get("valid") is False and not any(k.startswith("value") for k in vamp), vamp)
    check("capture: valid measurement in mV with the raw reply", vtop.get("value_mV") == 2977.5 and vtop["raw"] == "2.9775E+00", vtop)
    check("capture: channels filled from the scope (ratio, bw_limit), operator fields TODO",
          data["channels"]["CH1"]["ratio"] == "10x" and data["channels"]["CH1"]["bw_limit"] == "OFF"
          and data["channels"]["CH1"]["signal"] == "TODO" and m["feature"] == "TODO" and m["raw_observation"] == "TODO",
          data["channels"])
    rep = validate_log.validate_text(log.read_text(), log.stem)
    check("capture: generated log has no validator errors, only TODOs (exit 3)",
          not rep.errors and rep.todos and rep.exit_code() == 3, rep.errors)
    check("capture: clock read back ok", m["scope_clock"]["ok"] is True, m["scope_clock"])

    # 2. second capture into the same session: nn = 02, comments kept, entry appended
    log.write_text("# operator comment kept\n" + log.read_text())
    f = FakeScope()
    rc, out = run_capture(root, f)
    f.close()
    data = yaml.safe_load(log.read_text())
    check("capture: second capture -> _02, appended to the same log, comments kept",
          rc == 0 and (cap / "2026-11-04_V7R-012_A1_02.png").exists() and len(data["measurements"]) == 2
          and log.read_text().startswith("# operator comment kept"), out)

    # 3. deeper memory is refused, nothing written
    root3 = tmp / "c3"
    f = FakeScope(mdepth=100000)
    rc, out = run_capture(root3, f)
    f.close()
    check("capture: memory depth > 10k refused (exit 2), nothing written",
          rc == 2 and "10k" in out and not (root3 / "lab").exists(), out)

    # 4. --chunked reads 10k windows
    root4 = tmp / "c4"
    f = FakeScope(mdepth=20000)
    rc, out = run_capture(root4, f, "--chunked")
    f.close()
    csvf = root4 / "lab" / "captures" / "V7R-012" / (stem + ".csv")
    nrows = len(csvf.read_text().splitlines()) - 1 if csvf.exists() else -1
    reads = [c.upper() for c in f.commands].count(":WAVEFORM:DATA?")
    d4 = yaml.safe_load((root4 / "lab" / "log" / "2026-11-04_s01.yaml").read_text()) if rc == 0 else {}
    check("capture: --chunked 20k = 2 reads, 20 000 rows, marked unverified",
          rc == 0 and nrows == 20000 and reads == 2
          and "unverified" in d4["measurements"][0]["waveform"]["read"], out)

    # 5. late TMC terminator: resync keeps later replies aligned
    root5 = tmp / "c5"
    f = FakeScope(late_terminator=True)
    rc, out = run_capture(root5, f)
    f.close()
    d5 = yaml.safe_load((root5 / "lab" / "log" / "2026-11-04_s01.yaml").read_text()) if rc == 0 else {}
    ok = rc == 0 and d5["measurements"][0]["values"][0]["raw"] == "2.9775E+00"
    check("capture: late block terminator -> resync, replies stay aligned", ok, out)

    # 6. other firmware refused
    f = FakeScope(idn="RIGOL TECHNOLOGIES,DHO804,X,00.01.06")
    rc, out = run_capture(tmp / "c6", f)
    f.close()
    check("capture: firmware other than 00.01.05 refused", rc == 2 and "00.01.06" in out, out)

    # 7. two channels -> one CSV, two columns
    root7 = tmp / "c7"
    f = FakeScope(displayed=(1, 2))
    rc, out = run_capture(root7, f)
    f.close()
    csvf = root7 / "lab" / "captures" / "V7R-012" / (stem + ".csv")
    head = csvf.read_text().splitlines()[0] if csvf.exists() else ""
    check("capture: two displayed channels -> Time(s),CH1V,CH2V", rc == 0 and head == "Time(s),CH1V,CH2V", out)

    # 8. a query with no reply (timeout) is recorded, capture continues
    root8 = tmp / "c8"
    f = FakeScope(drop_queries=[":MEASure:ITEM? VPP,CHANnel1"])
    rc, out = run_capture(root8, f, "--timeout", "1")
    f.close()
    d8 = yaml.safe_load((root8 / "lab" / "log" / "2026-11-04_s01.yaml").read_text()) if rc == 0 else {}
    vpp = [v for v in d8["measurements"][0]["values"] if v["name"] == "VPP"][0] if d8 else {}
    check("capture: unanswered measurement -> valid: false, capture still completes",
          rc == 0 and vpp.get("valid") is False and d8["measurements"][0]["scpi_errors"], out)

    # 9. the forbidden-command guard
    sc = capture.Scope(client=None)
    try:
        sc.w(":SAVE:SETup D:/x.stp")
        check("capture: guard refuses :SAVE:SETup", False)
    except capture.Refused:
        check("capture: guard refuses :SAVE:SETup", True)

    # 10. the YAML emitter round-trips awkward values through PyYAML
    obj = {"a": 1e-06, "b": "OFF", "c": "0x6B", "d": None, "e": True, "f": "x #y", "g": -2.994604,
           "h": [{"k": 9.9e37, "l": "yes"}], "i": {"j": {"k": 2e-4}}, "m": []}
    back = yaml.safe_load(capture.dump_yaml(obj))
    check("capture: YAML emitter round-trips through PyYAML", back == obj, capture.dump_yaml(obj))


# ---------------------------------------------------------------- validate_log.py + hook

def validator_tests(tmp):
    lf = HERE / "log_fixtures"
    for p in sorted((lf / "pass").glob("*.yaml")):
        rc, out = run([sys.executable, str(LAB / "validate_log.py"), str(p)])
        check("validate_log: pass/%s -> exit 0" % p.name, rc == 0, out)
    fail = lf / "fail" / "2026-11-04_s02.yaml"
    rep = validate_log.validate_text(fail.read_text(), fail.stem)
    expected = fail.read_text().count("# FAIL")
    check("validate_log: fail fixture -> one error per FAIL marker (%d)" % expected,
          len(rep.errors) == expected and rep.exit_code() == 1, "\n  ".join(rep.errors))
    tpl = LAB.parents[1] / "lab" / "templates" / "log.yaml"
    rep = validate_log.validate_text(tpl.read_text(), "2026-11-04_s01")
    check("validate_log: lab/templates/log.yaml is valid", not rep.errors, rep.errors)

    # pre-commit rule 4, in a scratch repo
    repo = tmp / "hookrepo"
    (repo / "lab" / "log").mkdir(parents=True)
    run(["git", "init", "-q"], cwd=str(repo))
    run(["git", "config", "user.email", "t@t"], cwd=str(repo))
    run(["git", "config", "user.name", "t"], cwd=str(repo))
    hook = [sys.executable, str(LAB / "precommit.py")]
    shutil.copy(str(fail), str(repo / "lab" / "log" / fail.name))
    run(["git", "add", "-A"], cwd=str(repo))
    rc, out = run(hook, cwd=str(repo))
    check("precommit: staged invalid log rejected", rc == 1 and "validation.passed" in out, out)
    run(["git", "rm", "-q", "--cached", "lab/log/" + fail.name], cwd=str(repo))
    os.remove(str(repo / "lab" / "log" / fail.name))
    good = lf / "pass" / "2026-11-04_s01.yaml"
    shutil.copy(str(good), str(repo / "lab" / "log" / good.name))
    run(["git", "add", "-A"], cwd=str(repo))
    rc, out = run(hook, cwd=str(repo))
    check("precommit: staged valid log accepted", rc == 0, out)
    p = repo / "lab" / "log" / good.name
    p.write_text(p.read_text().replace('feature: "SDA, master-driven 0-bit, flat region"', 'feature: "TODO"'))
    run(["git", "add", "-A"], cwd=str(repo))
    rc, out = run(hook, cwd=str(repo))
    check("precommit: TODO fields warn but do not reject", rc == 0 and "TODO" in out, out)


# ---------------------------------------------------------------- ingest_usb.py

def ingest_tests(tmp):
    stick = tmp / "stick"
    stick.mkdir()
    (stick / ".Spotlight-V100").mkdir()
    (stick / "._p6img0.png").write_bytes(b"appledouble")
    at = datetime.datetime(2026, 11, 4, 10, 42)
    files = {  # name -> stick mtime (stick runs ~1 h ahead of the Mac)
        "p6img0.png": at + datetime.timedelta(minutes=60, seconds=20),
        "p6wav0.csv": at + datetime.timedelta(minutes=60, seconds=40),
        "old0.png": datetime.datetime(2013, 1, 18, 9, 52),
    }
    for n, t in files.items():
        (stick / n).write_bytes(n.encode())
        ts = t.timestamp()
        os.utime(str(stick / n), (ts, ts))
    before = sorted((p.name, p.stat().st_mtime) for p in stick.iterdir())

    root = tmp / "i1"
    ing = [sys.executable, str(LAB / "ingest_usb.py"), "--src", str(stick), "--test", "V7R-012",
           "--arm", "A1", "--root", str(root), "--now", "2026-11-04T12:00:00"]
    rc, out = run(ing + ["--at", "2026-11-04T10:42"])
    cap = root / "lab" / "captures" / "V7R-012"
    got = sorted(p.name for p in cap.glob("2026-*")) if cap.is_dir() else []
    check("ingest: time match with the +60 min stick offset, §4.4 names",
          rc == 0 and got == ["2026-11-04_V7R-012_A1_01.csv", "2026-11-04_V7R-012_A1_01.png"], out)
    inbox = list((root / "lab" / "inbox").glob("usb-*/*"))
    check("ingest: whole stick copied to inbox, hidden files skipped",
          sorted(p.name for p in inbox) == sorted(files), [p.name for p in inbox])
    check("ingest: content kept", (cap / "2026-11-04_V7R-012_A1_01.png").read_bytes() == b"p6img0.png")
    check("ingest: INGEST.tsv records the mapping", (cap / "INGEST.tsv").exists()
          and "p6img0.png" in (cap / "INGEST.tsv").read_text())

    # reported name without its index digit, second ingest -> _02, inbox not re-copied
    rc, out = run(ing + ["--at", "2026-11-04T10:42", "--files", "p6img.png"])
    check("ingest: reported name without the index digit matches; next nn = 02; no re-copy",
          rc == 0 and (cap / "2026-11-04_V7R-012_A1_02.png").exists() and "0 new" in out, out)

    # ambiguity: two PNGs near the time -> nothing renamed
    (stick / "p6img1.png").write_bytes(b"second")
    ts = (at + datetime.timedelta(minutes=61)).timestamp()
    os.utime(str(stick / "p6img1.png"), (ts, ts))
    n_before = len(list(cap.glob("2026-*")))
    rc, out = run(ing + ["--at", "2026-11-04T10:42"])
    check("ingest: two PNGs in the window -> ambiguous, exit 1, nothing renamed",
          rc == 1 and "ambiguous" in out and len(list(cap.glob("2026-*"))) == n_before, out)
    rc, out = run(ing + ["--at", "2026-11-04T10:42", "--files", "p6img.png"])
    check("ingest: --files p6img.png with p6img0 and p6img1 both near --at -> ambiguous",
          rc == 1 and "ambiguous" in out, out)
    rc, out = run(ing + ["--at", "2026-11-04T10:42", "--files", "p6img1.png", "--dry-run"])
    check("ingest: exact name resolves it (dry run writes nothing)",
          rc == 0 and "would write" in out and len(list(cap.glob("2026-*"))) == n_before, out)

    rc, out = run(ing + ["--at", "2026-11-05T09:00"])
    check("ingest: no file near --at -> exit 1", rc == 1 and "no scope file" in out, out)

    os.remove(str(stick / "p6img1.png"))
    after = sorted((p.name, p.stat().st_mtime) for p in stick.iterdir())
    check("ingest: stick untouched (names and mtimes)", before == after, (before, after))


def main():
    if yaml is None:
        print("FAIL tool tests need PyYAML")
        return 1
    tmp = Path(tempfile.mkdtemp(prefix="labtools-"))
    try:
        capture_tests(tmp)
        validator_tests(tmp)
        ingest_tests(tmp)
    finally:
        shutil.rmtree(str(tmp), ignore_errors=True)
    return sum(1 for r in _results if not r)


if __name__ == "__main__":
    n = main()
    print("\n%s: %d failure(s)" % ("OK" if not n else "FAILED", n))
    sys.exit(1 if n else 0)
