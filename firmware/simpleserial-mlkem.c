#include "hal.h"
#include "simpleserial.h"
#include "params.h"
#include "api.h"
#include <string.h>
#include "random_data.h"

/* ML-KEM-768 buffers */
uint8_t test_ct[KYBER_CIPHERTEXTBYTES];
uint8_t test_sk[KYBER_SECRETKEYBYTES];
uint8_t ss[KYBER_SSBYTES];
uint8_t ct_work[KYBER_CIPHERTEXTBYTES];

/* FO-check trigger hooks called by the DMR code in kem.c */
void fo_trigger_high(void){ trigger_high(); }
void fo_trigger_low(void){ trigger_low(); }

/* Defense trap: udf -> UsageFault/HardFault -> 0xEE sentinel */
void fo_trap(void){ __builtin_trap(); }

void HardFault_Handler(void){
    uint8_t s[32]; for(int i=0;i<32;i++) s[i]=0xEE;
    simpleserial_put('r', 32, s);
    for(volatile int i=0;i<300000;i++);      /* let UART drain */
    *((volatile uint32_t*)0xE000ED0C) = 0x05FA0004;   /* system reset */
    while(1);
}
void UsageFault_Handler(void){ HardFault_Handler(); }
void BusFault_Handler(void){ HardFault_Handler(); }
void MemManage_Handler(void){ HardFault_Handler(); }

/* 'd' : full (defended) decapsulation, return shared secret */
static uint8_t handle_dec_test(uint8_t* cmd, uint8_t len)
{
    (void)cmd; (void)len;
    memcpy(ct_work, test_ct, KYBER_CIPHERTEXTBYTES);
    pqcrystals_kyber768_ref_dec(ss, ct_work, test_sk);
    simpleserial_put('r', KYBER_SSBYTES, ss);
    return 0;
}

/* 't' : decapsulation cycle count via DWT (for overhead measurement) */
static uint8_t handle_time(uint8_t* cmd, uint8_t len)
{
    (void)cmd; (void)len;
    volatile uint32_t *CYC = (volatile uint32_t*)0xE0001004;  /* DWT_CYCCNT */
    memcpy(ct_work, test_ct, KYBER_CIPHERTEXTBYTES);
    uint32_t t0 = *CYC;
    pqcrystals_kyber768_ref_dec(ss, ct_work, test_sk);
    uint32_t dt = *CYC - t0;
    simpleserial_put('r', 4, (uint8_t*)&dt);
    return 0;
}

static uint8_t handle_set_ct(uint8_t* cmd, uint8_t len)
{ if (len <= KYBER_CIPHERTEXTBYTES) memcpy(test_ct, cmd, len); return 0; }

static uint8_t handle_set_sk(uint8_t* cmd, uint8_t len)
{ if (len <= KYBER_SECRETKEYBYTES) memcpy(test_sk, cmd, len); return 0; }

static uint8_t handle_cycle_profile(uint8_t* cmd, uint8_t len)
{ (void)cmd; (void)len; trigger_high(); trigger_low(); return 0; }

int main(void)
{
    platform_init();
    init_uart();
    trigger_setup();

    /* enable DWT cycle counter */
    *((volatile uint32_t*)0xE000EDFC) |= (1u<<24);   /* TRCENA */
    *((volatile uint32_t*)0xE0001000) |= 1u;         /* CYCCNTENA */

    simpleserial_init();
    memcpy(test_ct, RANDOM_CT, KYBER_CIPHERTEXTBYTES);
    memcpy(test_sk, RANDOM_SK, KYBER_SECRETKEYBYTES);

    simpleserial_addcmd('d', 0, handle_dec_test);
    simpleserial_addcmd('t', 0, handle_time);
    simpleserial_addcmd('c', KYBER_CIPHERTEXTBYTES, handle_set_ct);
    simpleserial_addcmd('s', KYBER_SECRETKEYBYTES, handle_set_sk);
    simpleserial_addcmd('p', 0, handle_cycle_profile);

    while(1) simpleserial_get();
}
