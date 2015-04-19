import time
from inputs import Manager, Digital, Counter, Analog

mgr = Manager([Digital('Y1:button1'),
               Counter('Y2'),
               Analog('X1:sensor1_volts', convert_func=lambda x: x / 4095 * 3.3)])

# wait to fill the Analog buffer with readings before reading the first time.
time.sleep(0.4)
while True:
    vals = mgr.values()
    print(vals)
    time.sleep(1)
