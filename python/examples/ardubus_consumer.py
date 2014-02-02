#!/usr/bin/env python
import dbus,time
from dbushelpers.call_cached import call_cached
 
bus = dbus.SessionBus()
launcher = bus.get_object('fi.hacklab.ardubus.launcher', '/fi/hacklab/ardubus/launcher')

for board in launcher.list_boards():
    print "try b = get_board('%s') and then b.method(*args)" % board


def get_board(bname):
    print "try also call_cached('/fi/hacklab/ardubus/%s', 'method', *args)"  % bname
    return bus.get_object("fi.hacklab.ardubus.%s" % bname, "/fi/hacklab/ardubus/%s" % bname)
    

#b = get_board('rod_control_panel')
#l = get_board('reactor_lid')
