# inputs.py
# Author: Alan Mitchell, tabb99@gmail.com
# Provides counters, debounced digital inputs, analog inputs with
# moving averages.

import pyb
import array
import math


# -------------------------- Classes to Manage All Inputs ----------------------------

class Manager:
    '''Class to manage and service a number of inputs.
    '''

    def __init__(self, inputs, timer_num=1, poll_freq=480):
        '''Arguments are:
        inputs: a list or tuple of Inputs objects that derive from InputBase.
        timer_num: the number of the microcontroller Timer that will be used to
            periodically poll the inputs.  If None is passed, no Timer will be
            set up automatically and you will need to periodically call 
            the 'service_inputs()` method from your own timer.
        poll_freq: the frequency in Hz to read the inputs.  The default value
            of 480 Hz means each input will be read every 2.08 ms (1000 ms / 480).
            Be careful about setting this too high as the time required to read
            each input will consume substantial CPU cycles.  Roughly, each input
            takes 80 usec to read.  Therefore, reading 20 inputs would require
            80 usec x 20 = 1600 usec or 1.6 ms.  If inputs are being read every 2.08 ms,
            the process of reading inputs consumes 1.6 / 2.08 or 77% of the CPU cycles.
        '''
        self.inputs = inputs
        if timer_num is not None:
            self._tim = pyb.Timer(timer_num, freq=poll_freq)
            self._tim.callback(self.service_inputs)

    def service_inputs(self, t):
        '''This method is called by the timer interrupt and runs the 'service_input'
        routine on each input.  That routine reads the input and does any required
        processing.
        '''
        for i in range(len(self.inputs)):
            self.inputs[i].service_input()

    def values(self):
        '''Returns the current values of all inputs as a MyDict object
        (basically a Python dictionary that also allows value access through
        attributes).
        The keys in the dictionary are the 'key_name' for the input (see
        InputBase class) and the dictionary values are the fully processed
        input values (e.g. debounced digital input values, counter values, moving
        average analog values).
        '''
        return MyDict([(inp.key_name(), inp.value()) for inp in self.inputs])

    def __getattr__(self, input_key):
        '''Returns a particular input with the key_name of 'input_key'.  This
        method is accessed by the obj.input_key sytax.
        '''
        for inp in self.inputs:
            if inp.key_name() == input_key:
                return inp
        raise KeyError


class MyDict(dict):
    '''A normal Python dictionary that also allows access to the value
    of each item as an attribute of the object.  For example,
    if 'd' is a MyDict object and has a key of 'abc', the value associated
    with 'abc' can be accessed via d['abc'] or via d.abc .
    '''

    def __getattr__(self, key_name):
        return self[key_name]


# ---------------------- The Base Input Class and all Dervied Input Classes


class InputBase(object):
    '''Base Class for all input types (digital and analog).  The input classes
    that are used inherit from this one.
    '''

    def __init__(self, pin_name, pull=pyb.Pin.PULL_NONE, convert_func=None):
        '''Arguments are:
        pin_name:  The Pyboard pin name, such as X1 or Y2, as string.  Optionally,
            a more descriptive name can be added after a colon, e.g. 'X1:outside_temp'.
            If the descriptive name is present, it will be used as the key for accessing
            the input's value.
        pull:  can be used to enable a pull-up or pull-down on the input line.  Must be
            one of the pyb.Pin.PULL_ constants and defaults to no pull on the input line.
        convert_func:  If a function is provided here, it will be applied to the input's
            value before being returned.  The function can be used to convert the value
            into engineering units or even a text string.
        '''
        name_parts = pin_name.split(':')
        self._pin_name = name_parts[0].strip()
        self._pin = pyb.Pin(self._pin_name, pyb.Pin.IN, pull)
        self.input_name = name_parts[1].strip() if len(name_parts) > 1 else None
        self.convert_func = convert_func

    def key_name(self):
        '''Returns the the descriptive input name, if present, otherwise the pin
        name is returned.  This value is used as the identifying name for
        the input.
        '''
        return self.input_name if self.input_name else self._pin_name

    def service_input(self):
        '''Override this method to read the input and do any required processing.
        This method is called every timer interrupt by the Manager class.
        '''
        pass

    def _compute_value(self):
        '''Override this method to return the input value, prior to applying any
        convert_func provided in the constructor.
        '''
        return None

    def value(self):
        '''Returns the final value of this input.  Interrupts are disabled so that
        the value isn't altered during retrieval.  The conversion function, if supplied,
        in the constructor is applied before returning.
        '''
        irq_state = pyb.disable_irq()
        val = self._compute_value()
        pyb.enable_irq(irq_state)
        return self.convert_func(val) if self.convert_func else val


class DigitalBase(InputBase):
    '''The base class for digital inputs.
    '''

    def __init__(self, pin_name, pull=pyb.Pin.PULL_UP, stable_read_count=12, **kwargs):
        '''New arguments not in the inheritance chain are:
        stable_read_count:  The number of consistent readings of the pin in order to
            declare that the pin has changed state.  If sampling occurs at 480 Hz, 
            reads of the pin will occur every 2.1 ms.  A 'stable_read_count' of 12
            means that the same value has to be read 12 times to be considered solid.
            Those 12 reads will span 2.1 ms x 12 = 25.2 ms.
        '''
        InputBase.__init__(self, pin_name, pull=pull, **kwargs)
        # create a bit mask that will spans 'stable_read_count' bits.
        self._mask = 2 ** stable_read_count - 1
        # start the variables in a state consistent with the PULL_UP.
        # the self._reads variable holds the digital readings, each reading
        # occupying one bit position; the most recent read is in the LSB
        # position.
        if pull == pyb.Pin.PULL_UP:
            self._reads = self._mask
            self._cur_val = 1
        else:
            self._reads = 0
            self._cur_val = 0


class Digital(DigitalBase):
    '''A class to provide a debounced digital value from a pin.
    '''

    def __init__(self, pin_name, hl_func=None, lh_func=None, **kwargs):
        '''Arguments not in the inheritance chain:
        hl_func: if a function is provided, it is called when the pin 
            transitions from a high state (1) to a low state (0).  This
            function call occurs during the Timer interrupt, so do not
            consume much time within the function.
        lh_func: if a function is provided, it is called when the pin
            transitions from a low state (0) to a high state(1).  The
            call occurs during the timer iterrupt.
        '''
        DigitalBase.__init__(self, pin_name, **kwargs)
        self.hl_func = hl_func
        self.lh_func = lh_func

    def service_input(self):
        # shift the prior readings over one bit, and put the new reading
        # in the LSb position.
        self._reads = ((self._reads << 1) | self._pin.value()) & self._mask
        if self._reads != 0 and self._reads != self._mask:
            # The prior set of readings have alternated between ones and zeroes
            # so a bouncy state is occurring.  Just return w/o changing value.
            return
        # there is a stable set of readings.  Get the stable value (either a
        # 1 or a 0)
        self._new_val = self._reads & 0x01
        if self._new_val == self._cur_val:
            # no change in value
            return
        if self._new_val > self._cur_val:
            # transition from low to high occurred.
            if self.lh_func:
                self.lh_func()
        else:
            # transition from high to low occurred.
            if self.hl_func:
                self.hl_func()
        self._cur_val = self._new_val

    def _compute_value(self):
        return self._cur_val


class Counter(DigitalBase):
    '''A class used to count pulses on a digital input pin.  The counter
    can count one or both edge transitions of the pulse.  Pin transitions
    are debounced.
    '''

    # Constants signifying whether one or both transition edges are counted.
    ONE_EDGE = 1
    BOTH_EDGES = 2

    def __init__(self, pin_name, stable_read_count=4, edges=ONE_EDGE, reset_on_read=False, 
                 rollover=1073741823, **kwargs):
        '''Arguments not in the inheritance chain:
        edges: Either ONE_EDGE or BOTH_EDGES indicating which transitions of the pulse to 
            count.
        reset_on_read: if True, the counter value will be reset to 0 after the count
            is read via a call to the value() method.
        rollover: count will roll to 0 when it hits this value.
        Note that the default 'stable_read_count' value is set to 4 reads.  With the 
        default 2.1 ms read interval, this requires stability for 8.4 ms.  Counters are
        often reed switches or electronic pulse trains, both of which have little to no
        bounce.  Using a low value for 'stable_read_count' increases the pulse frequency
        that can be read by the counter.
        '''
        DigitalBase.__init__(self, pin_name, stable_read_count=stable_read_count, **kwargs)
        self.edges = edges
        self.reset_on_read = reset_on_read
        self._rollover = rollover
        self._count = 0
        self._new_val = None    # need to allocate memory here, not in interrupt routine

    def service_input(self):
        # shift the prior readings over one bit, and put the new reading
        # in the LSb position.
        self._reads = ((self._reads << 1) | self._pin.value()) & self._mask
        if self._reads != 0 and self._reads != self._mask:
            # The prior set of readings have alternated between ones and zeroes
            # so a bouncy state is occurring.  Just return w/o changing value.
            return
        self._new_val = self._reads & 0x01
        if self._new_val == self._cur_val:
            # no change in value
            return
        if self._new_val < self._cur_val:
            # transition from high to low occurred.  Always count these
            # transitions.
            self._count = (self._count + 1) % self._rollover
        elif self.edges == Counter.BOTH_EDGES:
            # A low to high transition occurred and counting both edges
            # was requested, so increment counter.
            self._count = (self._count + 1) % self._rollover
        self._cur_val = self._new_val

    def _compute_value(self):
        ct = self._count
        if self.reset_on_read:
            self._count = 0
        return ct

    def reset_count(self):
        '''Resets the counts and protects the processs form being
        interrupted.
        '''
        irq_state = pyb.disable_irq()
        self._count = 0
        pyb.enable_irq(irq_state)


class AnalogBase(InputBase):
    '''Base class for analog input pins.
    '''

    def __init__(self, pin_name, buffer_size=144, **kwargs):
        '''Arguments not in inheritance chain:
        buffer_size: the number readings to include in the moving
            average.  If the sampling frequency is 480 Hz and 144
            readings are included in the moving average, the average
            spans 144 / 480 = 0.3 seconds.  For cancellation of 60 Hz
            noise, it is good to have this time be an exact number of
            60 Hz cycles.  0.3 seconds is exactly 18 full 60 Hz cycles.
        '''
        InputBase.__init__(self, pin_name, **kwargs)
        self._adc = pyb.ADC(self._pin)
        self._buflen = buffer_size
        # create a ring array with 2 byte elements, sufficient to
        # store the 12-bit ADC readings.
        self._buf = array.array('H', [0] * buffer_size)
        self._ix = 0   # ring array index

    def service_input(self):
        self._buf[self._ix] = self._adc.read()
        self._ix = (self._ix + 1) % self._buflen


class Analog(AnalogBase):
    '''Analog input that returns a moving average of the input pin.
    '''

    def _compute_value(self):
        # return the average value in the ring buffer.
        return sum(self._buf)/self._buflen


class AnalogDeviation(AnalogBase):
    '''Analog input that returns the standard deviation of the readings
    in the ring buffer.
    '''

    def _compute_value(self):
        # returns standard deviation of values in the ring buffer.
        n = self._buflen
        mean = sum(self._buf) / n
        dev_sq = 0.0
        for v in self._buf:
            dev = v - mean
            dev_sq += dev * dev
        return math.sqrt(dev_sq/(n-1))
