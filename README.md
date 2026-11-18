# The Compiler's Blind Spot — Artifact

Artifact  on instruction-skip fault injection against the ML-KEM-768 (Kyber) Fujisaki–Okamoto (FO) check, and
**FODefensePass**, an automated LLVM countermeasure.

This repository lets a reader reproduce three claims from the paper:

1. A single instruction-skip at the FO ciphertext comparison turns Kyber
   decapsulation into a plaintext-checking oracle that leaks the session key.
2. Naive and hand-written duplicate-and-compare (DMR) defenses are **folded
   away by the optimizer** at `-O1` and above — the compiler is the blind spot.
3. **FODefensePass** reinserts the check in the LLVM IR *after* the optimizer
   runs, so it survives to the binary. On silicon it converts every leaking
   fault into a trap, at **+16 bytes ROM and +0.13% decapsulation cycles**.

> **Note on anonymity.** This artifact is anonymized for double-blind review.
> It contains no author names, institutions, or absolute paths.

---

## Repository layout

```
emulation/            Instruction-level fault emulation (Qiling/Unicorn, no hardware)
  attack_emulation.py   Skips the FO-check instruction and recovers the oracle bit
  harness.c, rb_stub.c  Minimal decapsulation harness
  Makefile.attack

compiler-fragility/   Shows the optimizer removing DMR checks (no hardware)
  run_dmr_sweep.sh      Builds the demo at -O0..-O3/-Os and greps for the check
  dmr_demo.c            Naive duplicate-and-compare predicate
  ct_verify.c           Constant-time compare variant
  RESULTS.txt           Recorded output of the sweep

pass/                 The countermeasure
  FODefensePass.cpp     LLVM new-PM pass: re-inserts the FO check post-optimizer
  build.sh              Builds build/FODefensePass.so (needs LLVM 18)

firmware/             ChipWhisperer target firmware (Kyber reference impl)
  cc-wrap.sh            Compiler wrapper: routes kem.c through opt + FODefensePass
  kem.c                 Single-verify decapsulation (the proven-leaking path)
  simpleserial-mlkem.c  SimpleSerial command handlers ('d' decap, 't' cycle count)
  *.c, *.h              Kyber reference sources + headers
  Makefile

campaign/             Hardware fault campaign (ChipWhisperer-Husky + CW308 STM32F3)
  glitch_leak.py        Sweeps glitch offset, logs Normal/Trap/Leak per shot
  hammer_2199.py        Fixed-offset A/B test (100 shots undefended vs defended)
  flash_verify.py       Flashes a build and reads back decap cycle count (DWT)

data/                 Measurements and the figure script
  sweep_undefended.csv  Per-offset outcomes, undefended build
  sweep_defended.csv    Per-offset outcomes, FODefensePass build
  cycles.txt            Decap cycle counts (undefended vs defended)
  make_sweep_fig.py     Regenerates fig_sweep.pdf from the two CSVs
```

---

## Requirements

| Component | Version used |
|---|---|
| ARM toolchain | `arm-none-eabi-gcc` 13.2.1 20231009 |
| LLVM / Clang | 18 (`clang`, `opt`, `llvm-config`) |
| Hardware | ChipWhisperer-Husky + CW308 UFO with STM32F3 target |
| ChipWhisperer SW | 5.x (provides `hal.h`, `simpleserial.h`, the build harness) |
| Emulation | Python 3.10+, Qiling + Unicorn |
| Figures | Python 3, matplotlib |

**ChipWhisperer is a separate dependency.** The `firmware/` sources here are
*only* the Kyber target code. The framework headers (`hal.h`,
`simpleserial.h`) and the SimpleSerial build machinery come from a
ChipWhisperer checkout and are intentionally not included.

---

## Reproduce without hardware

These two steps need no ChipWhisperer and establish the core claims.

**1. The fault leaks the key (emulation).**
```bash
cd emulation
make -f Makefile.attack
python3 attack_emulation.py
```
Skipping the FO-check instruction recovers the plaintext-checking oracle bit;
running without the skip does not.

**2. The optimizer removes the naive defense.**
```bash
cd compiler-fragility
./run_dmr_sweep.sh
```
The script compiles the DMR demo at `-O0` through `-O3` and `-Os` and reports,
per level, whether the duplicate check survives in the object code. The naive
predicate is folded at `-O1`+; opaque `verify()` calls survive. Compare against
the recorded `RESULTS.txt`.

---

## Reproduce the countermeasure build

**3. Build the pass.**
```bash
cd pass
./build.sh
export FODEFENSE_SO="$PWD/build/FODefensePass.so"
```

**4. Build the firmware with the pass.** Drop `firmware/` into a ChipWhisperer
tree (e.g. `hardware/victims/firmware/simpleserial-mlkem`), then:
```bash
make clean
make CC="$PWD/cc-wrap.sh" PLATFORM=CW308_STM32F3 CRYPTO_TARGET=NONE
```
The wrapper routes only `kem.c` through `clang -emit-llvm | opt -passes=fo-defense
| clang`; everything else uses `arm-none-eabi-gcc`. A successful build reports
**ROM ≈ 21,736 B** (vs 21,720 B undefended, **+16 B**).

---

## Reproduce on hardware (ChipWhisperer)

| Claim | Command | Expected |
|---|---|---|
| Undefended firmware leaks | `python3 campaign/glitch_leak.py sweep_undefended.csv` | Leaks at several offsets near 2199 |
| Defended firmware traps, never leaks | `python3 campaign/glitch_leak.py sweep_defended.csv` | 0 Leak over the sweep |
| A/B at the best offset | `python3 campaign/hammer_2199.py` | Undefended 100/100 Leak; defended 100/100 Trap, 0 Leak |
| Cycle overhead | `python3 campaign/flash_verify.py` (per build) | 1,711,484 → 1,713,739 cycles, **+2,255 (+0.13%)** |

Flash the undefended and defended builds with `flash_verify.py` *between*
campaigns — the board is not reflashed automatically, and a stale image
produces misleading results.

---

## Regenerate the figure

```bash
cd data
python3 make_sweep_fig.py      # writes fig_sweep.pdf and fig_sweep.png
```

---

## Headline numbers

| Metric | Undefended | FODefensePass | Hand-DMR (ref.) |
|---|---|---|---|
| ROM | 21,720 B | 21,736 B (**+16 B, +0.07%**) | 21,800 B (+0.37%) |
| Decap cycles | 1,711,484 | 1,713,739 (**+0.13%**) | 1,907,259 (+11.4%) |
| Fault outcome | Key leak | Trap (no leak) | Trap (no leak) |

FODefensePass matches the security of a hand-written DMR check at a fraction of
the cycle cost, and — unlike the hand-written check — is not removed by the
optimizer.
