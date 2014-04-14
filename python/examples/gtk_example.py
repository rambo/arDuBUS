#!/usr/bin/env python
import pygtk
import gtk
import gobject

class mainwindow:
    def __init__(self):
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_title('PyGTK Example')
        self.window.connect("delete_event", self.quit)
        self.window.connect("destroy", self.quit)

    def quit(self, widget, data=None):
        gtk.main_quit()

    def mainloop(self):
         self.window.show_all()
         gtk.main()


if __name__ == '__main__':
    w = mainwindow()
    w.mainloop()

