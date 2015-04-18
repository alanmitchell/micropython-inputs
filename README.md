# micropython-inputs
This micropython library facilitates reading digital and analog inputs on the pyboard or other microcontrollers running micropython.  Some of the notable features are:

* Digital input pins are debounced so transitions are detected cleanly.  Debouncing parameters are controllable by the user.
* Digital input pins can be configured as counters for counting pulse trains.  Either one or both edges of the pulses can be counted, and debouncing is present to clean up reed switch closures.
* Analog readings are averaged across a user-selectable number of recent readings spaced at 2.1 ms (configurable) intervals.  Noise on the analog line can effectively be suppressed with this averaging technique.
* Current values from the pins are easily accessible through a Python dictionary, keyed by either the Pin name or a more descriptive name you can assign to the pin.

## Quickstart

Here is some code that demonstrates how the library is used:

```Python
from inputs import Manager, Digital, Counter, Analog

# We create this function that will be called when there is a
# High-to-Low transition on a Digital pin we will set up.
def hl_occurred():
    print('High to Low transition occurred!')


# the Manager class holds the input objects and polls them at a regular 
# interval from a Timer interrupt.
# Here we set up a Digital Input, a Counter Input, and an Analog Input by
# passing a list of input objects to the Manager constructor.
mgr = Manager([Digital('Y1:button1', hl_func=hl_occurred),
               Counter('Y2', edges=Counter.BOTH_EDGES),
               Analog('X1:sensor1_volts', convert_func=lambda x: x / 4095 * 3.3)])

```