#include <stddef.h>
int ct_verify(const unsigned char *a, const unsigned char *b, size_t n){
    unsigned char d = 0;
    for (size_t i = 0; i < n; i++) d |= (unsigned char)(a[i]^b[i]);
    return d; /* 0 == equal */
}
void fo_trap(void){ __builtin_trap(); }
