#!/usr/bin/env python3
"""
Verified Qiling emulation of the ML-KEM-768 FO single-skip shared-secret leak.

Models the fault the way the literature does (Xagawa et al., ASIACRYPT 2021):
a single fault neutralises the FO equality test, so decapsulation returns the
accept-branch shared secret K' for an INVALID ciphertext instead of the
rejection key J(z||c').

Unlike a raw buffer dump, this VERIFIES the result against ground truth:
  * no fault  -> ss must equal K_rej  (rejection key)
  * fault     -> ss must equal K_TARGET (real accept-branch secret)
Both constants are the SAME vector flashed on the STM32F3 hardware, so the
emulation and the silicon leak the identical value.

Build the target first (same vector as random_data.h):
  gcc -O1 -g -DKYBER_K=3 -I <kyber>/ref harness.c rb_stub.c \
      <kyber>/ref/{kem,indcpa,polyvec,poly,ntt,cbd,reduce,verify,fips202,symmetric-shake}.c \
      -o target_kyber_scalar
"""
import subprocess
from qiling import Qiling
from qiling.const import QL_VERBOSE

BIN      = "target_kyber_scalar"
K_TARGET = "2eec0d2747a234c7f23dbf4838b6d0400bbba6ca4c82e98fd102aaeecc0f646d"
K_REJ    = "4eda6889ca1f5f024fdfac9c60040271bcab7faf8f24dfa19d1995f8e5fe48ab"

# Resolve symbols from the ELF (robust to recompiles / changed offsets)
def sym(name):
    out = subprocess.check_output(["nm", BIN]).decode().splitlines()
    for line in out:
        parts = line.split()
        if len(parts) == 3 and parts[2] == name:
            return int(parts[0], 16)
    raise SystemExit(f"symbol {name} not found")

CMOV_OFF = sym("pqcrystals_kyber768_ref_cmov")
SS_OFF   = sym("ss_out")

def run(fault):
    ql = Qiling([BIN], rootfs="/", verbose=QL_VERBOSE.OFF)
    base = ql.loader.load_address
    st = {"armed": False, "ret": None, "ss": None}

    def hook(ql, addr, size):
        rel = addr - base
        # First cmov call in decapsulation is the FO select: cmov(ss, kr, 32, !fail).
        if rel == CMOV_OFF and not st["armed"]:
            st["armed"] = True
            st["ret"] = ql.mem.read(ql.arch.regs.read("rsp"), 8)      # return address
            st["ret"] = int.from_bytes(st["ret"], "little")
            if fault:
                ql.arch.regs.write("rcx", 1)   # force b=!fail=1 -> equality "passes"
        # When cmov returns, ss_out holds the final value.
        elif st["ret"] is not None and addr == st["ret"]:
            st["ss"] = ql.mem.read(base + SS_OFF, 32).hex()
            ql.emu_stop()

    ql.hook_code(hook)
    try:
        ql.run()
    except Exception as e:
        st["ss"] = f"(error: {e})"
    return st["ss"]

if __name__ == "__main__":
    base_ss = run(fault=False)
    leak_ss = run(fault=True)
    print(f"[no fault] ss = {base_ss}")
    print(f"           {'OK: equals K_rej (rejection held)' if base_ss==K_REJ else 'MISMATCH vs K_rej'}")
    print(f"[  fault ] ss = {leak_ss}")
    print(f"           {'OK: equals K_TARGET (shared secret leaked)' if leak_ss==K_TARGET else 'MISMATCH vs K_TARGET'}")
    ok = (base_ss == K_REJ and leak_ss == K_TARGET)
    print(f"\nVERIFIED EMULATED LEAK: {ok}")
