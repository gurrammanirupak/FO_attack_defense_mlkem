

#!/usr/bin/env python3
"""Flash the ML-KEM SimpleSerial firmware to the STM32F3 and verify it runs.

Checks, in order:
  1. programs the .hex
  2. 'p' raises the tio4 trigger (scope sees it)
  3. 'd' returns 32 bytes, and two no-glitch runs are IDENTICAL
     (decapsulation is deterministic -- if they differ, the firmware or the
      key/ct material is wrong, stop before glitching)
  4. 'm' returns the IND-CPA message m' (debug, for offline K_TARGET)
  5. 't' returns the DWT cycle count of one decap (overhead measurement)
"""

import chipwhisperer as cw
import time
import struct

FW = "simpleserial-mlkem-CW308_STM32F3.hex"   # <-- match your build output name

scope = cw.scope()
target = cw.target(scope, cw.targets.SimpleSerial)

# same clock/IO as the campaign (no glitch needed for verification)
scope.clock.clkgen_freq = 7372800
scope.clock.clkgen_src = "internal"
scope.clock.adc_mul = 4
scope.io.tio1 = "serial_rx"
scope.io.tio2 = "serial_tx"
scope.trigger.triggers = "tio4"
target.baud = 38400
scope.adc.basic_mode = "rising_edge"
scope.adc.samples = 500

# Deliver the clock to the target via the SAME path the working glitch script
# uses (HS2 = glitch/clock_xor). hs2="clkgen" generated a clock but did not drive
# the target on this Husky. trigger_src="manual" so no glitch fires during verify.
scope.glitch.enabled = True
scope.glitch.clk_src = "pll"
scope.glitch.output = "clock_xor"
scope.glitch.trigger_src = "manual"
scope.io.hs2 = "glitch"

# confirm the clock is actually running before expecting the target to boot
time.sleep(0.1)
try:
    print(f"[+] clkgen={scope.clock.clkgen_freq} Hz, adc_freq={scope.clock.adc_freq} Hz")
except Exception:
    pass

def reset_target():
    scope.io.nrst = 'low';  time.sleep(0.05)
    scope.io.nrst = 'high_z'; time.sleep(0.2)
    target.flush()

# --- 1) flash ---
print(f"[+] Programming {FW} ...")
cw.program_target(scope, cw.programmers.STM32FProgrammer, FW)
reset_target()

# --- 2) trigger sanity ('p') ---
target.flush()
scope.arm()
target.simpleserial_write('p', bytearray())
timed_out = scope.capture()          # False = trigger fired; True = never saw tio4
print("[+] Trigger on 'p':",
      "SEEN" if not timed_out else "NOT SEEN -> check trigger_setup() / tio4 wiring")

# --- 3) baseline decapsulation + determinism ---
def decap():
    target.flush()
    target.simpleserial_write('d', bytearray())
    return target.simpleserial_read('r', 32, timeout=2000)

reset_target()
ss1 = decap()
ss2 = decap()
if not ss1:
    print("[!] No response to 'd' -- firmware not running or wrong command table.")
else:
    print("[+] ss run 1 :", bytes(ss1).hex())
    print("[+] ss run 2 :", bytes(ss2).hex())
    print("[+] deterministic:",
          "YES" if ss1 == ss2 else "NO -> firmware/key/ct problem, do NOT glitch yet")

# --- 4) debug m' (IND-CPA message, for offline K_TARGET) ---
target.flush()
target.simpleserial_write('m', bytearray())
mp = target.simpleserial_read('r', 32, timeout=2000)
if mp:
    print("[+] m' (debug):", bytes(mp).hex())

# --- 5) decap cycle count (overhead measurement, DWT CYCCNT via 't') ---
reset_target()
target.flush()
target.simpleserial_write('t', bytearray())          # 't' = timed decap
resp = target.simpleserial_read('r', 4, timeout=2000)
if not resp:
    print("[!] no 'r' to 't'  ->  firmware has no 't' handler or DWT not enabled")
else:
    cyc = struct.unpack('<I', bytes(resp))[0]
    print(f"[+] decap cycles: {cyc}")

scope.dis()
target.dis()
print("[+] Verify complete.")









'''#!/usr/bin/env python3
"""Flash the ML-KEM SimpleSerial firmware to the STM32F3 and verify it runs.

Checks, in order:
  1. programs the .hex
  2. 'p' raises the tio4 trigger (scope sees it)
  3. 'd' returns 32 bytes, and two no-glitch runs are IDENTICAL
     (decapsulation is deterministic -- if they differ, the firmware or the
      key/ct material is wrong, stop before glitching)
  4. 'm' returns the IND-CPA message m' (debug, for offline K_TARGET)
"""

import chipwhisperer as cw
import time

FW = "simpleserial-mlkem-CW308_STM32F3.hex"   # <-- match your build output name

scope = cw.scope()
target = cw.target(scope, cw.targets.SimpleSerial)

# same clock/IO as the campaign (no glitch needed for verification)
scope.clock.clkgen_freq = 7372800
scope.clock.clkgen_src = "internal"
scope.clock.adc_mul = 4
scope.io.tio1 = "serial_rx"
scope.io.tio2 = "serial_tx"
scope.trigger.triggers = "tio4"
target.baud = 38400
scope.adc.basic_mode = "rising_edge"
scope.adc.samples = 500

# Deliver the clock to the target via the SAME path the working glitch script
# uses (HS2 = glitch/clock_xor). hs2="clkgen" generated a clock but did not drive
# the target on this Husky. trigger_src="manual" so no glitch fires during verify.
scope.glitch.enabled = True
scope.glitch.clk_src = "pll"
scope.glitch.output = "clock_xor"
scope.glitch.trigger_src = "manual"
scope.io.hs2 = "glitch"

# confirm the clock is actually running before expecting the target to boot
time.sleep(0.1)
try:
    print(f"[+] clkgen={scope.clock.clkgen_freq} Hz, adc_freq={scope.clock.adc_freq} Hz")
except Exception:
    pass

def reset_target():
    scope.io.nrst = 'low';  time.sleep(0.05)
    scope.io.nrst = 'high_z'; time.sleep(0.2)
    target.flush()

# --- 1) flash ---
print(f"[+] Programming {FW} ...")
cw.program_target(scope, cw.programmers.STM32FProgrammer, FW)
reset_target()

# --- 2) trigger sanity ('p') ---
target.flush()
scope.arm()
target.simpleserial_write('p', bytearray())
timed_out = scope.capture()          # False = trigger fired; True = never saw tio4
print("[+] Trigger on 'p':",
      "SEEN" if not timed_out else "NOT SEEN -> check trigger_setup() / tio4 wiring")

# --- 3) baseline decapsulation + determinism ---
def decap():
    target.flush()
    target.simpleserial_write('d', bytearray())
    return target.simpleserial_read('r', 32, timeout=2000)

reset_target()
ss1 = decap()
ss2 = decap()
if not ss1:
    print("[!] No response to 'd' -- firmware not running or wrong command table.")
else:
    print("[+] ss run 1 :", bytes(ss1).hex())
    print("[+] ss run 2 :", bytes(ss2).hex())
    print("[+] deterministic:",
          "YES" if ss1 == ss2 else "NO -> firmware/key/ct problem, do NOT glitch yet")

# --- 4) debug m' (IND-CPA message, for offline K_TARGET) ---
target.flush()
target.simpleserial_write('m', bytearray())
mp = target.simpleserial_read('r', 32, timeout=2000)
if mp:
    print("[+] m' (debug):", bytes(mp).hex())

scope.dis()
target.dis()
print("[+] Verify complete.")'''
