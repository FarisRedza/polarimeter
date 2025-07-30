import socket
import threading
import struct
import enum

from . import thorlabs_polarimeter

class Command(enum.IntEnum):
    LIST_DEVICES = 1
    DEVICE_INFO = 2
    SET_WAVELENGTH = 3
    SET_WAVEPLATE_ROTATION = 4
    MEASURE = 5

class Response(enum.IntEnum):
    ERROR = 0
    LIST_DEVICES = 1
    DEVICE_INFO = 2
    STATUS = 3
    RAWDATA = 4

def recvall(size: int, sock: socket.socket) -> bytes:
    data = bytearray()
    while len(data) < size:
        part = sock.recv(size - len(data))
        if not part:
            raise ConnectionError('Socket closed')
        data.extend(part)
    return data

def receive_command(
        sock: socket.socket
) -> tuple[Command, list]:
    header = recvall(size=8, sock=sock)
    command_id, num_args = struct.unpack('II', header)

    try:
        command = Command(command_id)
    except ValueError:
        raise ValueError(f'Invalid command ID: {command_id}')

    args = []    
    for _ in range(num_args):
        arg_len = struct.unpack('I', recvall(size=4, sock=sock))[0]
        arg = recvall(size=arg_len, sock=sock)
        args.append(arg.decode(encoding='utf-8'))

    return command, args

def send_message(
        sock: socket.socket,
        message: str,
        response_id: Response
) -> None:
    payload = struct.pack(
        f'I{len(message)}s',
        len(message),
        message.encode(encoding='utf-8')
    )
    header = struct.pack(
        'IB',
        len(payload) + 1,
        response_id
    )
    sock.sendall(header + payload)

def send_payload(
        sock: socket.socket,
        payload: bytes,
        response_id: Response
) -> None:
    header = struct.pack('IB', len(payload) +1, response_id)
    sock.sendall(header + payload)

def handle_client(
        sock: socket.socket,
        address
) -> None:
    with sock:
        try:
            while True:
                try:
                    command, args = receive_command(sock=sock)
                except (ValueError, ConnectionError) as e:
                    print(f'[{address}] Disconnected: {e}')
                    break

                if command == Command.LIST_DEVICES:
                    dev_infos = [dev.device_info.serialise() for dev in devices]
                    payload = struct.pack('I', len(dev_infos))

                    for info in dev_infos:
                        payload += struct.pack('I', len(info)) + info

                    send_payload(
                        sock=sock,
                        payload=payload,
                        response_id=Response.LIST_DEVICES
                    )
                
                elif args:
                    serial_number = str(args[0])
                    device = next(
                        (d for d in devices if d.device_info.serial_number == serial_number),
                        None
                    )
                    if not device:
                        send_message(
                            sock=sock,
                            message=f'Device {serial_number} not found',
                            response_id=Response.ERROR
                        )
                        continue

                    match command:
                        case Command.DEVICE_INFO:
                            send_payload(
                                sock=sock,
                                payload=device.device_info.serialise(),
                                response_id=Response.DEVICE_INFO
                            )

                        case Command.SET_WAVELENGTH:
                            if len(args) < 2:
                                send_message(
                                    sock=sock,
                                    message='No wavelength provided',
                                    response_id=Response.ERROR
                                )
                                continue
                            try:
                                wavelength = thorlabs_polarimeter.Metres(args[1])
                                device.set_wavelength(wavelength=wavelength)
                                send_message(
                                    sock=sock,
                                    message=f'Device {serial_number} wavelength set to {wavelength}',
                                    response_id=Response.STATUS
                                )
                                print(wavelength)
                            except Exception as e:
                                send_message(
                                    sock=sock,
                                    message=str(e),
                                    response_id=Response.ERROR
                                )

                        case Command.SET_WAVEPLATE_ROTATION:
                            if len(args) < 2:
                                send_message(
                                    sock=sock,
                                    message='No value for waveplate rotation provided',
                                    response_id=Response.ERROR
                                )
                                continue
                            try:
                                waveplate_rotation = thorlabs_polarimeter.Polarimeter.WaveplateRotation(args[1])
                                device._input_rotation_state(state=waveplate_rotation.value)
                                send_message(
                                    sock=sock,
                                    message=f'Device {serial_number} waveplate rotation {waveplate_rotation.name}',
                                    response_id=Response.STATUS
                                )
                            except Exception as e:
                                send_message(
                                    sock=sock,
                                    message=str(e),
                                    response_id=Response.ERROR
                                )

                        case Command.MEASURE:
                            send_payload(
                                sock=sock,
                                payload=device.measure().serialise(),
                                response_id=Response.RAWDATA
                            )

                        case _:
                            send_message(
                                sock=sock,
                                message=f'Unsupported command: {command}',
                                response_id=Response.ERROR
                            )
                    
                else:
                    send_message(
                        sock=sock,
                        message=f'No arguments provided',
                        response_id=Response.ERROR    
                    )

        except Exception as e:
            print(f'[{address}] Unexpected error: {e}')
        finally:
            print(f'Disconnected from {address}')

def start_server(
        host: str = '0.0.0.0',
        port: int = 5001
) -> None:
    sock = socket.socket(
        family=socket.AF_INET,
        type=socket.SOCK_STREAM
    )
    sock.bind((host, port))
    sock.listen()
    print(f'Measurement server listening on {host}:{port}')
    try:
        while True:
            conn, addr = sock.accept()
            threading.Thread(
                target=handle_client,
                args=(conn, addr),
                daemon=True
            ).start()

    except KeyboardInterrupt:
        print('Measurement server shutting down')
    finally:
        sock.close()
        for dev in devices:
            dev.disconnect()

if __name__ == '__main__':
    devices = [
        d for d in thorlabs_polarimeter.list_devices()
        if isinstance(d,thorlabs_polarimeter.Polarimeter)
    ]
    start_server()