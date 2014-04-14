#!/usr/bin/env python
import pygtk
import gtk
import gobject
import dbus
import dbus.mainloop.glib
from dbushelpers.call_cached import call_cached


class example_program:
    def __init__(self, bus):
        # Boilerplate
        self.mainwindow = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.mainwindow.set_title('PyGTK Example')
        self.mainwindow.connect("delete_event", self.quit)
        self.mainwindow.connect("destroy", self.quit)

        # Connect to DBus signals
        self.bus = bus
        self.bus.add_signal_receiver(self.alias_changed, dbus_interface = "fi.hacklab.ardubus", signal_name = "alias_change")

        # Divive window to left and right halves which are vboxes        
        hbox = gtk.HBox(homogeneous=True)
        self.main_left_column = gtk.VBox()
        hbox.add(self.main_left_column)
        self.main_right_column = gtk.VBox()
        hbox.add(self.main_right_column)
        self.mainwindow.add(hbox)
        
        self.led_pwm = gtk.Adjustment(value=0, lower=0, upper=255, step_incr=1, page_incr=0, page_size=0)
        self.led_pwm_slider = gtk.HScale(adjustment=self.led_pwm)
        self.main_right_column.add(self.led_pwm_slider)


    def alias_changed(self, alias, value, sender):
        # TODO: display state
        pass


    def led_slider_changed(self, *args):
        # TODO: read the value and set led PWM
        pass
        value = 0
        call_cached('/fi/hacklab/ardubus/gtk_example_board', 'set_alias', value)


    def quit(self, widget, data=None):
        gtk.main_quit()


    def mainloop(self):
         self.mainwindow.show_all()
         gtk.main()



if __name__ == '__main__':
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SessionBus()
    w = example_program(bus)
    w.mainloop()

