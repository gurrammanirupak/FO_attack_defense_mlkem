#include <stddef.h>
extern int  ct_verify(const unsigned char *a, const unsigned char *b, size_t n); /* opaque, other TU */
extern void fo_trap(void);                                                        /* opaque trap      */

/* Style A1: naive scalar DMR -- the equality committed to two locals */
int accept_naive_scalar(unsigned char x, unsigned char y) {
    int fail1 = (x == y) ? 0 : 1;
    int fail2 = (x == y) ? 0 : 1;          /* optimizer can prove fail1 == fail2 */
    if (fail1 != fail2) fo_trap();          /* can it drop this trap? */
    return fail1;
}

/* Style A2: realistic hand-written constant-time compare, duplicated inline */
static inline int ct_eq(const unsigned char *restrict a, const unsigned char *restrict b, size_t n){
    unsigned char d = 0;
    for (size_t i = 0; i < n; i++) d |= (unsigned char)(a[i] ^ b[i]);
    return d;                               /* 0 == equal */
}
int accept_naive_inline(const unsigned char *restrict a, const unsigned char *restrict b, size_t n){
    int fail1 = ct_eq(a, b, n);
    int fail2 = ct_eq(a, b, n);             /* two inline loops -- does -O3 merge them? */
    if (fail1 != fail2) fo_trap();
    return fail1;
}

/* Style B: opaque call-based DMR -- exactly what the STM32F3 firmware uses */
int accept_calls(const unsigned char *a, const unsigned char *b, size_t n){
    int fail1 = ct_verify(a, b, n);
    int fail2 = ct_verify(a, b, n);         /* opaque calls -- cannot be merged */
    if (fail1 != fail2) fo_trap();
    return fail1;
}
