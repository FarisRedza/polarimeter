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

        self.main_stack = Gtk.Stack(
            transition_type=Gtk.StackTransitionType.CROSSFADE
        )
        self.main_box.append(child=self.main_stack)

        devices = [
            d for d in thorlabs_polarimeter.list_devices()
            if isinstance(d,thorlabs_polarimeter.Polarimeter)
        ]
        if len(devices) == 0:
            self.main_box.append(
                child=Gtk.Label(
                    label='No devices found',
                    valign=Gtk.Align.CENTER,
                    vexpand=True
                )
            )
        else:
            ### polarimeter
            add_device_page = Adw.PreferencesPage()
            self.main_stack.add_titled(
                child=add_device_page,
                name='add device',
                title='add device'
            )
            add_device_group = Adw.PreferencesGroup(title='Devices')
            add_device_page.add(group=add_device_group)
            for d in devices:
                add_device_row = Adw.ActionRow(
                    title=d.device_info.manufacturer,
                    subtitle=d.device_info.serial_number
                )
                add_device_group.add(child=add_device_row)
                connect_device_button = Gtk.Button(
                    label='Connect',
                    valign=Gtk.Align.CENTER
                )
                connect_device_button.connect(
                    'clicked',
                    lambda widget,
                    device=d: self.on_add_device(
                        widget,
                        device
                    )
                )
                add_device_row.add_suffix(widget=connect_device_button)

    def on_add_device(
            self,
            button: Gtk.Button,
            device: thorlabs_polarimeter.Polarimeter
    ) -> None:
        device._input_rotation_state(
            state=thorlabs_polarimeter.Polarimeter.WaveplateRotation.ON.value
        )
        self.device_control_box = gui_widget.PolarimeterBox(
            polarimeter=device
        )
        self.main_stack.add_titled(
            child=self.device_control_box,
            name='Device',
            title='Device'
        )
        self.main_stack.set_visible_child(
            child=self.device_control_box
        )

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
        if hasattr(app.win, 'device_control_box'):
            app.win.device_control_box._event.set()
            app.win.device_control_box._measurement_thread.join()
            app.win.device_control_box.polarimeter.disconnect()