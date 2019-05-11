"""Proxy objects for sending commands to transports"""
import logging

# We need to offset the pin numbers to CR and LF which are control characters to us
# NOTE: this *must* be same as in ardubus.h
# TODO: Use hex encoded values everywhere to avoid this
IDX_OFFSET = 32
LOGGER = logging.getLogger(__name__)


def idx2byte(idx):
    """Offset the idx number and return the bytes object"""
    return bytes([idx + IDX_OFFSET])


def value2safebyte(value):
    """Take boolean or integer value, convert to byte making sure it's not too large or reserved control char"""
    if isinstance(value, bool):
        if value:
            return b'1'
        return b'0'
    if not isinstance(value, int):
        raise RuntimeError('Input must be int or bool')
    if value > 255:
        raise RuntimeError('Input is too large')
    if value in [13, 10]:
        value += 1
    return bytes([value])


class BaseProxy:
    """Baseclass for the object proxies"""
    alias = None
    transport = None

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __str__(self):
        return '<{}({})>'.format(self.__class__.__name__, self.__dict__)

    def __repr__(self):
        return str(self)

    async def set_value(self, value):
        """In most cases simple value is enough, needs transport set"""
        if not self.transport:
            raise RuntimeError('Transport must be set to use this method')
        return await self.transport.send_command(self.encode_value(value))

    def encode_value(self, value):
        """In most cases simple value is enough, returns the encoded command for transport"""
        raise NotImplementedError('Must be overridden')


class SimpleProxy(BaseProxy):
    """For very simple cases"""
    idx = 0
    _command_char = None

    def encode_value(self, value):
        if self._command_char is None:
            raise RuntimeError('command_char must be defines')
        return self._command_char + idx2byte(self.idx) + value2safebyte(value)


class PWMProxy(SimpleProxy):
    """MCU PWM output pins"""
    _command_char = b'P'


class PinProxy(SimpleProxy):
    """For digital output pins without PWM"""
    _command_char = b'D'


class AirCoreProxy(BaseProxy):
    """AirCore motor proxy"""
    board_idx = 0
    motorno = 0
    value_correction = 0

    def encode_value(self, value):
        """the value is the aircore position"""
        value = (value + self.value_correction) % 255
        return b'A' + idx2byte(self.board_idx) + idx2byte(self.motorno) + value2safebyte(value)


class JBOLLedProxy(BaseProxy):
    """Proxy for LEDs controlled with JBOL boards"""
    board_idx = 0
    ledno = 0

    def encode_value(self, value):
        """the value is the LED PWM"""
        return b'J' + idx2byte(self.board_idx) + idx2byte(self.ledno) + value2safebyte(value)


class SPI595Proxy(BaseProxy):
    """595 Shift registers"""
    idx = 0

    def encode_value(self, value):
        """the value is the aircore position"""
        return b'W' + idx2byte(self.idx) + (b'%0.2X' % value)

    def get_bitproxy(self, bit_idx):
        """Get a proxy object for given bit on this register"""
        return SPI595BitProxy(idx=8 * self.idx + bit_idx, transport=self.transport)

    async def set_bit(self, bit_idx, value):
        """Set single bit on this board to value"""
        if not self.transport:
            raise RuntimeError('Transport must be set to use this method')
        return await self.transport.send_command(self.encode_bit(bit_idx, value))

    def encode_bit(self, bit_idx, value):
        """encoding method for set_bit"""
        bitproxy = self.get_bitproxy(bit_idx)
        return bitproxy.encode_value(value)


class SPI595BitProxy(SimpleProxy):
    """Single bit access to the shift registers"""
    _command_char = b'B'


class PCA9535PinProxy(SimpleProxy):
    """Single pin=bit access to the IO expander"""
    _command_char = b'E'


class I2CASCIIProxy(BaseProxy):
    """I2C ASCII 7-segment display boards"""
    board_idx = 0
    max_chars = None

    def encode_value(self, value):
        """The value must be bytes or string (which will be encoded to ASCII)"""
        if isinstance(value, str):
            value = value.encode('ascii')
        if not isinstance(value, bytes):
            raise RuntimeError('Input must be bytes or str')
        if self.max_chars is not None:
            if len(value) > self.max_chars:
                LOGGER.warning('Input is longer than {}, truncating'.format(self.max_chars))
                value = value[0:self.max_chars]
        return b'w' + idx2byte(self.board_idx) + value


class ServoProxy(BaseProxy):
    """For servo control"""
    idx = 0

    def encode_value(self, value):
        """Values over 255 are considered usec, lower are considered degrees, max degrees is 180"""
        if not isinstance(value, int):
            raise RuntimeError('Values must be integers')
        if value < 0:
            raise RuntimeError('Values must be positive')
        # usec
        if value > 255:
            return b's' + idx2byte(self.idx) + (b'%0.4X' % value)
        # degrees
        if value > 180:
            LOGGER.warning('Degrees value is over 180, limiting')
            value = 180
        return b'S' + idx2byte(self.idx) + value2safebyte(value)
