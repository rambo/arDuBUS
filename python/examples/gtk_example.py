#!/usr/bin/env python
import pygtk
import gtk
import gobject
import dbus
import dbus.mainloop.glib
dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
from dbushelpers.call_cached import call_cached


class example_program:
    def __init__(self, bus):
        # Boilerplate
        self.mainwindow = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.mainwindow.resize(300,200)
        self.mainwindow.set_title('PyGTK Example')
        self.mainwindow.connect("delete_event", self.quit)
        self.mainwindow.connect("destroy", self.quit)

        # Connect to DBus signals
        self.bus = bus
        self.bus.add_signal_receiver(self.alias_changed, dbus_interface = "fi.hacklab.ardubus", signal_name = "alias_change")

        # Divide widow to top & bottom halves
        vbox = gtk.VBox(homogeneous=False)
        self.top_half = gtk.HBox()
        vbox.pack_start(self.top_half, fill=False, expand=False)
        self.bottom_half = gtk.HBox()
        vbox.pack_start(self.bottom_half, fill=False, expand=False)
        self.mainwindow.add(vbox)

        self.led_pwm = gtk.Adjustment(value=0, lower=0, upper=255, step_incr=1.0)
        self.led_pwm.connect("value_changed", self.led_pwm_changed)
        self.led_pwm_slider = gtk.HScale(adjustment=self.led_pwm)
        self.led_pwm_slider.set_digits(0)
        self.top_half.pack_start(gtk.Label("LED brightness"), fill=False, expand=False)
        self.top_half.pack_start(self.led_pwm_slider, fill=True, expand=True)


    def alias_changed(self, alias, value, sender):
        # TODO: display state
        pass


    def led_pwm_changed(self, *args):
        value = self.led_pwm.get_value()
        try:
            call_cached('/fi/hacklab/ardubus/gtk_example_board', 'set_alias', value)
        except dbus.exceptions.DBusException,e:
            # No arduino
            print "Could not set value %d via arDuBUS" % value


    def quit(self, widget, data=None):
        gtk.main_quit()


    def mainloop(self):
         self.mainwindow.show_all()
         gtk.main()



if __name__ == '__main__':
    bus = dbus.SessionBus()
    w = example_program(bus)
    w.mainloop()

