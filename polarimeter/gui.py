import sys
import os
import signal

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw

from . import gui_widget
from . import thorlabs_polarimeter

class MainWindow(Adw.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_title(title='Polarisation Viewer')
        self.set_default_size(width=600, height=500)
        self.set_size_request(width=450, height=150)
        self.connect('close-request', self.on_close_request)

        # main box
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(content=self.main_box)

        ## header_bar
        try:
            header_bar = Gtk.HeaderBar(
                use_native_controls=True
            )
        except:
            header_bar = Gtk.HeaderBar()

        self.main_box.append(child=header_bar)

        ### polarimeter box
        try:
            self.polarimeter_box = gui_widget.PolarimeterBox(
                polarimeter=thorlabs_polarimeter.Polarimeter(
                    serial_number='M00910360'
                )
            )
        except:
            self.main_box.append(
                child=Gtk.Label(
                    label='No polarimeter found',
                    valign=Gtk.Align.CENTER,
                    vexpand=True
                )
            )
        else:
            self.main_box.append(child=self.polarimeter_box)

    def on_close_request(self, window: Adw.ApplicationWindow) -> bool:
        os.kill(os.getpid(), signal.SIGINT)
        return False

class App(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connect('activate', self.on_activate)

    def on_activate(self, app: Adw.Application):
        self.win = MainWindow(application=app)
        self.win.present()

if __name__ == '__main__':
    app = App(application_id='com.github.FarisRedza.PolarisationViewer')
    try:
        app.run(sys.argv)
    except Exception as e:
        print('App crashed with an exception:', e)
    except KeyboardInterrupt:
        app.win.polarimeter_box._event.set()
        app.win.polarimeter_box._measurement_thread.join()
        app.win.polarimeter_box.polarimeter.disconnect()