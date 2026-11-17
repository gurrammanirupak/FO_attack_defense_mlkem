#!/usr/bin/env bash
# Reproduces: optimization-dependent survival of a duplicate-check (DMR) trap
# in the ML-KEM FO verification. Target compiler: arm-none-eabi-gcc 13.2.1
# (identical to the STM32F3 firmware). Corroborated on gcc-13 / clang-18.
set -e; cd "$(dirname "$0")"
ARMGCC="arm-none-eabi-gcc -mcpu=cortex-m4 -mthumb -mfloat-abi=soft -march=armv7e-m -std=gnu99"
ARMCLANG="clang --target=armv7em-none-eabi -mcpu=cortex-m4 -mthumb -std=gnu99"
HGCC="gcc -std=gnu99"; HCLANG="clang -std=gnu99"
row () { label="$1"; shift; printf "  %-11s" "$label"
  for O in -O0 -O1 -O2 -O3 -Os; do
    s=$("$@" $O -S -o - dmr_demo.c 2>/dev/null | awk '
      /^[A-Za-z_][A-Za-z0-9_]*:/{fn=$1;sub(":.*","",fn)}
      fn~/^accept_/&&/fo_trap/{t[fn]=1}
      END{printf "%s%s%s",(t["accept_naive_scalar"]?"S":"x"),(t["accept_naive_inline"]?"S":"x"),(t["accept_calls"]?"S":"x")}')
    printf " %-7s" "$O=$s"; done; echo; }
echo "Legend: [naive-scalar][inline-CT-loop][opaque-verify-calls]  S=survives x=stripped"
printf "  %-11s %-7s %-7s %-7s %-7s %-7s\n" compiler -O0 -O1 -O2 -O3 -Os
row arm-gcc $ARMGCC; row arm-clang $ARMCLANG; row host-gcc $HGCC; row host-clang $HCLANG
echo; echo "=== arm-gcc -O3 disassembly: naive-scalar (folded) vs verify-calls (kept) ==="
$ARMGCC -O3 -c dmr_demo.c -o /tmp/a.o
arm-none-eabi-objdump -d --no-show-raw-insn /tmp/a.o | sed -n '/<accept_naive_scalar>:/,/<accept_naive_inline>:/p'
arm-none-eabi-objdump -d --no-show-raw-insn /tmp/a.o | sed -n '/<accept_calls>:/,/^$/p'
