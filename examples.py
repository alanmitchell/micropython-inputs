# Example of using the "inputs" library with the Micro Python pyboard.

import time
from inputs import Manager, Digital, Counter, Analog

# List the desired inputs and pass them to a Manager object. 
mgr = Manager([Digital('Y1:button1'),
               Counter('Y2'),
               Analog('X1:sensor1_volts', convert_func=lambda x: x / 4095 * 3.3)])

# The manager object immediately starts polling the inputs after instantiation.

# wait until the Analog input reading buffer before reading all the inputs the 
# first time.
time.sleep(0.4)

while True:
    # get a snapshot of all the current input values
    vals = mgr.values()

    print(vals)  # prints the entire dictionary of readings

    # prints two individual readings, using normal dictionary access and also
    # attribute access.
    print(vals['button1'], vals.sensor1_volts, '\n')
    
    time.sleep(1)
