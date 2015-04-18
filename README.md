# micropython-inputs
This micropython library facilitates reading digital and analog inputs on the pyboard or other microcontrollers running micropython.  Some of the notable features are:

* Digital input pins are debounced so transitions are detected cleanly.  Debouncing parameters are controllable by the user.
* Digital input pins can be configured as counters for counting pulse trains.  Either one or both edges of the pulses can be counted, and debouncing is present to clean up reed switch closures.
* Analog readings are averaged across a user-selectable number of recent readings spaced at 2.1 ms (configurable) intervals.  Noise on the analog line can effectively be suppressed with this averaging technique.
* Current values from the pins are easily accessible through a Python dictionary, keyed by either the Pin name or a more descriptive name you can assign to the pin.

## Quickstart

Suppose we need to set up an input to detect button presses, a counter to count the pulses from a water meter utilizing a dry contact reed switch, and an Analog input to measure a sensor voltage.  Here is the setup code:

```Python
from inputs import Manager, Digital, Counter, Analog

# We create this function that will be called when there is a
# High-to-Low transition on a Digital pin we will set up.
def hl_occurred():
    print('High to Low transition occurred!')


# the Manager class holds the input objects and polls them at a regular 
# interval from a Timer interrupt.  We pass a list of the three needed
# input objects to the constructor.
mgr = Manager([Digital('Y1:button1', hl_func=hl_occurred),
               Counter('Y2'),
               Analog('X1:sensor1_volts', convert_func=lambda x: x / 4095 * 3.3)])
```
The first parameter passed to constructor of each Input object is the name of the pin to use for the input.  For example, the Counter input uses the Y2 pin.  Optionally, a more descriptive name can be added after a colon.  The Digital input uses Pin Y1 and is labeled `button1`.  If a descriptive name is provided, it will be used for all labeling and accessing of the input.

Each input type has a number of configuration options, all with default values except from the required pin name.  Some of the configuration options are shown in the example.  For the Digital input, a function is passed in that will be called when the input makes a clean transition from High (1) to Low (0). For the Analog input, a conversion function is passed in that takes the raw 0 - 4095 reading from the Analog pin and converts it to a voltage value.  Either a lambda function, as shown here, or a normal multi-line `def` function name can be passed.

After the Manager object is created, it automatically starts polling the input objects at the default rate of 480 Hz (an even multiple of 60 Hz to cause 60 Hz noise to be filtered on Analog lines).  Each input is read and processed according to the type of input it is.

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

I will be using the pyboard as a data acquistion peripheral for the Raspberry Pi.  A simple way to transfer the input value to the Pi is to print the `vals` dictionary.  When the Pi receives the string representation of the dictionary, a call to `eval()` will convert the string back into a dictionary.