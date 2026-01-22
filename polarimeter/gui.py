import sys
import pathlib
import os
import signal
import typing
import socket

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio

sys.path.append(str(pathlib.Path.cwd()))
from polarimeter import gui_widget
from polarimeter import thorlabs_polarimeter
from polarimeter import remote_polarimeter

class DeviceListGroup(Adw.PreferencesGroup):
    def __init__(
            self,
            title,
            devices_infos: list[thorlabs_polarimeter.DeviceInfo],
            set_device_callback: typing.Callable,
            remote: bool = False
    ) -> None:
        super().__init__(title=title)
        self.set_device_callback = set_device_callback
        self.remote = remote

        if len(devices_infos) == 0:
            no_devices_row = Adw.ActionRow(
                child=Gtk.Label(
                    label='No devices found',
                    valign=Gtk.Align.CENTER,
                    vexpand=True
                )
            )
            self.add(child=no_devices_row)

        else:
            for d in devices_infos:
                device_row = Adw.ActionRow(
                    title=d.manufacturer,
                    subtitle=f'Serial number: {d.serial_number}'
                )
                self.add(child=device_row)
                connect_device_button = Gtk.Button(
                    label='Connect',
                    icon_name='carousel-arrow-next-symbolic',
                    css_classes=['flat'],
                    valign=Gtk.Align.CENTER
                )
                connect_device_button.connect(
                    'clicked',
                    lambda button,
                    serial_number=d.serial_number: self.on_connect_device(
                        button=button,
                        serial_number=serial_number
                    )
                )
                device_row.add_suffix(widget=connect_device_button)

    def on_connect_device(self, button: Gtk.Button, serial_number: str) -> None:
        self.set_device_callback(
            serial_number=serial_number,
            remote=self.remote
        )

class RemoteConnectionGroup(Adw.PreferencesGroup):
    def __init__(
            self,
            set_host_callback: typing.Callable,
            set_port_callback: typing.Callable,
            set_sock_callback: typing.Callable,
            server_connect_callback: typing.Callable
        ) -> None:
        super().__init__(title='Remote Connection')
        self.set_host_callback = set_host_callback
        self.set_port_callback = set_port_callback
        self.set_sock_callback = set_sock_callback
        self.server_connect_callback = server_connect_callback

        # host
        self.host_row = Adw.ActionRow(title='Host')
        self.add(child=self.host_row)
        host_entry = Gtk.Entry(
            text='127.0.0.1',
            valign=Gtk.Align.CENTER
        )
        host_entry.connect(
            'activate',
            self.on_set_host
        )
        self.host_row.add_suffix(
            widget=host_entry
        )
        # port
        self.port_row = Adw.ActionRow(title='Port')
        self.add(child=self.port_row)
        port_entry = Gtk.Entry(
            text='5001',
            valign=Gtk.Align.CENTER
        )
        port_entry.connect(
            'activate',
            self.on_set_port
        )
        self.port_row.add_suffix(
            widget=port_entry
        )

        # connect
        connect_button = Gtk.Button(
            label='Connect',
            valign=Gtk.Align.CENTER
        )
        connect_button.connect(
            'clicked',
            self.on_server_connect
        )
        self.set_header_suffix(suffix=connect_button)

    def on_set_host(self, entry: Gtk.Entry) -> None:
        self.set_host_callback(host=entry.get_text())

    def on_set_port(self, entry: Gtk.Entry) -> None:
        try:    
            port = int(entry.get_text())
        except:
            print(f'Invalid entry: {entry.get_text()}')
        else:
            self.set_port_callback(port=port)

    def on_server_connect(self, button: Gtk.Button) -> None:
        self.server_connect_callback()

class MainWindow(Adw.ApplicationWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_title(title='Polarisation Viewer')
        self.set_default_size(width=600, height=500)
        self.set_size_request(width=450, height=150)
        self.connect('close-request', self.on_close_request)

        self.host = '127.0.0.1'
        self.port = 5001
        self._sock: socket.socket | None = None

        # main box
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(content=main_box)

        ## header_bar
        try:
            header_bar = Gtk.HeaderBar(
                use_native_controls=True
            )
        except:
            header_bar = Gtk.HeaderBar()
        main_box.append(child=header_bar)

        self.main_stack = Gtk.Stack(
            transition_type=Gtk.StackTransitionType.CROSSFADE
        )
        main_box.append(child=self.main_stack)

        # menu button
        menu = Gio.Menu.new()
        menu.append('Help', 'app.help')
        menu.append('About', 'app.about')
        popover = Gtk.PopoverMenu()
        popover.set_menu_model(model=menu)

        menu_button = Gtk.MenuButton(
            icon_name='open-menu-symbolic',
            popover=popover
        )
        header_bar.pack_end(child=menu_button)

        self.device_select_page = Adw.PreferencesPage()
        self.main_stack.add_child(child=self.device_select_page)
        self.main_stack.set_visible_child(child=self.device_select_page)

        local_device_infos = [
            d.device_info for d in thorlabs_polarimeter.list_devices()
            if isinstance(d,thorlabs_polarimeter.Polarimeter)
        ]
        local_device_group = DeviceListGroup(
            title='Local Devices',
            devices_infos=local_device_infos,
            set_device_callback=self.set_device
        )
        self.device_select_page.add(group=local_device_group)

        self.remote_connection_group = RemoteConnectionGroup(
            set_host_callback=self.set_host,
            set_port_callback=self.set_port,
            set_sock_callback=self.set_sock,
            server_connect_callback=self.server_connect
        )
        self.device_select_page.add(group=self.remote_connection_group)

    def server_connect(self) -> None:
        sock = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM
        )
        sock.settimeout(5)
        sock.connect((self.host, self.port))
        self._sock = sock

        remote_device_infos = remote_polarimeter.list_device_info(
            sock=self._sock
        )

        self.device_select_page.remove(group=self.remote_connection_group)
        self.device_select_page.add(
            group=DeviceListGroup(
                title='Remote Devices',
                devices_infos=remote_device_infos,
                set_device_callback=self.set_device,
                remote=True
            )
        )

    def set_device(self, serial_number: str, remote: bool = False) -> None:
        if not remote:
            self.polarimeter_box = gui_widget.PolarimeterBox(
                polarimeter=thorlabs_polarimeter.Polarimeter(
                    serial_number=serial_number
                )
            )
        else:
            self.polarimeter_box = gui_widget.PolarimeterBox(
                polarimeter=remote_polarimeter.RemotePolarimeter(
                    serial_number=serial_number,
                    sock=self._sock
                )
            )
        self.main_stack.add_child(child=self.polarimeter_box)
        self.main_stack.set_visible_child(child=self.polarimeter_box)

    def on_close_request(self, window: Adw.ApplicationWindow) -> bool:
        os.kill(os.getpid(), signal.SIGINT)
        return False
    
    def get_host(self) -> str:
        return self.host
    
    def set_host(self, host: str) -> None:
        self.host = host

    def get_port(self) -> int:
        return self.port

    def set_port(self, port: int) -> None:
        self.port = port

    def set_sock(self, sock: socket.socket) -> None:
        self._sock = sock

class App(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connect('activate', self.on_activate)

        help_action = Gio.SimpleAction.new(
            name='help',
            parameter_type=None
        )
        help_action.connect('activate', self.on_help)
        self.add_action(action=help_action)

        about_action = Gio.SimpleAction.new(
            name='about',
            parameter_type=None
        )
        about_action.connect('activate', self.on_about)
        self.add_action(action=about_action)


    def on_activate(self, app: Adw.Application):
        self.win = MainWindow(application=app)
        self.win.present()

    def on_help(self, action: Gio.SimpleAction, param: None) -> None:
        help_dialog = Gtk.MessageDialog(
            transient_for=self.get_active_window(),
            modal=True,
            visible=True,
            buttons=Gtk.ButtonsType.OK,
            text='Help',
            secondary_text='Select a polarimeter from "Local Devices" or connect to a remote polarimeter server using "Remote Connection".'
        )
        help_dialog.connect(
            'response',
            lambda dialog, response: dialog.destroy()
        )

    def on_about(self, action: Gio.SimpleAction, param: None) -> None:
        about_dialog = Gtk.AboutDialog(
            transient_for=self.get_active_window(),
            modal=True,
            visible=True,
            program_name='Polarimeter Viewer',
            version='0.1',
            logo_icon_name='display-brightness-symbolic',
            website='https://github.com/FarisRedza/polarimeter',
            website_label='GitHub',
            authors=['Faris Redza']
        )


if __name__ == '__main__':
    app = App(application_id='com.github.FarisRedza.PolarisationViewer')
    try:
        app.run(sys.argv)
    except Exception as e:
        print('App crashed with an exception:', e)
    except KeyboardInterrupt:
        if hasattr(app.win, 'polarimeter_box'):
            app.win.polarimeter_box._event.set()
            app.win.polarimeter_box._measurement_thread.join()
            app.win.polarimeter_box.polarimeter.disconnect()