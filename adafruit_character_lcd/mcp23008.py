# MCP23008 I2C GPIO Extender Driver
# Bare-bones driver for the MCP23008 driver, as used by the character LCD
# backpack.  This exposes the MCP2308 and its pins as standard CircuitPython
# digitalio pins.  Currently this is integrated in the character LCD class for
# simplicity and reduction in dependent imports, but it could be broken out
# into a standalone library later.
# Author: Tony DiCola
import digitalio

import adafruit_bus_device.i2c_device as i2c_device


# Registers and other constants:
_MCP23008_ADDRESS       = const(0x20)
_MCP23008_IODIR         = const(0x00)
_MCP23008_IPOL          = const(0x01)
_MCP23008_GPINTEN       = const(0x02)
_MCP23008_DEFVAL        = const(0x03)
_MCP23008_INTCON        = const(0x04)
_MCP23008_IOCON         = const(0x05)
_MCP23008_GPPU          = const(0x06)
_MCP23008_INTF          = const(0x07)
_MCP23008_INTCAP        = const(0x08)
_MCP23008_GPIO          = const(0x09)
_MCP23008_OLAT          = const(0x0A)


class MCP23008:

    # Class-level buffer for reading and writing registers with the device.
    # This reduces memory allocations but makes the code non-reentrant/thread-
    # safe!
    _BUFFER = bytearray(2)

    class DigitalInOut:
        """Digital input/output of the MCP23008.  The interface is exactly the
        same as the digitalio.DigitalInOut class (however the MCP23008 does not
        support pull-down resistors and an exception will be thrown
        attempting to set one).
        """

        def __init__(self, pin_number, mcp23008):
            """Specify the pin number of the MCP23008 (0...7) and MCP23008
            instance.
            """
            self._pin = pin_number
            self._mcp = mcp23008

        def switch_to_output(value=False, **kwargs):
            self.direction = digitalio.Direction.OUTPUT
            self.value = value

        def switch_to_input(self, pull=None, **kwargs):
            self.direction = digitalio.Direction.INPUT
            self.pull = pull

        @property
        def value(self):
            gpio = self._mcp.gpio
            return bool(gpio & (1 << self._pin))

        @value.setter
        def value(self, val):
            gpio = self._mcp.gpio
            if val:
                gpio |= (1 << self._pin)
            else:
                gpio &= ~(1 << self._pin)
            self._mcp.gpio = gpio

        @property
        def direction(self):
            iodir = self._mcp._read_u8(_MCP23008_IODIR)
            if iodir & (1 << self._pin) > 0:
                return digitalio.Direction.INPUT
            else:
                return digitalio.Direction.OUTPUT

        @direction.setter
        def direction(self, val):
            iodir = self._mcp._read_u8(_MCP23008_IODIR)
            if val == digitalio.Direction.INPUT:
                iodir |= (1 << self._pin)
            elif val == digitalio.Direction.OUTPUT:
                iodir &= ~(1 << self._pin)
            else:
                raise ValueError('Expected INPUT or OUTPUT direction!')
            self._mcp._write_u8(_MCP23008_IODIR, iodir)

        @property
        def pull(self):
            gppu = self._mcp._read_u8(_MCP23008_GPPU)
            if gppu & (1 << self._pin) > 0:
                return digitalio.Pull.UP
            else:
                return None

        @pull.setter
        def pull(self, val):
            gppu = self._mcp._read_u8(_MCP23008_GPPU)
            if val is None:
                gppu &= ~(1 << self._pin)  # Disable pull-up
            elif val == digitalio.Pull.UP:
                gppu |= (1 << self._pin)
            elif val == digitalio.Pull.DOWN:
                raise ValueError('Pull-down resistors are not supported!')
            else:
                raise ValueError('Expected UP, DOWN, or None for pull state!')
            self._mcp._write_u8(_MCP23008_GPPU, gppu)

    def __init__(self, i2c, address=_MCP23008_ADDRESS):
        """Initialize MCP23008 instance on specified I2C bus and optionally
        at the specified I2C address.
        """
        self._device = i2c_device.I2CDevice(i2c, address)
        # Reset device state to all pins as inputs (safest option).
        with self._device as device:
            # Write to MCP23008_IODIR register 0xFF followed by 9 zeros
            # for defaults of other registers.
            device.write('\x00\xFF\x00\x00\x00\x00\x00\x00\x00\x00\x00')

    def _read_u8(self, register):
        # Read an unsigned 8 bit value from the specified 8-bit register.
        with self._device as i2c:
            self._BUFFER[0] = register & 0xFF
            i2c.write(self._BUFFER, end=1, stop=False)
            i2c.readinto(self._BUFFER, end=1)
            return self._BUFFER[0]

    def _write_u8(self, register, val):
        # Write an 8 bit value to the specified 8-bit register.
        with self._device as i2c:
            self._BUFFER[0] = register & 0xFF
            self._BUFFER[1] = val & 0xFF
            i2c.write(self._BUFFER)

    @property
    def gpio(self):
        """Get and set the raw GPIO output register.  Each bit represents the
        output value of the associated pin (0 = low, 1 = high), assuming that
        pin has been configured as an output previously.
        """
        return self._read_u8(_MCP23008_GPIO)

    @gpio.setter
    def gpio(self, val):
        self._write_u8(_MCP23008_GPIO, val)
