"""Handle serial transport"""
import asyncio
import logging
import re
import time

import serial
import serial.threaded

from .errors import InvalidPacketError, NACKError, TransportError
from .events import (AnalogPinChange, AnalogPinStatus, PCA9535PinChange,
                     PCA9535PinStatus, PinChange, PinStatus)

SERIAL_WRITE_TIMEOUT = 0.5

LOGGER = logging.getLogger(__name__)
BOARD_IDENTIFY_RE = re.compile(rb'^Board: (\w+) \w+')


class BaseTransport:
    """Baseclass for tranport layers, abstracts away details, must be subclassed to implement"""
    message_callback = None
    unsolicited_message_callback = None
    lock = asyncio.Lock()

    def __str__(self):
        return '<{}({})>'.format(self.__class__.__name__, self.__dict__)

    def __repr__(self):
        return str(self)

    async def quit(self):
        """Must shutdown all background threads (if any)"""
        raise NotImplementedError()

    async def send_command(self, command):
        """Sends a complete command to the device, line termination, write timeouts etc are handled by the transport
        note: the transport probably should handle locking transparently using
        'with (await self.lock):' as context manager"""
        raise NotImplementedError()

    def message_received(self, message):
        """Passes the message to the callback expecting it, or to the unsolicited callback"""
        if self.message_callback is not None:
            self.message_callback(message)  # pylint: disable=E1102
            self.message_callback = None
            return
        # Fall-through for unsolicited messages
        if self.unsolicited_message_callback is not None:
            self.unsolicited_message_callback(message)  # pylint: disable=E1102
            return
        LOGGER.warning("Got unsolicited message but have no callback to send it to")


class SerialProtocol(serial.threaded.Packetizer):
    """Handle the serial io"""

    TERMINATOR = b'\r\n'

    def connection_made(self, transport):
        """Overridden to make sure we have write_timeout set"""
        super().connection_made(transport)
        # Make sure we have a write timeout of expected size
        self.transport.write_timeout = SERIAL_WRITE_TIMEOUT

    def handle_packet(self, packet):
        raise TransportError("This should have been overloaded by SerialTransport")

    def write_packet(self, packet):
        """Sanity-check and write the packet"""
        if not isinstance(packet, bytes):
            raise InvalidPacketError('Packet has wrong type: {}'.format(type(packet)))

        if b'\r'in packet or b'\n' in packet:
            raise InvalidPacketError('Packet contains line ending characters')

        self.transport.write(packet + self.TERMINATOR)


class SerialTransport(BaseTransport):
    """Uses PySerials ReaderThread in the background to save us some pain"""
    serialhandler = None
    events_callback = None
    device_name = None

    def __init__(self, serial_device, device_config_map, *args, **kwargs):
        self.device_config_map = device_config_map
        self.update_proxy_transports(self.device_config_map)
        self.serialhandler = serial.threaded.ReaderThread(serial_device, SerialProtocol)
        self.serialhandler.start()
        self.serialhandler.protocol.handle_packet = self.message_received
        self.unsolicited_message_callback = self.parse_report
        if 'device_name' in kwargs:
            self.device_name = kwargs.pop('device_name')
        super().__init__(*args, **kwargs)

    def __str__(self):
        return '<{}(name={}, port={})>'.format(self.__class__.__name__, self.device_name,
                                               self.serialhandler.serial.port)

    def update_proxy_transports(self, config_level):
        """recursively Add transport to proxies that are missing it"""
        if isinstance(config_level, dict):
            # we have proxy, update it
            if 'PROXY' in config_level:
                if not config_level['PROXY'].transport:
                    config_level['PROXY'].transport = self
                # Update or no, we are done here
                return
            # Otherwise recurse
            for key in config_level:
                self.update_proxy_transports(config_level[key])
            return
        if isinstance(config_level, list):
            for item in config_level:
                self.update_proxy_transports(item)
            return
        # PONDER: Do we have other iterable types we need to consider ??
        return

    def parse_report(self, input_buffer):  # pylin: disable=R0911,R0912
        """Parses the unsolicited reports, sends events to callback"""
        event = None
        LOGGER.debug('got {}'.format(repr(input_buffer)))

        if not input_buffer:
            # Empty buffer, skip
            return
        if input_buffer.startswith(b'DEBUG:'):
            # It's logged above anyway
            return
        # Get the device name
        if input_buffer.startswith(b'Board: '):
            matched = BOARD_IDENTIFY_RE.findall(input_buffer)
            if not matched:
                LOGGER.warning('Could not parse device_name from {}'.format(input_buffer))
                return
            new_name = matched[0].decode('ascii')
            if self.device_name and self.device_name != new_name:
                LOGGER.warning('We had device_name "{}" but got "{}" from buffer'.format(self.device_name, new_name))
            self.device_name = new_name
            return

        if input_buffer[0:2] == b'CP':
            event = PCA9535PinChange(self.device_config_map, idx=input_buffer[2],
                                     state=bool(int(chr(input_buffer[3]))))

        if input_buffer[0:2] == b'CD':
            event = PinChange(self.device_config_map, idx=input_buffer[2],
                              state=bool(int(chr(input_buffer[3]))))

        if input_buffer[0:2] == b'CA':
            event = AnalogPinChange(self.device_config_map, idx=input_buffer[2],
                                    value=int(input_buffer[3:7], 16))

        if input_buffer[0:2] == b'RP':
            event = PCA9535PinStatus(self.device_config_map, idx=input_buffer[2],
                                     state=bool(int(chr(input_buffer[3]))), reported_ms=int(input_buffer[4:12], 16))

        if input_buffer[0:2] == b'RD':
            event = PinStatus(self.device_config_map, idx=input_buffer[2],
                              state=bool(int(chr(input_buffer[3]))), reported_ms=int(input_buffer[4:12], 16))

        if input_buffer[0:2] == b'RA':
            event = AnalogPinStatus(self.device_config_map, idx=input_buffer[2],
                                    value=int(input_buffer[3:7], 16), reported_ms=int(input_buffer[6:15], 16))

        if event is None:
            LOGGER.error('Could not parse packet: {}'.format(repr(input_buffer)))
            return
        if self.events_callback is None:
            LOGGER.warning('Got event {} but no callback'.format(event))
            return
        self.events_callback(event)  # pylint: disable=E1102
        return

    async def send_command(self, command):
        """Wrapper for write_line on the protocol with some sanity checks"""
        if not self.serialhandler or not self.serialhandler.is_alive():
            raise TransportError('Serial handler not ready')
        with await self.lock:
            self.serialhandler.protocol.write_packet(command)
            response = None

            def set_response(message):
                """Callback for setting the response"""
                nonlocal response
                response = message
            self.message_callback = set_response
            while response is None:
                await asyncio.sleep(0)
            # Parse response
            if response == b'\x15':
                raise NACKError('Got explicit NACK, command was {}'.format(repr(command)))
            if not response.endswith(b'\x06'):
                raise NACKError('Did not get ACK, command was {}'.format(repr(command)))

    async def quit(self):
        """Closes the port and background threads"""
        self.serialhandler.close()


def get(serial_url, device_config_map, **serial_kwargs):
    """Shorthand for creating the port from url and initializing the transport"""
    if 'baudrate' not in serial_kwargs:
        serial_kwargs['baudrate'] = 115200
    port = serial.serial_for_url(serial_url, **serial_kwargs)
    port.setDTR(False)  # Reset the arduino by driving DTR for a moment (RS323 signals are active-low)
    time.sleep(0.050)
    port.setDTR(True)
    return SerialTransport(port, device_config_map)
