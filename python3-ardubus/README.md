# arDuBUS python3

Rewriting in progress. In fact we might throw away DBUS support,
there are better ways these days.

## ardubus_core

Core libs for handling the serial coms with the Arduino that deals with the
real world. Also handles `devices.yml` loading/normalizing.

### Testing in interactive session

    # Imports, get asyncio eventloop
    import asyncio
    loop = asyncio.get_event_loop()
    from ardubus_core import deviceconfig, transport, init_logging
    from ardubus_core.aiowrapper import AIOWrapper

    # Setup logging 20=info
    init_logging(20)
    # Load & normalize configs
    deviceconfig.load_devices_yml('../python/devices.yml.example')
    # shorthards, we're using the "rod_control_panel" for testing
    panelcfg = deviceconfig.FULL_CONFIG_MAP['rod_control_panel']
    aliases = deviceconfig.ALIAS_MAP['rod_control_panel']

    # Dummy callback handler
    def throw_away(*args, **kwargs):
        return

    # Init the transport
    tr = transport.get('/dev/tty.usbserial-A600clwx', deviceconfig.FULL_CONFIG_MAP['rod_control_panel'])
    # Ignore events for now, comment out to see the warnings for missing callback
    tr.events_callback = throw_away

    # Normal asyncio stuff
    loop.run_until_complete(panelcfg['pca9635RGBJBOL_maps'][1][0]['PROXY'].set_value(255))
    loop.run_until_complete(panelcfg['aircore_correction_values'][0][3]['PROXY'].set_value(0))
    loop.run_until_complete(aliases['alias_gauge']['PROXY'].set_value(10))

    # Wrapper so things look like traditional blocking calls
    g1 = AIOWrapper(aliases['alias_gauge']['PROXY'])
    g1.set_value(20)

    # Tell the transport to quit before exiting to be nice
    loop.run_until_complete(tr.quit())
