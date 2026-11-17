# ATTACK build: plain arm-none-eabi-gcc, NO clang-wrap, NO FODefensePass.
# This is the unprotected vulnerable baseline -- exactly what you glitch.
TARGET = simpleserial-mlkem

SRC += simpleserial-mlkem.c
SRC += kem.c
SRC += indcpa.c
SRC += polyvec.c
SRC += poly.c
SRC += ntt.c
SRC += cbd.c
SRC += reduce.c
SRC += verify.c
SRC += fips202.c
SRC += symmetric-shake.c
SRC += randombytes_stub.c

PLATFORM = CW308_STM32F3
CRYPTO_TARGET = NONE
SS_VER = SS_VER_1_1
OPT = 3

FIRMWAREPATH = ..
include $(FIRMWAREPATH)/Makefile.inc
