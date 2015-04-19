# micropython-inputs
This Micro Python library facilitates reading digital and analog inputs on the pyboard or other microcontrollers running [Micro Python](http://micropython.org/), a variant of the Python 3 programming language that runs on some microcontrollers.  These library routines were tested on a [pyboard, available here](https://micropython.org/store/#/store).  Some of the notable features of this library are:

* Digital input pins are debounced so transitions are detected cleanly.  Debouncing parameters are controllable by the user.
* Digital input pins can be configured as counters for counting pulse trains.  Either one or both edges of the pulses can be counted, and debouncing is present to clean up reed switch closures.
* Analog readings are averaged across a user-selectable number of recent readings spaced at 2.1 ms (configurable) intervals.  Noise on the analog line can be significantly suppressed with this averaging technique.
* Current values from the pins are easily accessible through a Python dictionary, keyed by either the Pin name or a more descriptive name you can assign to the pin.

## Quickstart

The entire library resides in one file, `inputs.py`.  Suppose we need to set up an input to detect button presses, a counter to count the pulses from a water meter utilizing a reed switch, and an Analog input to measure a sensor voltage.  Here is the setup code:

```Python
from inputs import Manager, Digital, Counter, Analog

# We create this function that will be called when there is a
# High-to-Low transition on a Digital pin we set up below.
def hl_occurred():
    print('High to Low transition occurred!')


# the Manager class holds the input objects and polls them at a regular 
# interval from a Timer interrupt.  We pass a list of the three needed
# input objects to the constructor.
mgr = Manager([Digital('Y1:button1', hl_func=hl_occurred),
               Counter('Y2'),
               Analog('X1:sensor1_volts', convert_func=lambda x: x / 4095 * 3.3)])
```
The first argument passed to constructor of each Input object is the name of the pin to use for the input.  For example, the Counter input uses the Y2 pin.  Optionally, a more descriptive name can be added after a colon.  The Digital input uses Pin Y1 and is labeled `button1`.  If a descriptive name is provided, it will be used for all labeling and accessing of the input.

Each Input object type has a number of configuration options, all with default values except for the required `pin_name` argument.  Some of the configuration options are shown in the example.  For the Digital input, a function is passed in that will be called when the input makes a clean transition from High (1) to Low (0). For the Analog input, a conversion function is passed in that takes the raw 0 - 4095 reading from the Analog pin and converts it to a voltage value.  Either a lambda function, as shown here, or a normal multi-line `def` function name can be passed.

After the Manager object is created, it automatically starts polling the input objects at the default rate of 480 Hz (a 2x or greater multiple of 60 Hz will help 60 Hz noise to be filtered on Analog lines).  Each input is read and processed according to the type of input it is.

At any time, the current values of all the inputs can be read by executing the `values()` method on the Manager object.  The return object is a superset of a Python dictionary, also allowing access to values through attributes:

```Python
# get all of the current input values
vals = mgr.values()

# two different ways of accessing the current counter value on pin Y2.
print(vals['Y2'])
print(vals.Y2)

# for pins with descriptive names, you must use the descriptive name to access
# the input value.  Note that if the descriptive name contains spaces,
# attribute access will not work, and instead, standard dictionary access
# should be used:  vals['descriptive name']
print(vals.button1)
```

I will be using the pyboard as a data acquistion peripheral for the Raspberry Pi.  A simple way to transfer the input values to the Pi is to print the `vals` dictionary.  When the Pi receives the string representation of the dictionary, a call to `eval()` will convert the string back into a dictionary.  Here is a complete pyboard program for printing three input values out the USB port every second:

```Python
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
```

And here is a sample of the output from the program:

```
{'Y2': 3, 'button1': 1, 'sensor1_volts': 1.64033}
{'Y2': 3, 'button1': 1, 'sensor1_volts': 1.639513}
{'Y2': 3, 'button1': 1, 'sensor1_volts': 1.639983}
```

If you want to access one individual input object, perhaps to read its value alone or change its descriptive name, you can do that through attribute access on the Manager object:

```Python
# counter_obj will contain the full Counter object, not just its current value.
counter_obj = mgr.Y2

# print the counter's current value
print(counter_obj.value())
```

## CPU Resources

If you are setting up many input objects, you need to consider the amount of load you will put on the CPU.  Each input takes roughly 80 usec to poll.  If you have 20 inputs, total time consumed in the Timer interrupt routine polling the inputs will be 20 x 80 usec = 1600 usec, or 1.6 ms.  The default polling rate is 2.1 ms, so the polling process will consumer 76% of your CPU resources. This may or may not be acceptable, depending on your application.

## Documentation of Classes

This section documents the public interface to classes in the micropython-inputs library.

### Manager class

This class holds the configured Input objects, periodically polls each input to update the input's value, and provides convenient ways to return the current value of inputs.

**Manager**(inputs, timer_num=1, poll_freq=480)  

Arguments include:

`inputs`: This is the list of input objects that the Manager will periodically poll and manage.

`timer_num`: The number of the microcontroller Timer that will be used to generate an interrupt for polling the inputs.

`poll_freq`: The frequency that will be used to poll the inputs in Hz.  The default of 480 Hz will poll each sensor every 2.08 ms, which is a convenient value for debounce routines discussed later and analog averaging routines that sample across an exact number of 60 Hz cycles.