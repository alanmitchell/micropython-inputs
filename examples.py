import time
from inputs import Manager, Digital, Counter, Analog, AnalogDeviation


def hl_occurred():
    print('High to Low transition occurred!')


mgr = Manager([Digital('Y1:button1', hl_func=hl_occurred),
               Counter('Y2', edges=Counter.BOTH_EDGES),
               Analog('X1:sensor1_volts', convert_func=lambda x: x / 4095 * 3.3),
               AnalogDeviation('X2:coil_sensor')])
while True:
    vals = mgr.values()
    print(vals)
    print('Value access through attributes: %.3f V' % vals.sensor1_volts)
    #gc.collect()
    #print(gc.mem_free())
    time.sleep(1)
