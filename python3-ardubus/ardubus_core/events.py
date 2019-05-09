"""Event messages coming back from the serialport abstracted"""

# pylint: disable=R0903


class BaseEvent:
    """baseclass for events"""
    alias = None
    idx = None
    configkey = ''

    def __init__(self, device_config_map, idx, **kwargs):
        self.idx = idx
        self.__dict__.update(kwargs)
        self.alias = self.resolve_alias(device_config_map, idx, **kwargs)

    def resolve_alias(self, device_config_map, idx, **kwargs):
        """Resolve the alias from config based on the given index"""
        return None

    def __str__(self):
        return '<{}({})>'.format(self.__class__.__name__, self.__dict__)

    def __repr__(self):
        return str(self)


class Change(BaseEvent):
    """Change events"""


class Status(BaseEvent):
    """Report status"""
    reported_ms = None


class PinEvent(BaseEvent):
    """MCU digital input events"""
    pin = None
    state = False


class PinChange(PinEvent, Change):
    """MCU digital input state changes"""


class PinStatus(PinEvent, Status):
    """MCU digital input status reports"""


class AnalogPinEvent(BaseEvent):
    """MCU analog input events"""
    pin = None
    value = 0


class AnalogPinChange(AnalogPinEvent, Change):
    """MCU analog input changes"""


class AnalogPinStatus(AnalogPinEvent, Status):
    """MCU analog input status reports"""


class PCA9535PinEvent(BaseEvent):
    """PCA953 I2C digital io-expander events"""
    pin = None
    state = False


class PCA9535PinChange(PCA9535PinEvent, Change):
    """PCA953 pin change"""


class PCA9535PinStatus(PCA9535PinEvent, Status):
    """PCA953 pin status report"""
