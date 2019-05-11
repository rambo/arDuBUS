"""Errors"""


class TransportError(IOError):
    """Baseclass for transport level errors"""


class InvalidPacketError(TransportError):
    """Packet is not valid (has forbidden values)"""


class NACKError(TransportError):
    """Command NACKed"""


class PanicError(TransportError):
    """Transport panicked"""
