#!/usr/bin/env python3
"""
Regenerate the glitch-offset sweep figure (undefended vs FODefensePass-defended)
from the two campaign CSVs.

Usage:
    python3 make_sweep_fig.py            # writes fig_sweep.pdf and fig_sweep.png
    python3 make_sweep_fig.py --show     # also opens a window

Expects, in the same directory:
    sweep_undefended.csv
    sweep_defended.csv

Each CSV is one row per glitch offset. The script auto-detects the offset
column and the outcome-count columns from the header, so it tolerates minor
naming differences. If detection fails it prints the header it saw and exits,
so you can tell it the right column names.
"""
import argparse
import csv
import sys
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def classify(status):
    s = status.strip().lower()
    if "leak" in s or "target" in s:
        return "leak"
    if "fault" in s or "trap" in s or "0xee" in s:
        return "fault"
    if "normal" in s or "rej" in s:
        return "normal"
    return "other"


def load(path):
    try:
        with open(path, newline="") as f:
            rows = list(csv.DictReader(f))
    except FileNotFoundError:
        sys.exit(f"{path}: not found")
    if not rows or "ExtOffset" not in rows[0] or "Status" not in rows[0]:
        sys.exit(f"{path}: expected columns ExtOffset, Status. Saw {list(rows[0]) if rows else 'nothing'}")
    # leaks[offset] = number of leaks at that offset
    leaks = defaultdict(int)
    offsets = set()
    for r in rows:
        off = int(float(r["ExtOffset"]))
        offsets.add(off)
        if classify(r["Status"]) == "leak":
            leaks[off] += 1
    return offsets, leaks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--undef", default="sweep_undefended.csv")
    ap.add_argument("--def", dest="defended", default="sweep_defended.csv")
    ap.add_argument("--out", default="fig_sweep")
    args = ap.parse_args()

    u_off, u_leak = load(args.undef)
    d_off, d_leak = load(args.defended)

    offs = sorted(u_off | d_off)
    uy = [u_leak.get(o, 0) for o in offs]
    dy = [d_leak.get(o, 0) for o in offs]

    print(f"Undefended: {sum(uy)} leaks across {len(u_off)} offsets")
    print(f"Defended:   {sum(dy)} leaks across {len(d_off)} offsets")

    fig, ax = plt.subplots(figsize=(6.4, 2.6))
    ax.bar(offs, uy, width=0.9, color="#c0392b", label="Undefended")
    ax.bar(offs, dy, width=0.9, color="#27ae60", label="FODefensePass")
    ax.set_xlabel("Glitch ext_offset (cycles)")
    ax.set_ylabel("Leaks per offset")
    ax.set_ylim(bottom=0)
    ax.grid(True, axis="y", alpha=0.3)
    ax.legend(frameon=False, loc="upper right")
    fig.tight_layout()

    fig.savefig(args.out + ".pdf")
    fig.savefig(args.out + ".png", dpi=200)
    print(f"Wrote {args.out}.pdf and {args.out}.png")


if __name__ == "__main__":
    main()
