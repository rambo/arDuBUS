"""Naive homemade "eventloop" """
import logging
import sys
import time

import ardubus_core
import ardubus_core.deviceconfig
import ardubus_core.transport
from ardubus_core.aiowrapper import AIOWrapper

# Constants
TICK_INTERVAL = 0.1  # seconds
GAUGE_TICK_MOVE = 5  # units
GAUGE_VALUE_LIMITS = (0, 200)  # units, the circle has 255 positions

# Global state, not very elegant
GAUGE_VALUES = {}
GAUGE_DIRECTIONS = {}
KEEP_RUNNING = True

# Logging
LOGGER = logging.getLogger(__name__)


def event_callback(event):
    """Handle trigger event"""
    global GAUGE_DIRECTIONS  # pylint: disable=W0603
    # rod_x_y_(down/up) signals, pin signaling is active-low so we invert the signal
    if event.alias.startswith('rod_'):
        GAUGE_DIRECTIONS[event.alias] = not event.state


def mainloop(serialpath, configfile, loglevel, device_name='rod_control_panel'):
    """Init connection, apply gauge values based on the button states"""
    global GAUGE_VALUES, GAUGE_DIRECTIONS, KEEP_RUNNING  # pylint: disable=W0603
    # Init logging with sane defaults
    ardubus_core.init_logging(loglevel)
    # Load the configfile
    ardubus_core.deviceconfig.load_devices_yml(configfile)
    local_aliases = ardubus_core.deviceconfig.ALIAS_MAP[device_name]
    # Init transport and wrap for blocking access
    transport_aio = ardubus_core.transport.get(serialpath, ardubus_core.deviceconfig.FULL_CONFIG_MAP[device_name])
    transport = AIOWrapper(transport_aio)
    # Set the event callback
    transport.events_callback = event_callback

    # Get the rod signal aliases and use them to populate the state dicts
    for alias in local_aliases:
        if alias.startswith('rod_') and alias.endswith('_down'):
            gauge_key = alias.replace('_down', '') + '_gauge'
            upalias = alias.replace('_down', '_up')
            GAUGE_DIRECTIONS[alias] = False
            GAUGE_DIRECTIONS[upalias] = False
            GAUGE_VALUES[gauge_key] = GAUGE_VALUE_LIMITS[0]

            # Create wrapped proxy object for traditional blocking access
            if gauge_key in local_aliases:
                local_aliases[gauge_key]['BPROXY'] = AIOWrapper(local_aliases[gauge_key]['PROXY'])

    # Start the "eventloop"
    next_tick = time.time()
    KEEP_RUNNING = True
    try:
        while KEEP_RUNNING:
            # Wait for next tick, yield CPU with sleep(0) without hurting responsiveness
            if time.time() < next_tick:
                time.sleep(0)
                continue
            # Set next tick time
            next_tick = time.time() + TICK_INTERVAL

            # Check the directions, apply accordingly
            for gauge_key in GAUGE_VALUES:
                up_alias = gauge_key.replace('_gauge', '_up')
                dn_alias = gauge_key.replace('_gauge', '_down')

                # Apply changes if the signals are set
                if GAUGE_DIRECTIONS[dn_alias]:
                    GAUGE_VALUES[gauge_key] -= GAUGE_TICK_MOVE
                if GAUGE_DIRECTIONS[up_alias]:
                    GAUGE_VALUES[gauge_key] += GAUGE_TICK_MOVE
                if GAUGE_DIRECTIONS[dn_alias] and GAUGE_DIRECTIONS[up_alias]:
                    LOGGER.error('Gauge {} has both up and down signals set, this should not happen'.format(gauge_key))

                # Limit the values
                if GAUGE_VALUES[gauge_key] < GAUGE_VALUE_LIMITS[0]:
                    LOGGER.info('Gauge {} value limited to {}'.format(gauge_key, GAUGE_VALUE_LIMITS[0]))
                    GAUGE_VALUES[gauge_key] = GAUGE_VALUE_LIMITS[0]
                if GAUGE_VALUES[gauge_key] > GAUGE_VALUE_LIMITS[1]:
                    LOGGER.info('Gauge {} value limited to {}'.format(gauge_key, GAUGE_VALUE_LIMITS[1]))
                    GAUGE_VALUES[gauge_key] = GAUGE_VALUE_LIMITS[1]

                # And send the value to the HW
                local_aliases[gauge_key]['BPROXY'].set_value(GAUGE_VALUES[gauge_key])

    except KeyboardInterrupt:
        LOGGER.info('KeyboardInterrupt, shutting down')
        KEEP_RUNNING = False

    # close the transport cleanly (using the wrapped object for traditional blocking access)
    transport.quit()

    # Normal exit
    return 0


def usage():
    """Show usage"""
    print("""Usage:

    python3 naive.py /dev/ttyUSB0 /path/to/devices.yml
""")


if __name__ == '__main__':
    if len(sys.argv) < 3:
        usage()
        sys.exit(1)
    SERIALPATH = sys.argv[1]
    CONFIGPATH = sys.argv[2]
    LOGLEVEL = 20
    if len(sys.argv) > 4:
        LOGLEVEL = int(sys.argv[3])
    sys.exit(mainloop(SERIALPATH, CONFIGPATH, LOGLEVEL))
