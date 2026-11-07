#!/usr/bin/env python3
"""Audit KiCad schematic pin-tip geometry vs nearby wires/labels.

Field lesson: global labels placed near an IC without a wire to the pin
endpoint leave pins electrically floating even when a stale netlist looks fine.

Usage:
  python check_sch_geo_vs_netlist.py path/to/Sheet.kicad_sch
  python check_sch_geo_vs_netlist.py path/to/project_dir

Coordinate rule (rotation 0 / 180 left-right pins):
  world_x = ox + lx
  world_y = oy - ly
KiCad schematic Y is down. Re-export netlist with kicad-cli after edits.
"""

from __future__ import annotations

import argparse
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PinDef:
    num: str
    name: str
    lx: float
    ly: float
    angle: int


@dataclass
class PinHit:
    ref: str
    pin: str
    name: str
    x: float
    y: float
    connected: bool


def _f(tok: str) -> float:
    return float(tok)


def _extract_balanced(text: str, start: int) -> str | None:
    if start < 0 or start >= len(text) or text[start] != "(":
        return None
    depth = 0
    for i in range(start, len(text)):
        ch = text[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def parse_lib_pins_from_text(text: str) -> dict[str, list[PinDef]]:
    """Map symbol name -> pins from unit drawings (…_1_1)."""
    out: dict[str, list[PinDef]] = {}
    for m in re.finditer(r'\(symbol "([^"]+)"', text):
        name = m.group(1)
        if name.endswith("_0_1") or name.endswith("_1_1"):
            continue
        block = _extract_balanced(text, m.start())
        if not block:
            continue
        # Prefer the pins unit (…_1_1); fall back to all pins in block.
        unit = None
        for um in re.finditer(rf'\(symbol "{re.escape(name)}_1_1"', block):
            unit = _extract_balanced(block, um.start())
            break
        src = unit or block
        pins: list[PinDef] = []
        for pm in re.finditer(
            r'\(pin [^\n]*\n\s*\(at ([^\s]+) ([^\s]+) ([^\s]+)\)[\s\S]*?'
            r'\(name "([^"]*)"[\s\S]*?\(number "([^"]*)"',
            src,
        ):
            pins.append(
                PinDef(
                    num=pm.group(5),
                    name=pm.group(4),
                    lx=_f(pm.group(1)),
                    ly=_f(pm.group(2)),
                    angle=int(float(pm.group(3))),
                )
            )
        if pins:
            out[name] = pins
            out[name.split(":")[-1]] = pins
    return out


def load_libs(sch_text: str, sch_path: Path) -> dict[str, list[PinDef]]:
    libs = parse_lib_pins_from_text(sch_text)
    for lib_path in list(sch_path.parent.glob("*.kicad_sym")) + list(
        sch_path.parent.glob("libraries/*.kicad_sym")
    ):
        libs.update(
            parse_lib_pins_from_text(
                lib_path.read_text(encoding="utf-8", errors="replace")
            )
        )
    return libs


def abs_pin(ox: float, oy: float, lx: float, ly: float) -> tuple[float, float]:
    return ox + lx, oy - ly


def collect_attach_points(text: str) -> set[tuple[float, float]]:
    pts: set[tuple[float, float]] = set()
    for m in re.finditer(r"\(wire[\s\S]*?\(pts([\s\S]*?)\)\s*\(stroke", text):
        for xy in re.finditer(r"\(xy ([^\s]+) ([^\s]+)\)", m.group(1)):
            pts.add((_f(xy.group(1)), _f(xy.group(2))))
    for m in re.finditer(
        r'\((?:global_label|label|hierarchical_label) "([^"]+)"[\s\S]*?\(at ([^\s]+) ([^\s]+)',
        text,
    ):
        pts.add((_f(m.group(2)), _f(m.group(3))))
    for m in re.finditer(r"\(junction[\s\S]*?\(at ([^\s]+) ([^\s]+)\)", text):
        pts.add((_f(m.group(1)), _f(m.group(2))))
    for m in re.finditer(r"\(no_connect[\s\S]*?\(at ([^\s]+) ([^\s]+)\)", text):
        pts.add((_f(m.group(1)), _f(m.group(2))))
    return pts


def near(
    a: tuple[float, float], b: tuple[float, float], tol: float
) -> bool:
    return math.hypot(a[0] - b[0], a[1] - b[1]) <= tol


def audit_sheet(path: Path, tol: float) -> list[PinHit]:
    text = path.read_text(encoding="utf-8", errors="replace")
    libs = load_libs(text, path)
    attach = collect_attach_points(text)
    body = re.sub(r"\(lib_symbols[\s\S]*?\n\t\)\n", "\n", text, count=1)
    hits: list[PinHit] = []
    for m in re.finditer(
        r'\(symbol\s*\n\t\t\(lib_id "([^"]+)"\)\s*\n\t\t\(at ([^\s]+) ([^\s]+) ([^\s]+)\)'
        r'[\s\S]*?\(property "Reference" "([^"]+)"',
        body,
    ):
        lib_id = m.group(1)
        ox, oy = _f(m.group(2)), _f(m.group(3))
        ref = m.group(5)
        if ref.startswith("#"):
            continue
        short = lib_id.split(":")[-1]
        pins = libs.get(lib_id) or libs.get(short) or []
        for p in pins:
            x, y = abs_pin(ox, oy, p.lx, p.ly)
            ok = any(near((x, y), q, tol) for q in attach)
            hits.append(PinHit(ref, p.num, p.name, x, y, ok))
    return hits


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("path", type=Path, help="Sheet .kicad_sch or directory")
    ap.add_argument("--tol", type=float, default=0.05)
    args = ap.parse_args()

    if args.path.is_dir():
        paths = sorted(
            p for p in args.path.glob("*.kicad_sch") if not p.name.startswith("~")
        )
    else:
        paths = [args.path]

    if not paths:
        print("No .kicad_sch found", file=sys.stderr)
        return 2

    total_float = 0
    for sch in paths:
        hits = audit_sheet(sch, args.tol)
        floating = [h for h in hits if not h.connected]
        print(f"== {sch.name}: pins={len(hits)} floating~={len(floating)}")
        for h in floating[:50]:
            print(
                f"  FLOAT {h.ref} pin {h.pin} ({h.name}) @ ({h.x:.2f},{h.y:.2f})"
            )
        if len(floating) > 50:
            print(f"  ... {len(floating) - 50} more")
        total_float += len(floating)

    print(f"TOTAL_FLOATING~={total_float}")
    print("Note: heuristic only. Re-export netlist with kicad-cli and reconcile.")
    return 1 if total_float else 0


if __name__ == "__main__":
    raise SystemExit(main())
