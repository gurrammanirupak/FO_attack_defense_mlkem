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

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

UNDEF = "sweep_undefended.csv"
DEF = "sweep_defended.csv"

# Candidate header names (lowercased) for each quantity we plot.
OFFSET_KEYS = ("offset", "ext_offset", "glitch_offset", "x", "cycle")
LEAK_KEYS = ("leak", "leaks", "leak_count", "n_leak")


def _pick(header, candidates):
    low = {h.lower().strip(): h for h in header}
    for c in candidates:
        if c in low:
            return low[c]
    return None


def load(path):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        sys.exit(f"{path}: no data rows")
    header = rows[0].keys()
    off = _pick(header, OFFSET_KEYS)
    leak = _pick(header, LEAK_KEYS)
    if off is None or leak is None:
        sys.exit(
            f"{path}: could not find offset/leak columns.\n"
            f"  header seen: {list(header)}\n"
            f"  edit OFFSET_KEYS / LEAK_KEYS at the top of this script."
        )
    xs = [float(r[off]) for r in rows]
    ys = [float(r[leak]) for r in rows]
    return xs, ys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", action="store_true")
    args = ap.parse_args()

    ux, uy = load(UNDEF)
    dx, dy = load(DEF)

    fig, ax = plt.subplots(figsize=(6.0, 3.2))
    ax.plot(ux, uy, "o-", color="#c0392b", label="Undefended", linewidth=1.5,
            markersize=4)
    ax.plot(dx, dy, "s-", color="#27ae60", label="FODefensePass", linewidth=1.5,
            markersize=4)
    ax.set_xlabel("Glitch ext_offset (cycles)")
    ax.set_ylabel("Key leaks per 100 shots")
    ax.set_ylim(bottom=-2)
    ax.grid(True, alpha=0.3)
    ax.legend(frameon=False)
    fig.tight_layout()

    fig.savefig("fig_sweep.pdf")
    fig.savefig("fig_sweep.png", dpi=200)
    print("Wrote fig_sweep.pdf and fig_sweep.png")
    if args.show:
        plt.show()


if __name__ == "__main__":
    main()
