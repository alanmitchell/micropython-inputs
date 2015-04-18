import pyb
import array
import math

# -------------------------- Classes to Manage All Inputs ----------------------------




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

    def __init__(self, pin_name, pull=pyb.Pin.PULL_UP, stable_read_count=12, **kwargs):
        InputBase.__init__(self, pin_name, pull=pull, **kwargs)
        self._mask = 2 ** stable_read_count - 1
        if pull == pyb.Pin.PULL_UP:
            self._reads = self._mask
            self._cur_val = 1
        else:
            self._reads = 0
            self._cur_val = 0


class Digital(DigitalBase):

    def __init__(self, pin_name, hl_func=None, lh_func=None, **kwargs):
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

    # Constants signifying whether one or both edges are counted.
    ONE_EDGE = 1
    BOTH_EDGES = 2

    def __init__(self, pin_name, stable_read_count=5, edges=ONE_EDGE, reset_on_read=False, **kwargs):
        DigitalBase.__init__(self, pin_name, stable_read_count=stable_read_count, **kwargs)
        self.edges = edges
        self.reset_on_read = reset_on_read
        self._low_to_high_count = 0
        self._high_to_low_count = 0
        self._new_val = None    # need to allocate memory here, not in interrupt routine

    def service_input(self):
        self._reads = ((self._reads << 1) | self._pin.value()) & self._mask
        if self._reads != 0 and self._reads != self._mask:
            # The prior set of readings have alternated between ones and zeroes
            # so a bouncy state is occurring.  Just return w/o changing value.
            return
        self._new_val = self._reads & 0x01
        if self._new_val == self._cur_val:
            # no change in value
            return
        if self._new_val > self._cur_val:
            # transition from low to high occurred.
            self._low_to_high_count += 1
        else:
            # transition from high to low occurred.
            self._high_to_low_count += 1
        self._cur_val = self._new_val

    def _compute_value(self):
        if self.edges == Counter.ONE_EDGE:
            ct = self._high_to_low_count
        else:
            ct = self._high_to_low_count + self._low_to_high_count
        if self.reset_on_read:
            self._high_to_low_count = self._low_to_high_count = 0
        return ct

    def reset_count(self):
        '''Resets the counts.
        '''
        irq_state = pyb.disable_irq()
        self._high_to_low_count = self._low_to_high_count = 0
        pyb.enable_irq(irq_state)


class AnalogBase(InputBase):

    def __init__(self, pin_name, buffer_size=144, **kwargs):
        InputBase.__init__(self, pin_name, **kwargs)
        self._adc = pyb.ADC(self._pin)
        self._buflen = buffer_size
        self._buf = array.array('H', [0] * buffer_size)
        self._ix = 0

    def service_input(self):
        self._buf[self._ix] = self._adc.read()
        self._ix = (self._ix + 1) % self._buflen


class Analog(AnalogBase):

    def _compute_value(self):
        return sum(self._buf)/self._buflen


class AnalogDeviation(AnalogBase):

    def _compute_value(self):
        sum_v = sum(self._buf)
        n = self._buflen
        sum_v2 = 0
        for v in self._buf:
            sum_v2 += v * v
        return math.sqrt((sum_v2 - sum_v*sum_v/n)/(n-1))

