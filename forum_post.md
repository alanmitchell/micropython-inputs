### Library for Debouncing, Counting Pulses, and Averaging Analog Signals

I just released a Micro Python library that makes it easier to do certain tasks with input pins.  Here is the [link to it on GitHub](https://github.com/alanmitchell/micropython-inputs). My motivations were:

* I wanted to be able to debounce digital inputs in software and run callback functions when the digital inputs changed state.
* I wanted to be able to count pulses from things like electric meters and water meters, including some debouncing to compensate for reed switch closure bounces.
* I wanted to filter noise out of analog input channels by using a moving average of multiple readings.
* I wanted to read current input values into a data structure that is easy to work with in my data acquistion and controller code.

Here is some sample code from use of the library.  It sets up a button input on pin Y1, a counter input on pin Y2 and an analog input on X1.  Descriptive names are assigned to the Y1 and X1 inputs.  Numerous configuration options are not shown in this simple example:

```Python
import time
from inputs import Manager, Digital, Counter, Analog

# List the desired inputs and pass them to a Manager object. 
mgr = Manager([Digital('Y1:button1'),
               Counter('Y2'),
               Analog('X1:sensor1_volts', convert_func=lambda x: x / 4095 * 3.3)])

# The manager object immediately starts polling the inputs after instantiation.

while True:
    # get a snapshot of all the current input values
    vals = mgr.values()

    print(vals)  # prints the entire dictionary of readings

    # prints two individual readings, using normal dictionary access and also
    # attribute access.
    print(vals['button1'], vals.sensor1_volts, '\n')
    
    time.sleep(1)
```

Much more documentation is present in the README.md on the GitHub site.  Feeback is appreciated.

