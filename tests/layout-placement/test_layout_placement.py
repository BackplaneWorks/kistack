#!/usr/bin/env python3
"""Headless checks of skills/layout-placement on synthetic boards.

    KICAD_CLI=/path/to/kicad-cli python3 tests/layout-placement/test_layout_placement.py [--v18 DIR]

Starts its own `kicad-cli api-server` processes on boards made by
make_fixture.py in a temporary folder (never a real project, never a
Backplane server: every script gets KICAD_API_SOCKET or
LAYOUT_PLACEMENT_SOCKETS pointing at this test's own sockets). The skill's
scripts run through scripts/run.sh, so the first run also sets up their
Python environment from requirements.txt.

--skill DIR: test another copy of the skill (a packaged one) instead.
--v18 DIR: the frozen v18 skill folder; its route_check.py and
placement_audit.py must print the same as this copy's on a board whose rules
are v18's built-in ones.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.normpath(os.path.join(HERE, "..", "..", "skills", "layout-placement"))
FAILS = []
PASSES = []


def check(name, ok, detail=""):
    (PASSES if ok else FAILS).append(name)
    print(("ok   " if ok else "FAIL ") + name + ("" if ok or not detail else "\n     " + detail.replace("\n", "\n     ")))


def sha(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def fixture(d, name="fixture", *extra):
    subprocess.run([sys.executable, "-I", os.path.join(HERE, "make_fixture.py"), d, "--name", name, *extra], check=True)
    return os.path.join(d, name + ".kicad_pcb")


class Server:
    def __init__(self, cli, board, sockdir):
        os.makedirs(sockdir, exist_ok=True)
        self.sock = os.path.join(sockdir, "api.sock")
        env = dict(os.environ)
        env.pop("DISPLAY", None)
        env.pop("WAYLAND_DISPLAY", None)
        self.log = open(os.path.join(sockdir, "server.log"), "w")
        self.p = subprocess.Popen([cli, "api-server", "--socket", self.sock, "--parent-pid", str(os.getpid()),
                                   "--idle-exit", "600", board], stdout=self.log, stderr=subprocess.STDOUT, env=env,
                                  start_new_session=True)
        for _ in range(120):
            if os.path.exists(self.sock):
                break
            if self.p.poll() is not None:
                raise SystemExit(f"api-server exited {self.p.returncode}; see {self.log.name}")
            time.sleep(0.25)
        else:
            raise SystemExit("api-server did not open its socket")
        time.sleep(0.5)

    @property
    def url(self):
        return "ipc://" + self.sock

    def stop(self):
        if self.p.poll() is None:
            self.p.send_signal(signal.SIGTERM)
            try:
                self.p.wait(10)
            except subprocess.TimeoutExpired:
                self.p.kill()
        self.log.close()


def run(script, *args, env=None, extra_env=None):
    e = dict(os.environ)
    e.pop("KICAD_API_SOCKET", None)
    e.update(env or {})
    e.update(extra_env or {})
    return subprocess.run([os.path.join(SKILL, "scripts", "run.sh"), script, *args], capture_output=True, text=True, env=e, timeout=600)


def pose_of(board, ref, sock):
    """A footprint's (x, y, rot, side) as the server sees it, through the skill's own loader."""
    code = ("import sys; sys.path.insert(0, sys.argv[1]); import ipc_board as g; "
            "f = g.by_ref(g.load(sys.argv[2]))[sys.argv[3]]; print(f'{f.x:.4f} {f.y:.4f} {f.rot:.1f} {f.layer}')")
    py = venv_python()
    r = subprocess.run([py, "-s", "-c", code, os.path.join(SKILL, "scripts"), board, ref], capture_output=True,
                       text=True, env={**os.environ, "KICAD_API_SOCKET": sock, "PYTHONDONTWRITEBYTECODE": "1"})
    if r.returncode:
        raise SystemExit(r.stderr)
    return r.stdout.split()


def venv_python():
    with open(os.path.join(SKILL, "requirements.txt"), "rb") as f:
        h = hashlib.sha256(f.read()).hexdigest()[:16]
    base = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    return os.path.join(base, "kistack", "layout-placement", h, "bin", "python")


FAULT = r'''
import json, os, runpy, sys
sys.path.insert(0, sys.argv[1])
from kipy.board import Board
real_push, real_fps = Board.push_commit, Board.get_footprints
state = {}
action = os.environ.get("FAULT", "count")
board = sys.argv[3]
def push(self, c, m=""):
    state["moved"] = m.startswith("move")
    out = real_push(self, c, m)
    # another writer, right after the move's commit
    if state["moved"] and action == "sidecar":
        p = board + ".backplane.json"
        d = json.load(open(p))
        d["x-other-writer"] = True
        json.dump(d, open(p, "w"))
    if state["moved"] and action == "board":
        open(board, "a").write("\n")
    return out
real_save = Board.save
def save(self):
    real_save(self)
    # a save that loses an extension record
    if action == "drop-ext":
        p = board + ".backplane.json"
        d = json.load(open(p))
        d["extensions"].pop("x-sentinel-item", None)
        json.dump(d, open(p, "w"))
Board.save = save
def fps(self):
    out = list(real_fps(self))
    # right after the move's commit only: pretend a footprint vanished
    return out[:-1] if state.get("moved") and action == "count" else out
Board.push_commit, Board.get_footprints = push, fps
sys.argv = [sys.argv[2]] + sys.argv[3:]
runpy.run_path(sys.argv[0], run_name="__main__")
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--v18", help="the frozen v18 layout-placement folder, to compare outputs")
    ap.add_argument("--v19", help="the frozen v19 layout-placement folder, to compare its RF chain output")
    ap.add_argument("--v20", help="the frozen v20 layout-placement folder, to compare its RF chain and tie output")
    ap.add_argument("--keep", action="store_true", help="keep the temporary folder")
    ap.add_argument("--skill", help="the layout-placement folder to test (default: this repository's), "
                                    "e.g. a packaged copy")
    a = ap.parse_args()
    global SKILL
    if a.skill:
        SKILL = os.path.realpath(a.skill)
    print("testing", SKILL)
    cli = os.environ.get("KICAD_CLI") or os.environ.get("BACKPLANE_KICAD_CLI") or shutil.which("kicad-cli")
    if not cli:
        sys.exit("set KICAD_CLI to a kicad-cli with api-server")
    tmp = tempfile.mkdtemp(prefix="layout-placement-test.")
    servers = []
    try:
        proj = os.path.join(tmp, "proj")
        board = fixture(os.path.join(proj, "board"))
        with open(os.path.join(proj, ".backplane.json"), "w") as f:
            json.dump({"pcb": "board/fixture.kicad_pcb", "other": "kept"}, f)
        other = fixture(os.path.join(proj, "alt"), "other")
        bare = fixture(os.path.join(tmp, "bare"), "bare", "--no-project")
        wide = fixture(os.path.join(tmp, "wide"), "wide", "--track", "0.2", "--clearance", "0.15", "--via", "0.6")
        companion = board + ".backplane.json"
        with open(board) as f:
            u1 = re.search(r'\(footprint "fixture:R1" \(layer "F.Cu"\) \(uuid "([0-9a-f-]+)"\)', f.read()).group(1)
        # KiCad removes a companion file with no items, so give U1 a property to keep
        # sentinels: entries of other tools and keys this KiCad does not know
        meta = {"format": "backplane-kicad-metadata", "version": 1,
                "items": {u1: {"custom_properties": {"fixture.note": "kept"}, "x-sentinel-field": "keep"},
                          "x-sentinel-item": {"x-note": "keep", "nested": {"a": 1}}}}
        want_ext = {u1: {"x-sentinel-field": "keep"}, "x-sentinel-item": {"x-note": "keep", "nested": {"a": 1}}}
        with open(companion, "w") as f:
            json.dump(meta, f)
        shutil.copy(companion, os.path.join(tmp, "companion.orig"))
        s1 = Server(cli, board, os.path.join(tmp, "s1"))
        servers.append(s1)
        s2 = Server(cli, other, os.path.join(tmp, "s2"))
        servers.append(s2)
        S1 = {"KICAD_API_SOCKET": s1.url}

        # reading, and the environment set up from scratch
        r = run("pin_sides.py", board, "U1", env=S1)
        check("pin_sides reads the board", r.returncode == 0 and "pin   1 VDD" in r.stdout, r.stderr + r.stdout)
        check("python environment is the private one", os.path.exists(venv_python()), venv_python())
        r = run("pin_sides.py", board, "U9", env=S1)
        check("unknown part refused", r.returncode != 0 and "no footprint U9" in r.stderr, r.stderr)

        # binding to the right board
        r = run("pin_sides.py", board, "U1", env={"KICAD_API_SOCKET": s2.url})
        check("socket with another board refused", r.returncode != 0 and "not " + os.path.realpath(board) in r.stderr,
              r.stderr)
        r = run("pin_sides.py", other, "U1", env={"KICAD_API_SOCKET": s2.url})
        check("board that is not the project's refused", r.returncode != 0 and "is not the project's board" in r.stderr,
              r.stderr)
        r = run("pin_sides.py", other, "U1", env={"KICAD_API_SOCKET": s2.url, "LAYOUT_PLACEMENT_ALTERNATE": "1"})
        check("alternate board allowed when asked", r.returncode == 0, r.stderr)
        globs = os.path.join(tmp, "s*", "api.sock")
        r = run("pin_sides.py", board, "U1", env={"LAYOUT_PLACEMENT_SOCKETS": globs})
        check("discovery finds the one server with the board", r.returncode == 0, r.stderr)
        s3 = Server(cli, board, os.path.join(tmp, "s3"))
        servers.append(s3)
        r = run("pin_sides.py", board, "U1", env={"LAYOUT_PLACEMENT_SOCKETS": globs})
        check("two servers with the board refused", r.returncode != 0 and "2 KiCad servers have" in r.stderr, r.stderr)
        s3.stop()
        servers.remove(s3)
        r = run("pin_sides.py", board, "U1", env={"LAYOUT_PLACEMENT_SOCKETS": os.path.join(tmp, "none", "*.sock")})
        check("no server refused", r.returncode != 0 and "no KiCad API server has" in r.stderr, r.stderr)

        # moves: refused before anything changes
        before_file = sha(board)
        before_c1 = pose_of(board, "C1", s1.url)
        for args, word in ((["C1=105,95,90", "C1=105,96,0"], "repeated: C1"), (["C1=105,95"], "bad move"),
                           (["C1=105,x,90"], "bad move"), (["C1=105,95,90,Q"], "bad move"),
                           (["C1=nan,95,90"], "bad move"), (["C9=105,95,90"], "no footprint C9")):
            r = run("move.py", board, *args, "--save", env=S1)
            check(f"move {' '.join(args)} refused", r.returncode != 0 and word in r.stderr, r.stderr)
        check("refused moves left the server alone", pose_of(board, "C1", s1.url) == before_c1)
        check("refused moves left the file alone", sha(board) == before_file)

        # a move without --save changes the server, not the file
        r = run("move.py", board, "C1=104.5,98.5,90", env=S1)
        check("move without --save", r.returncode == 0 and "not saved" in r.stdout, r.stderr + r.stdout)
        check("server has the move", pose_of(board, "C1", s1.url)[:3] == ["104.5000", "98.5000", "90.0"],
              str(pose_of(board, "C1", s1.url)))
        check("file unchanged without --save", sha(board) == before_file)

        # an integrity failure after the commit puts the parts back
        fault = os.path.join(tmp, "fault.py")
        with open(fault, "w") as f:
            f.write(FAULT)
        e = {**os.environ, **S1, "PYTHONDONTWRITEBYTECODE": "1"}
        r = subprocess.run([venv_python(), "-s", fault, os.path.join(SKILL, "scripts"),
                            os.path.join(SKILL, "scripts", "move.py"), board, "C1=103,97,0", "--save"],
                           capture_output=True, text=True, env=e)
        check("integrity failure reported", r.returncode != 0 and "footprint count changed" in r.stderr
              and "the parts were put back" in r.stderr, r.stderr)
        check("integrity failure restored the part", pose_of(board, "C1", s1.url)[:3] == ["104.5000", "98.5000", "90.0"],
              str(pose_of(board, "C1", s1.url)))
        check("integrity failure did not save", sha(board) == before_file)

        # a side change is a real flip, and a failure after it is undone too
        r = subprocess.run([venv_python(), "-s", fault, os.path.join(SKILL, "scripts"),
                            os.path.join(SKILL, "scripts", "move.py"), board, "C2=114,103,0,B"],
                           capture_output=True, text=True, env=e)
        c2 = pose_of(board, "C2", s1.url)
        check("failed flip and move put back", r.returncode != 0 and "put back where they were" in r.stderr
              and c2[:2] == ["113.8000", "101.0000"] and c2[3] == "F.Cu", r.stderr + str(c2))
        r = run("move.py", board, "C2=114,103,0,B", env=S1)
        c2 = pose_of(board, "C2", s1.url)
        check("flip to B", r.returncode == 0 and c2 == ["114.0000", "103.0000", "0.0", "B.Cu"], r.stderr + str(c2))
        code = ("import sys; sys.path.insert(0, sys.argv[1]); import ipc_board as g; "
                "f = g.by_ref(g.load(sys.argv[2]))['C2']; "
                "print(sorted({l for p in f.pads for l in p.layers}), f.courtyard is not None)")
        rr = subprocess.run([venv_python(), "-s", "-c", code, os.path.join(SKILL, "scripts"), board],
                            capture_output=True, text=True,
                            env={**os.environ, **S1, "PYTHONDONTWRITEBYTECODE": "1"})
        check("flipped part has its pads and courtyard on B", rr.stdout.strip() == "['B.Cu'] True",
              rr.stdout + rr.stderr)
        r = run("move.py", board, "U1=110,100,0", env=S1)
        check("part with a paste-only pad moves", r.returncode == 0, r.stderr)
        r = run("move.py", board, "R1=104,104.5,0", env=S1)
        check("part with custom properties refused (the update would drop them)", r.returncode != 0
              and "R1 has custom properties" in r.stderr and "Nothing was changed" in r.stderr, r.stderr)
        r = run("move.py", board, "C2=113.8,101,0,F", env=S1)
        c2 = pose_of(board, "C2", s1.url)
        check("flip back to F", r.returncode == 0 and c2 == ["113.8000", "101.0000", "0.0", "F.Cu"], r.stderr + str(c2))

        # a position KiCad cannot take is dropped, not half applied
        r = run("move.py", board, "C1=104.5,98.5,90", "C2=5000000,0,0", "--save", env=S1)
        check("out-of-range move refused", r.returncode != 0, r.stderr + r.stdout)
        print("     (" + (r.stderr.strip().splitlines() or ["no message"])[-1][:200] + ")")
        check("out-of-range move left the file alone", sha(board) == before_file)

        # companion metadata that cannot be kept stops --save before any change
        comp_good = open(companion, "rb").read()
        with open(companion, "w") as f:
            f.write("{not json")
        c1 = pose_of(board, "C1", s1.url)
        r = run("move.py", board, "C1=103.5,97.5,0", "--save", env=S1)
        check("unreadable companion refused before any change", r.returncode != 0
              and "nothing was changed" in r.stderr and pose_of(board, "C1", s1.url) == c1
              and sha(board) == before_file and open(companion).read() == "{not json", r.stderr)
        for bad, word in (({**meta, "version": 3}, "version 1 or 2"),
                          ({**meta, "x-sentinel-top": {"keep": 1}}, "top-level keys a save drops: x-sentinel-top"),
                          ({**meta, "items": {**meta["items"], "no-such-item": {"custom_properties": {"a": "b"}}}},
                           "no item on the board")):
            with open(companion, "w") as f:
                json.dump(bad, f)
            r = run("move.py", board, "C1=103.5,97.5,0", "--save", env=S1)
            check(f"companion a save would lose refused before any change ({word})", r.returncode != 0
                  and word in r.stderr and "nothing was changed" in r.stderr
                  and pose_of(board, "C1", s1.url) == c1 and sha(board) == before_file, r.stderr)
        with open(companion, "wb") as f:
            f.write(comp_good)

        # another writer between the move and the save: nothing saved, parts put back
        for what, path in (("sidecar", companion), ("board", board)):
            keep = open(path, "rb").read()
            r = subprocess.run([venv_python(), "-s", fault, os.path.join(SKILL, "scripts"),
                                os.path.join(SKILL, "scripts", "move.py"), board, "C1=103.5,97.5,0", "--save"],
                               capture_output=True, text=True, env={**e, "FAULT": what})
            other = open(path, "rb").read()
            check(f"{what} changed by another writer: not saved, parts put back", r.returncode != 0
                  and "changed on disk" in r.stderr and "put back where they were" in r.stderr
                  and pose_of(board, "C1", s1.url) == c1 and other != keep
                  and (what == "board" or sha(board) == before_file), r.stderr)
            if what == "sidecar":
                check("the other writer's companion is left as they wrote it",
                      json.loads(other).get("x-other-writer") is True)
            with open(path, "wb") as f:
                f.write(keep)

        # --save writes the configured board, and nothing else
        cfg_before = sha(os.path.join(proj, ".backplane.json"))
        r = run("move.py", board, "C1=104.6,98.4,90", "C3=104.8,101.6,180", "--save", env=S1)
        check("move with --save", r.returncode == 0 and "saved " + os.path.realpath(board) in r.stdout,
              r.stderr + r.stdout)
        check("file changed by --save", sha(board) != before_file)
        with open(board) as f:
            text = f.read()
        check("saved file has the new position", re.search(r"\(at\s+104\.6\s+98\.4\s+90\)|\(translate\s+104\.6\s+98\.4\)\s*\(rotate\s+90\)", text) is not None,
              "C1 position not found in the file")
        # every sentinel survives the save: extension records in the companion
        # (now version 2), the custom property in the board file itself
        kept = json.load(open(companion)) if os.path.exists(companion) else {}
        check("companion extension sentinels survive --save", kept.get("version") == 2
              and kept.get("extensions") == want_ext, json.dumps(kept)[:400])
        check("custom property sentinel moved into the board file",
              re.search(r'\(custom_property\s+"fixture\.note"\s+"kept"', open(board).read()) is not None)
        check("--save says what it kept", "2 extension records kept" in r.stdout, r.stdout)
        # a version 2 companion survives a second save
        r = run("move.py", board, "C1=104.6,98.3,90", "--save", env=S1)
        kept = json.load(open(companion)) if os.path.exists(companion) else {}
        check("version 2 companion survives another save", r.returncode == 0 and kept.get("extensions") == want_ext,
              r.stderr + json.dumps(kept)[:300])
        # a save that drops a record: it is put back
        r = subprocess.run([venv_python(), "-s", fault, os.path.join(SKILL, "scripts"),
                            os.path.join(SKILL, "scripts", "move.py"), board, "C1=104.6,98.4,90", "--save"],
                           capture_output=True, text=True, env={**e, "FAULT": "drop-ext"})
        kept = json.load(open(companion)) if os.path.exists(companion) else {}
        check("an extension record the save dropped is put back", r.returncode == 0
              and "put back 1 extension record" in r.stdout and kept.get("extensions") == want_ext,
              r.stdout + r.stderr + json.dumps(kept)[:300])
        # the saved board and its companion load again
        s4 = Server(cli, board, os.path.join(tmp, "s4"))
        servers.append(s4)
        r = run("pin_sides.py", board, "U1", env={"KICAD_API_SOCKET": s4.url})
        check("saved board and companion load in a new server", r.returncode == 0, r.stderr)
        s4.stop()
        servers.remove(s4)
        check(".backplane.json kept", sha(os.path.join(proj, ".backplane.json")) == cfg_before)
        drc = os.path.join(tmp, "drc.json")
        subprocess.run([cli, "pcb", "drc", "--format", "json", "-o", drc, board], capture_output=True)
        with open(drc) as f:
            kinds = {v["type"] for v in json.load(f)["violations"]}
        check("saved board loads in kicad-cli DRC, no courtyard overlap", "courtyards_overlap" not in kinds, str(kinds))

        # rules come from the board, or from flags, never from defaults
        r = run("route_check.py", board, "--ic", "U1", env=S1)
        check("route_check runs", r.returncode == 0 and "all local links together" in r.stdout, r.stderr + r.stdout)
        check("route_check names the board's rules",
              "track width 0.150 mm (" in r.stderr and "via diameter 0.500 mm (" in r.stderr
              and "clearance 0.100 mm (" in r.stderr and "copper to edge 0.200 mm (" in r.stderr, r.stderr)
        r = run("placement_audit.py", board, "--ic", "U1", env=S1)
        check("placement_audit runs", r.returncode == 0 and "fronts (" in r.stdout, r.stderr)
        r = run("local_search.py", board, "--ic", "U1", "--pin", "1", "--part", "C1", "--top", "2", env=S1)
        check("local_search runs", r.returncode == 0 and "legal candidates" in r.stdout, r.stderr)
        r = run("group_search.py", board, "--ic", "U1", "--assign", "C1:1", "C2:11", "--top", "1", env=S1)
        check("group_search runs", r.returncode == 0 and "order " in r.stdout, r.stderr)

        sb = Server(cli, bare, os.path.join(tmp, "sb"))
        servers.append(sb)
        SB = {"KICAD_API_SOCKET": sb.url}
        r = run("route_check.py", bare, "--ic", "U1", env=SB)
        check("board without rules refused", r.returncode != 0 and "pass --track --clear --via --edge" in r.stderr,
              r.stderr)
        r = run("route_check.py", bare, "--ic", "U1", "--track", "0.15", "--clear", "0.1", "--via", "0.5", "--edge",
                "0.2", env=SB)
        check("board without rules runs with flags", r.returncode == 0 and "(flag)" in r.stderr, r.stderr)
        r = run("local_search.py", bare, "--ic", "U1", "--pin", "1", "--part", "C1", "--track", "0.15",
                "--clear", "0.1", env=SB)
        check("local_search needs only track and clearance", r.returncode == 0, r.stderr)
        sb.stop()
        servers.remove(sb)

        # a symbolic link inside the project to a board elsewhere is not the project's board
        link = os.path.join(proj, "linked.kicad_pcb")
        os.symlink(bare, link)
        sb = Server(cli, bare, os.path.join(tmp, "sb"))
        servers.append(sb)
        r = run("pin_sides.py", link, "U1", env={"KICAD_API_SOCKET": sb.url})
        check("symbolic link into the project refused", r.returncode != 0 and "is not the project's board" in r.stderr,
              r.stderr)
        sb.stop()
        servers.remove(sb)

        # a duplicated reference is refused, and does not break other moves
        dupb = fixture(os.path.join(tmp, "dup"), "dup", "--dup")
        sd = Server(cli, dupb, os.path.join(tmp, "sd"))
        servers.append(sd)
        SD = {"KICAD_API_SOCKET": sd.url}
        r = run("move.py", dupb, "R1=104,104.2,0", env=SD)
        check("duplicated reference refused", r.returncode != 0 and "more than one footprint" in r.stderr, r.stderr)
        r = run("move.py", dupb, "C1=104.5,98.5,90", env=SD)
        check("move on a board with a duplicated reference", r.returncode == 0, r.stderr)
        sd.stop()
        servers.remove(sd)

        # custom net classes, board minimums, overrides, pairs and custom rules
        cls = fixture(os.path.join(tmp, "cls"), "cls", "--klass", "Power:0.3:0.2:0.7:VDD", "--pad-clearance", "5=0.35")
        pair = fixture(os.path.join(tmp, "pair"), "pair", "--klass", "Pair:0.15:0.1:0.5:USB_*:x:0.25:0.12",
                       "--min-clearance", "0.25")
        dru = fixture(os.path.join(tmp, "dru"), "dru", "--dru",
                      "(version 1)\n# a comment (rule not_a_rule)\n(rule big (constraint clearance (min 0.5mm)))\n")
        for bd in (cls, pair, dru):
            sv = Server(cli, bd, os.path.join(tmp, "s-" + os.path.basename(bd)))
            servers.append(sv)
            E = {"KICAD_API_SOCKET": sv.url}
            if bd == cls:
                r = run("route_check.py", bd, "--ic", "U1", env=E)
                check("a custom net class sets track and via", r.returncode == 0
                      and "track width 0.300 mm (net class Power on VDD)" in r.stderr
                      and "via diameter 0.700 mm (net class Power on VDD)" in r.stderr, r.stderr)
                check("a pad clearance override sets clearance",
                      "clearance 0.350 mm (pad U1.5 clearance override)" in r.stderr, r.stderr)
                r = run("placement_audit.py", bd, "--ic", "U1", env=E)
                check("placement_audit uses the same rules", r.returncode == 0
                      and "clearance 0.350 mm (pad U1.5" in r.stderr, r.stderr)
                r = run("route_check.py", bd, "--ic", "U1", "--clear", "0.1", env=E)
                check("a flag looser than the board refused", r.returncode != 0
                      and "looser than the board's 0.350 mm" in r.stderr, r.stderr)
                r = run("route_check.py", bd, "--ic", "U1", "--clear", "0.1", "--rules-override", env=E)
                check("--rules-override runs and says it is looser", r.returncode == 0
                      and "LOOSER THAN THE BOARD" in r.stderr and "results do not hold" in r.stderr, r.stderr)
                r = run("route_check.py", bd, "--ic", "U1", "--clear", "0.4", env=E)
                check("a stricter flag runs", r.returncode == 0 and "clearance 0.400 mm (flag)" in r.stderr, r.stderr)
            elif bd == pair:
                r = run("route_check.py", bd, "--ic", "U1", env=E)
                check("a pattern-assigned pair class sets the track to the pair width", r.returncode == 0
                      and "track width 0.250 mm (net class Pair pair width on USB_" in r.stderr, r.stderr)
                check("pairs are named as routed as single tracks",
                      "2 nets are differential pairs (USB_N, USB_P)" in r.stderr, r.stderr)
                check("a board minimum sets clearance",
                      "clearance 0.250 mm (board minimum min_clearance)" in r.stderr, r.stderr)
            else:
                r = run("route_check.py", bd, "--ic", "U1", env=E)
                check("custom DRC rules refused without flags", r.returncode != 0
                      and "custom DRC rules" in r.stderr, r.stderr)
                r = run("route_check.py", bd, "--ic", "U1", "--track", "0.15", "--clear", "0.5", "--via", "0.5",
                        "--edge", "0.2", env=E)
                check("custom DRC rules with all four flags runs and says they are not evaluated",
                      r.returncode == 0 and "are not evaluated" in r.stderr, r.stderr)
            sv.stop()
            servers.remove(sv)

        # an RF pi chain: a shunt in the gap is inline, one beside the path is a branch
        rfb = fixture(os.path.join(tmp, "rf"), "rf", "--rf")
        sr = Server(cli, rfb, os.path.join(tmp, "s-rf"))
        servers.append(sr)
        ER = {"KICAD_API_SOCKET": sr.url}
        chain = ["--ic", "U1", "--chain", "U1.7", "L1", "L2", "RF"]
        r = run("placement_audit.py", rfb, *chain, env=ER)
        check("--chain without --rf-track refused", r.returncode != 0 and "--chain needs --rf-track" in r.stderr, r.stderr)
        r = run("placement_audit.py", rfb, *chain, "--rf-track", "0.3", env=ER)
        check("an RF shunt in the gap reads inline", r.returncode == 0
              and re.search(r"C20\s+on RFN\s+[\d.]+ mm  inline", r.stdout) is not None, r.stdout[-600:] + r.stderr)
        check("an RF shunt beside the path reads as a branch",
              re.search(r"C21\s+on RF\s+[\d.]+ mm  OFF THE PATH: a [\d.]+ mm branch", r.stdout) is not None,
              r.stdout[-600:])
        if a.v19:
            old = subprocess.run([venv_python(), "-s", os.path.join(a.v19, "scripts", "placement_audit.py"), rfb, *chain,
                                  "--rf-track", "0.3"], capture_output=True, text=True,
                                 env={**os.environ, **ER, "PYTHONDONTWRITEBYTECODE": "1"})
            check("placement_audit --chain prints what v19 printed", old.returncode == 0 and old.stdout == r.stdout,
                  f"v19 rc {old.returncode}: {old.stderr[-300:]}")
        # a documented tie: shown on the shunt's line, flagged when stretched past the part
        ties = ["--tie", "C20:RFN=L1.2", "C21:GND=U1.8"]
        rt = run("placement_audit.py", rfb, *chain, "--rf-track", "0.3", *ties, env=ER)
        check("a short documented tie is shown on the shunt and not flagged", rt.returncode == 0
              and re.search(r"C20\s+on RFN.*inline.*documented tie C20:RFN=L1.2 [\d.]+ mm$", rt.stdout, re.M) is not None,
              rt.stdout[-800:] + rt.stderr)
        check("a stretched documented tie on a shunt is flagged",
              re.search(r"C21\s+on RF.*documented tie C21:GND=U1.8 [\d.]+ mm TIE STRETCHED", rt.stdout) is not None
              and re.search(r"C21:GND=U1.8\s+[\d.]+ mm  TIE STRETCHED", rt.stdout) is not None, rt.stdout[-800:])
        check("without --tie no tie is reported", "documented tie" not in r.stdout and "TIE" not in r.stdout)
        if a.v20:
            old = subprocess.run([venv_python(), "-s", os.path.join(a.v20, "scripts", "placement_audit.py"), rfb, *chain,
                                  "--rf-track", "0.3", *ties], capture_output=True, text=True,
                                 env={**os.environ, **ER, "PYTHONDONTWRITEBYTECODE": "1"})
            check("placement_audit --chain --tie prints what v20 printed", old.returncode == 0 and old.stdout == rt.stdout,
                  f"v20 rc {old.returncode}: {old.stderr[-300:]}")
        sr.stop()
        servers.remove(sr)

        sw = Server(cli, wide, os.path.join(tmp, "sw"))
        servers.append(sw)
        r = run("route_check.py", wide, "--ic", "U1", env={"KICAD_API_SOCKET": sw.url})
        check("other rules are read", r.returncode == 0 and "track width 0.200 mm" in r.stderr
              and "clearance 0.150 mm" in r.stderr and "via diameter 0.600 mm" in r.stderr, r.stderr)

        # what a bp.4 save keeps, and what counts as lost
        code = ("import json, sys; sys.path.insert(0, sys.argv[1]); import sidecar as s; "
                "v1 = {'format': 'f', 'version': 1, 'items': {'a': {'custom_properties': {'p': 'q'}, 'x': 1}, "
                "'b': {'start_ending': {}}}}; "
                "e, p = s.expected(v1); "
                "v2 = {'version': 2, 'extensions': {'a': {'x': 2}}}; "
                "print(json.dumps([e, p, s.lost_extensions(e, v2), s.lost_extensions(e, None), "
                "s.lost_properties(p, '(custom_property \"p\" \"q\" (at 0 0))'), s.lost_properties(p, '')]))")
        rr = subprocess.run([sys.executable, "-I", "-B", "-c", code, os.path.join(SKILL, "scripts")], capture_output=True,
                            text=True)
        check("the save's mapping and the loss checks",
              rr.stdout.strip() == '[{"a": {"x": 1}}, {"a": {"p": "q"}}, {"a": {"x": 1}}, {"a": {"x": 1}}, [], ["a:p"]]',
              rr.stdout + rr.stderr)

        if a.v18:
            for script, args in (("route_check.py", ["--ic", "U1"]), ("placement_audit.py", ["--ic", "U1"])):
                old = subprocess.run([venv_python(), "-s", os.path.join(a.v18, "scripts", script), board, *args],
                                     capture_output=True, text=True, env={**os.environ, **S1,
                                                                          "PYTHONDONTWRITEBYTECODE": "1"})
                new = run(script, board, *args, env=S1)
                check(f"{script} prints what v18 printed on v18's rules", old.returncode == 0 and
                      old.stdout == new.stdout, f"v18 rc {old.returncode}: {old.stderr[-400:]}")
    finally:
        for s in servers:
            s.stop()
        if a.keep:
            print("kept", tmp)
        else:
            shutil.rmtree(tmp, ignore_errors=True)
    print(f"{len(PASSES)} passed, {len(FAILS)} failed")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
