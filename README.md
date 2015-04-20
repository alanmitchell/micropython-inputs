# micropython-inputs
This Micro Python library facilitates reading digital and analog inputs on the pyboard or other microcontrollers running [Micro Python](http://micropython.org/), a variant of the Python 3 programming language.  These library routines were tested on a [pyboard, available here](https://micropython.org/store/#/store).  Some of the notable features of this library are:

* Digital input pins are debounced so transitions are detected cleanly.  Debouncing parameters are controllable by the user.
* Digital input pins can be configured as counters for counting pulse trains.  Either one or both edges of the pulses can be counted, and debouncing is present to clean up reed switch closures.
* Analog readings are averaged across a user-selectable number of recent readings spaced at 2.1 ms (user configurable) intervals.  Noise on the analog line can be significantly suppressed with this averaging technique.
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
mgr = Manager([Digital('Y1: button1', hl_func=hl_occurred),
               Counter('Y2'),
               Analog('X1: sensor1_volts', convert_func=lambda x: x / 4095 * 3.3)])
```
The first argument passed to constructor of each Input object is the name of the pin to use for the input.  For example, the Counter input uses the Y2 pin.  Optionally, a more descriptive name can be added after a colon.  The Digital input uses Pin Y1 and is labeled `button1`.  If a descriptive name is provided, it will be used for all labeling and accessing of the input.

Each Input object type has a number of configuration options, all with default values except for the required `pin_name` argument.  Some of the configuration options are shown in the example.  For the Digital input in this example, a function is passed that will be called when the input makes a clean transition from High (1) to Low (0). For the Analog input, a conversion function is passed that takes the raw 0 - 4095 reading from the Analog pin and converts it to a voltage value.  Either a lambda function, as shown here, or a normal multi-line `def` function name can be passed.

After the Manager object is created, it automatically starts polling the input objects at the default rate of 480 Hz (a 2x or greater multiple of 60 Hz will help filter 60 Hz noise on Analog lines).  Each input is read and processed according to the type of input it is.

At any time, the current values of all the inputs can be read by executing the `values()` method on the Manager object.  The return object is a Python dictionary with the added feature that values can be read as attributes of the object:

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

mgr = Manager([Digital('Y1: button1'),
               Counter('Y2'),
               Analog('X1: sensor1_volts', convert_func=lambda x: x / 4095 * 3.3)])

# wait to fill the Analog buffer with readings before reading the first time.
time.sleep(0.4)
while True:
    vals = mgr.values()
    print(vals)
    time.sleep(1)
```

And here is a sample of the output from the program:

```
{'Y2': 0, 'button1': 1, 'sensor1_volts': 1.64033}
{'Y2': 1, 'button1': 0, 'sensor1_volts': 1.639513}
{'Y2': 2, 'button1': 0, 'sensor1_volts': 1.639983}
{'Y2': 2, 'button1': 1, 'sensor1_volts': 1.639995}
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
Arguments for instantiating a Manager object include:

`inputs`: This is the list of input objects that the Manager will periodically poll and manage.

`timer_num`: The number of the microcontroller Timer that will be used to generate an interrupt for polling the inputs.  If `None` is passed, no automatic polling of inputs will occur, and you will need to periodically call the `service_inputs()` method of this object, perhaps from your own Timer interrupt routine.

`poll_freq`: The frequency that will be used to poll the inputs in Hz.  The default of 480 Hz will poll each sensor every 2.08 ms, which is a convenient value for debounce routines discussed later and analog averaging routines that sample across an exact number of 60 Hz cycles.

**Manager.values**()  
This returns a snapshot of all of the current inputs.  The return object is a Python dictionary with the added feature of being able to use an attribute to access a value as well as standard dictionary syntax.  If `vals` is the object returned by this method, these two read access means are equivalent:  `vals['X1']` and `vals.X1`.

**Manager.service_inputs**()  
This routine reads and services all of the inputs and does not normally need to be used; it is generally called from a Timer interrupt internally set up by the Manager object.  However, if this internal Timer is disabled by passing `None` to the `timer_num` constructor argument, a user can use their own Timer interrupt to periodically call this `service_inputs()` method.

---

### Methods Common to All Input Classes

A number of methods are present on all the Input classes below, including:

InputClass.**value**()  
This returns the current value for the input, including all processing that occurs for that input, e.g. debouncing, averaging.

InputClass.**key_name**()  
This returns the pin name, e.g. 'X1', or, if a descriptive name for the input was provided, the descriptive name is returned instead.

InputClass.**service_input**()  
If you are using one of the Input objects without use of the Manager object, this is the method that must be periodically called to update and process new input values.

---

### Digital class
This class handles a digital input pin, providing debouncing and the ability to have callback functions that run when the pin changes state.

**Digital**(pin_name, pull=pyb.Pin.PULL_UP, convert_func=None,
            stable_read_count=12, hl_func=None, lh_func=None)  
Arguments for instantiating a Digital object include:

`pin_name`: The microcontroller pin name, such as 'X1' or 'Y2'.  Optionally a descriptive name can be provided after a separating colon, e.g. 'X1: button1'.  If the descriptive name is provided, it will be used instead of the pin name for accessing the input.

`pull`:  A pull up or pull down resistor can be enabled on the pin by setting this argument to one of the `pyb.Pin.PULL_` constants.

`convert_func`:  A Digital input normally reads a 0 or a 1 value.  If you want these two values translated to something else (even a string), provide the name of a conversion function here, or enter a Python lambda function.

`stable_read_count`:  The digital input pin is read repeatedly at a rate determined by the `poll_freq` value passed to the Manager class.  To debounce the input, a changed input value must remain the same for `stable_read_count` readings.  If so, a state changed is deemed to occur.  The default value is 12 readings in a row, and with the default polling frequency of 480 Hz (2.08 ms spacing), the reading must remain stable for about 25 ms to be considered valid.  This argument must be set to a value of 30 stable readings or less. 

`hl_func`: A callback function that will be run when the input stably transitions from a 1 value to a 0 value.  This callback function is run
from inside a Timer interrupt routine, so do not consume much time in
the function you provide, as it will block future interrupts.

`lh_func`: A callback function that will be run when the input stably transitions from a 0 value to a 1 value. This callback function is run
from inside a Timer interrupt routine, so do not consume much time in
the function you provide, as it will block future interrupts.

---

### Counter class
This class uses a digital input pin to count pulses.  Transitions on the pin are debounced before counting.

**Counter**(pin_name, pull=pyb.Pin.PULL_UP, convert_func=None,  
stable_read_count=4, edges=Counter.ONE_EDGE, reset_on_read=False,   
rollover=1073741823)

Arguments for instantiating a Digital object include:

`pin_name`: The microcontroller pin name, such as 'X1' or 'Y2'.  Optionally a descriptive name can be provided after a separating colon, e.g. 'X1: button1'.  If the descriptive name is provided, it will be used instead of the pin name for accessing the input.

`pull`:  A pull up or pull down resistor can be enabled on the pin by setting this argument to one of the `pyb.Pin.PULL_` constants.

`convert_func`:  The value returned by the Counter object is the count that has accumulated.  If you want this count value translated to something else, provide the name of a conversion function here, or enter a Python lambda function.

`stable_read_count`:  The digital input pin is read repeatedly at a rate determined by the `poll_freq` value passed to the Manager class.  To debounce the input, a changed input value must remain the same for `stable_read_count` readings.  If so, a state changed is deemed to occur.  The default value is 4 readings in a row, and with the default polling frequency of 480 Hz (2.08 ms spacing), the reading must remain stable for about 8.3 ms to be considered valid.  Electronic generated pulses and reed switch pulses have little or no bounce, so a small stable read count can be used to increase the maximum pulse rate that can be read.  This argument must be set to a value of 30 stable readings or less. 

`edges`:  This argument determines whether the falling edge alone of the pulse is counted, or whether both the falling and rising edges are counted.  It must be either the constant `Counter.ONE_EDGE` or the constant `Counter.BOTH_EDGES`.

`reset_on_read`: If True, the count is reset to 0 every time the count value is read through use of the `value()` method.

`rollover`:  If the count reaches this value it will reset to 0.  The default rollover value of 1073741823 is the largest that is possible.  

**Counter.reset_count**()  
This method will reset the count to zero.

---

### Analog class
This class is used to read analog values on an analog input pin.  A moving average of prior reads is calculated to help reduce the impacts of noise on the pin.  The value() returned by the class is the 12 bit ADC count, ranging from 0 - 4095.

**Analog**(pin_name, pull=pyb.Pin.PULL_NONE, convert_func=None,  
buffer_size=144,)
The arguments for instantiating an Analog input object are:

`pin_name`: The microcontroller pin name, such as 'X1' or 'Y2'.  Optionally a descriptive name can be provided after a separating colon, e.g. 'X1: button1'.  If the descriptive name is provided, it will be used instead of the pin name for accessing the input.

`pull`:  While not normally used with an analog channel, a pull up or pull down resistor can be enabled on the pin by setting this argument to one of the `pyb.Pin.PULL_` constants.

`convert_func`:  The value returned by the Analog object is the 12 bit ADC value, ranging from 0 - 4095. If you want this value translated to something else, provide the name of a conversion function here, or enter a Python lambda function.  For example, to convert the ADC value into measured voltage, use `convert_func=lambda x: x / 4095 * 3.3`.

`buffer_size`:  This is the number of recent readings that you want averaged together to determine the final value returned by the `value()` method.  At the default sampling rate of 480 Hz, 144 reading values take 0.3 seconds to complete and span 16 complete 60 Hz cycles.

---

### AnalogDeviation class
The AnalogDeviation class measures the standard deviation of the signal on an analog input pin.  The standard deviation is expressed in terms of the ADC units, which range from 0 to 4095 for the 12-bit converter.

The instantiation arguments and methods are identical for this class and the `Analog` class.  The only difference is that this class returns the standard deviation of the signal instead of the average value of the signal.
