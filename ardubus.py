#!/usr/bin/env python

import os
import gobject
import dbus
import dbus.service
import dbus.mainloop.glib


class ardubus(dbus.service.Object):
    def __init__(self, bus, object_name):
        self.object_name = object_name
        self.object_path = '/fi/hacklab/ardubus/' + object_name
        self.bus_name = dbus.service.BusName('fi.hacklab.ardubus', bus=bus)
        dbus.service.Object.__init__(self, self.bus_name, self.object_path)

    @dbus.service.method('fi.hacklab.ardubus')
    def hello(self):
        return "Hello,World! My name is " + self.object_name



if __name__ == '__main__':
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    import ConfigParser
    config = ConfigParser.SafeConfigParser()
    if not os.path.isfile('ardubus.conf'):
        config.add_section('arduino0')
        config.set('arduino0', 'device', '/dev/ttyUSB0')
        # TODO: Other defaults
        with open('ardubus.conf', 'wb') as configfile:
            config.write(configfile)
    config.read('ardubus.conf')

    bus = dbus.SessionBus()

    service_objects = {}
    for board_name in config.sections():
        service_objects[board_name] = ardubus(bus, board_name)

    loop = gobject.MainLoop()
    loop.run()