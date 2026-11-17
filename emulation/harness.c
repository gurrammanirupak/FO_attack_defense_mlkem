#include <stdint.h>
#include <stdio.h>
#include "random_data.h"
extern int pqcrystals_kyber768_ref_dec(uint8_t *ss, const uint8_t *ct, const uint8_t *sk);
uint8_t ss_out[32];
int main(void){
    pqcrystals_kyber768_ref_dec(ss_out, RANDOM_CT, RANDOM_SK);
    for(int i=0;i<32;i++) printf("%02x", ss_out[i]);
    printf("\n");
    return 0;
}
