import socket
import struct

from . import thorlabs_polarimeter
from . import remote_protocol

def send_command(
        sock: socket.socket,
        command: remote_protocol.Command,
        args : tuple | None = None
) -> None:
    encoded_args = [
        str(arg).encode(encoding='utf-8') for arg in args
    ] if args else []
    payload = struct.pack('II', command, len(encoded_args))

    for arg in encoded_args:
        payload += struct.pack('I', len(arg)) + arg

    sock.sendall(payload)

def recvall(size: int, sock: socket.socket) -> bytes:
    data = bytearray()
    while len(data) < size:
        part = sock.recv(size - len(data))
        if not part:
            raise ConnectionError('Socket closed')
        data.extend(part)
    return data

def receive_response(sock: socket.socket) -> tuple[int, bytes]:
    header = recvall(size=5, sock=sock)
    total_len, response_id = struct.unpack('IB', header)
    try:
        response = remote_protocol.Response(response_id)
    except ValueError:
        raise ValueError(f'Invalid response ID: {response_id}')
    else:
        payload = recvall(
            size=total_len - 1,
            sock=sock
        )
        return response, payload

def list_device_info(
        host: str | None = None,
        port: int | None = None,
        sock: socket.socket | None = None
) -> list[thorlabs_polarimeter.DeviceInfo]:
    if sock:
        host, port = sock.getpeername()
    elif host and port:
        sock = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM
        )
        sock.settimeout(5)
        sock.connect((host, port))
    else:
        raise ValueError('Must provide either a socket or host and port')

    send_command(
        sock=sock,
        command=remote_protocol.Command.LIST_DEVICES
    )
    response, payload = receive_response(sock=sock)
    
    device_infos = []
    if response == remote_protocol.Response.LIST_DEVICES:
        (num_devices,) = struct.unpack('I', payload[:4])
        offset = 4
        for _ in range(num_devices):
            (length,) = struct.unpack('I', payload[offset: offset + 4])
            offset += 4
            info_bytes = payload[offset:offset + length]
            offset += length
            dev_info = thorlabs_polarimeter.DeviceInfo.deserialise(
                payload=info_bytes
            )
            device_infos.append(dev_info)

    else:
        print(f'Unexpected response: {response}')

    return device_infos

class RemotePolarimeter(thorlabs_polarimeter.Polarimeter):
    def __init__(
            self,
            serial_number: str,
            host: str | None = None,
            port: int | None = None,
            sock: socket.socket | None = None
    ) -> None:
        if sock:
            self.host, self.port = sock.getpeername()
            self._sock = sock
        elif host and port:
            self.host = host
            self.port = port
            self._sock = socket.socket(
                socket.AF_INET,
                socket.SOCK_STREAM
            )
            self._sock.settimeout(5)
            self._sock.connect((self.host, self.port))
        else:
            raise NameError('Must provide either a socket or host and port')
        self._get_device_info(serial_number=serial_number)
        self._input_rotation_state(state=self.WaveplateRotation.ON.value)
    
    def disconnect(self) -> None:
        self._input_rotation_state(state=self.WaveplateRotation.OFF.value)

    def set_wavelength(self, wavelength: thorlabs_polarimeter.Metres) -> None:
        send_command(
            sock=self._sock,
            command=remote_protocol.Command.SET_WAVELENGTH,
            args=(self.device_info.serial_number, wavelength)
        )
        payload = self._handle_response(
            expected_response_id=remote_protocol.Response.STATUS
        )
        msg_len, = struct.unpack('I', payload[:4])
        status_msg = payload[4:4 + msg_len].decode(encoding='utf-8')

    def measure(self) -> thorlabs_polarimeter.RawData:
        send_command(
            sock=self._sock,
            command=remote_protocol.Command.MEASURE,
            args=(self.device_info.serial_number,)
        )
        payload = self._handle_response(
            expected_response_id=remote_protocol.Response.RAWDATA,
        )
        return thorlabs_polarimeter.RawData.deserialise(
            payload=payload
        )

    def _handle_response(
            self,
            expected_response_id: remote_protocol.Response
    ):
        response, payload = receive_response(self._sock)

        match response:
            case r if r == expected_response_id:
                return payload
            
            case remote_protocol.Response.ERROR:
                error_msg = payload.decode(encoding='utf-8')
                raise RuntimeError(f'Server error: {error_msg}')
            
            case _:
                raise ValueError(f'Unexpected response: {response}')

    def _get_device_info(
            self,
            serial_number: str
    ) -> None:
        send_command(
            sock=self._sock,
            command=remote_protocol.Command.DEVICE_INFO,
            args=(serial_number,)
        )
        payload = self._handle_response(
            expected_response_id=remote_protocol.Response.DEVICE_INFO,
        )
        self.device_info = thorlabs_polarimeter.DeviceInfo.deserialise(
            payload=payload
        )

    def _input_rotation_state(self, state: str) -> None:
        send_command(
            sock=self._sock,
            command=remote_protocol.Command.SET_WAVEPLATE_ROTATION,
            args=(self.device_info.serial_number, state)
        )
        payload = self._handle_response(
            expected_response_id=remote_protocol.Response.STATUS
        )
        msg_len, = struct.unpack('I', payload[:4])
        status_msg = payload[4:4 + msg_len].decode(encoding='utf-8')
