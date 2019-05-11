"""Normalize device configs, this module also maintains global normalized config state"""
import logging

import yaml

from .cmdproxies import (AirCoreProxy, I2CASCIIProxy, JBOLLedProxy,
                         PCA9535PinProxy, PinProxy, PWMProxy, ServoProxy)

LOGGER = logging.getLogger(__name__)
SECTION_CMDPROXY_MAP = {
    'digital_out_pins': PinProxy,
    'pca9535_outputs': PCA9535PinProxy,
    'servo_pins': ServoProxy,
    'digital_pwmout_pins': PWMProxy,
}

GENERIC_ALIAS_SUPPORTED_KEYS = (
    'digital_in_pins',
    'digital_out_pins',
    'pca9535_inputs',
    'pca9535_outputs',
    'pulse_input_pins',
    'servo_pins',
    'digital_pwmout_pins',
)


FULL_CONFIG_MAP = {}
ALIAS_MAP = {}


# pylint: disable=W0603

def load_devices_yml(filepath, device_transports=None):
    """Loads the config file, normalizes configs etc"""
    global FULL_CONFIG_MAP
    with open(filepath, 'rt') as filepointer:
        FULL_CONFIG_MAP = yaml.safe_load(filepointer)

    for devicename in FULL_CONFIG_MAP.keys():
        transport = None
        if device_transports and devicename in device_transports:
            transport = device_transports[devicename]
        normalize_device_config(devicename, transport)


def normalize_generic_aliases(devicename, transport=None):
    """Normalize all config items that have generic alias support and create command proxies for them"""
    global FULL_CONFIG_MAP, GENERIC_ALIAS_SUPPORTED_KEYS, ALIAS_MAP, SECTION_CMDPROXY_MAP
    config = FULL_CONFIG_MAP[devicename]
    for section_key in GENERIC_ALIAS_SUPPORTED_KEYS:
        if section_key not in config:
            continue
        section = config[section_key]
        item_keys = []
        if isinstance(section, list):
            item_keys = range(len(section))
        if isinstance(section, dict):
            item_keys = section.keys()
        for idx, item_key in enumerate(item_keys):
            item = section[item_key]
            if not isinstance(item, dict):
                item = {'pin': item}
                section[item_key] = item
            if 'alias' not in item:
                item['alias'] = None

            # Assign to alias map if alias is set
            if item['alias'] is not None:
                if item['alias'] in ALIAS_MAP[devicename]:
                    LOGGER.error('Duplicate alias "{}" at {}:{}:{}'.format(
                        item['alias'], devicename, section_key, item_key))
                else:
                    ALIAS_MAP[devicename][item['alias']] = FULL_CONFIG_MAP[devicename][section_key][item_key]

            # create command proxy
            if section_key in SECTION_CMDPROXY_MAP:
                klass = SECTION_CMDPROXY_MAP[section_key]
                item['PROXY'] = klass(idx=idx, transport=transport, alias=item['alias'])


def normalize_pca9635rgbjbol_boards(devicename, transport=None):  # pylint: disable=R0912
    """Normalize the led remapping with aliases and create command proxies for them"""
    global FULL_CONFIG_MAP
    config = FULL_CONFIG_MAP[devicename]
    if 'pca9635RGBJBOL_boards' not in config:
        return

    # Make sure the maps are defined for all boards
    if 'pca9635RGBJBOL_maps' not in config:
        config['pca9635RGBJBOL_maps'] = {}
    for idx, _ in enumerate(config['pca9635RGBJBOL_boards']):
        if idx not in config['pca9635RGBJBOL_maps']:
            config['pca9635RGBJBOL_maps'][idx] = {}

    for board_idx in config['pca9635RGBJBOL_maps']:
        board_map = config['pca9635RGBJBOL_maps'][board_idx]

        # Make sure all LED pins are defined
        for idx in range(3 * 16):  # 3 pcs of 16ch drivers per board
            if idx not in board_map:
                board_map[idx] = idx

        # Then normalize them
        for req_idx in board_map:
            item = board_map[req_idx]
            if not isinstance(item, dict):
                item = {'pin': item}
                board_map[req_idx] = item
            if 'alias' not in item:
                item['alias'] = None

            # Assign to alias map if alias is set
            if item['alias'] is not None:
                if item['alias'] in ALIAS_MAP[devicename]:
                    LOGGER.error('Duplicate alias "{}" at {}:pca9635RGBJBOL_maps:{}:{}'.format(
                        item['alias'], devicename, board_idx, req_idx))
                else:
                    ALIAS_MAP[devicename][item['alias']] = FULL_CONFIG_MAP[devicename]['pca9635RGBJBOL_maps'][board_idx][req_idx]  # noqa: E501 ; # pylint: disable=C0301

            # create command proxy
            item['PROXY'] = JBOLLedProxy(board_idx=board_idx, ledno=item['pin'],
                                         transport=transport, alias=item['alias'])


def normalize_i2cascii_boards(devicename, transport=None):
    """Normalize config and create command proxies for I2CASCII boards"""
    global FULL_CONFIG_MAP
    config = FULL_CONFIG_MAP[devicename]
    if 'i2cascii_boards' not in config:
        return

    for board_idx, item in enumerate(config['i2cascii_boards']):
        if not isinstance(item, dict):
            item = {'address': item}
            config[board_idx] = item
        if 'alias' not in item:
            item['alias'] = None
        if 'chars' not in item:
            item['chars'] = None

        # Assign to alias map if alias is set
        if item['alias'] is not None:
            if item['alias'] in ALIAS_MAP[devicename]:
                LOGGER.error('Duplicate alias "{}" at {}:i2cascii_boards:{}'.format(
                    item['alias'], devicename, board_idx))
            else:
                ALIAS_MAP[devicename][item['alias']] = FULL_CONFIG_MAP[devicename]['i2cascii_boards'][board_idx]  # noqa: E501 ; # pylint: disable=C0301

        # create command proxy
        item['PROXY'] = I2CASCIIProxy(board_idx=board_idx, max_chars=item['chars'],
                                      transport=transport, alias=item['alias'])


def normalize_aircore_boards(devicename, transport=None):  # pylint: disable=R0912
    """Normalize the led remapping with aliases and create command proxies for them"""
    global FULL_CONFIG_MAP
    config = FULL_CONFIG_MAP[devicename]
    if 'aircore_boards' not in config:
        return

    # Make sure the maps are defined for all boards
    if 'aircore_correction_values' not in config:
        config['aircore_correction_values'] = {}
    for idx, _ in enumerate(config['aircore_boards']):
        if idx not in config['pca9635RGBJBOL_maps']:
            config['aircore_correction_values'][idx] = {}

    for board_idx in config['aircore_correction_values']:
        board_map = config['aircore_correction_values'][board_idx]

        # Make sure all channels are defined
        for motorno in range(8):
            if motorno not in board_map:
                board_map[motorno] = 0

        # Then normalize them
        for motorno in board_map:
            item = board_map[motorno]
            if not isinstance(item, dict):
                item = {'correction': item}
                board_map[motorno] = item
            if 'alias' not in item:
                item['alias'] = None

            # Assign to alias map if alias is set
            if item['alias'] is not None:
                if item['alias'] in ALIAS_MAP[devicename]:
                    LOGGER.error('Duplicate alias "{}" at {}:aircore_correction_values:{}:{}'.format(
                        item['alias'], devicename, board_idx, motorno))
                else:
                    ALIAS_MAP[devicename][item['alias']] = FULL_CONFIG_MAP[devicename]['aircore_correction_values'][board_idx][motorno]  # noqa: E501 ; # pylint: disable=C0301

            # create command proxy
            item['PROXY'] = AirCoreProxy(board_idx=board_idx, motorno=motorno, transport=transport,
                                         alias=item['alias'], value_correction=item['correction'])


def normalize_device_config(devicename, transport=None):
    """Normalizes a device config dict, if transport is set initializes the command proxies too"""
    global FULL_CONFIG_MAP, ALIAS_MAP
    ALIAS_MAP[devicename] = {}
    normalize_generic_aliases(devicename, transport)
    normalize_pca9635rgbjbol_boards(devicename, transport)
    normalize_i2cascii_boards(devicename, transport)
    normalize_aircore_boards(devicename, transport)

    # If tranport is defined, set this config and the device_config it should use
    if transport:
        transport.device_config_map = FULL_CONFIG_MAP[devicename]
