import math
import dataclasses
import typing
import pprint
import enum
import struct
import time

import pyvisa

Percent = typing.NewType('Percent', float)
Degrees = typing.NewType('Degrees', float)
Radians = typing.NewType('Radians', float)
Watts = typing.NewType('Watts', float)
Metres = typing.NewType('Metres', float)
DecibelMilliwatts = typing.NewType('DecibelMilliwatts', float)

def decibel_milliwatts(power: Watts) -> DecibelMilliwatts:
    if power > 0:
        return DecibelMilliwatts(10 * math.log10(power / 1e-3))
    else:
        return DecibelMilliwatts(0.0)

@dataclasses.dataclass
class DeviceInfo:
    manufacturer: str
    model: str
    serial_number: str
    firmware_version: str

    def serialise(self) -> bytes:
        def encode_string(s: str) -> bytes:
            b = s.encode()
            return struct.pack(
                f'I{len(b)}s',
                len(b),
                b
            )

        return (
            encode_string(self.manufacturer) +
            encode_string(self.model) +
            encode_string(self.serial_number) +
            encode_string(self.firmware_version)
        )
    
    @classmethod
    def deserialise(cls, payload: bytes) -> 'DeviceInfo':
        offset = 0
        fields = []
        for _ in range(4):
            length = struct.unpack_from('I', payload, offset)[0]
            offset += 4
            value = struct.unpack_from(
                f'{length}s',
                payload,
                offset
            )[0].decode()
            offset += length
            fields.append(value)
        return DeviceInfo(*fields)

class SCPIDevice:
    def __init__(
            self,
            id: str,
            serial_number: str
    ) -> None:
        if id and serial_number:
            id_parts = id.split(':')
            # resource_name=f'USB0::{hex(int(id_parts[0]))}::{hex(int(id_parts[1]))}::{serial_number}::0::INSTR'
            resource_name=f'USB0::{id_parts[0]}::{id_parts[1]}::{serial_number}::0::INSTR'
        else:
            raise NameError('Device not found')

        self._instrument = pyvisa.ResourceManager().open_resource(
            resource_name=resource_name
        )
        self._check_connection()
        self._reset_command()

    def _check_connection(self) -> None:
        idn = self._identification_query()
        idn_parts = idn.removesuffix('\n').split(',')
        if idn:
            self.device_info = DeviceInfo(
                manufacturer=idn_parts[0],
                model=idn_parts[1],
                serial_number=idn_parts[2],
                firmware_version=idn_parts[3]
            )
            print(f'Connected to {idn}')
        else:
            self.disconnect()
            print(f'Instrument could not be identified')

    def disconnect(self) -> None:
        self._instrument.close()

    def write(self, command: str) -> None:
        self._instrument.write(command)
        
    def query(self, command: str) -> str:
        return str(self._instrument.query(command))

    def _clear_status_command(self) -> None:
        self._instrument.write('*CLS')

    def _standard_event_status_enable_command(self) -> None:
        self._instrument.write('*ESE')
        

    def _standard_event_status_enable_query(self) -> str:
        return str(self._instrument.query('*ESE?'))
    
    def _standard_event_status_register_query(self) -> str:
        return str(self._instrument.query('*ESR?'))
    
    def _identification_query(self) -> str:
        return str(self._instrument.query('*IDN?'))
    
    def _operation_complete_command(self) -> None:
        self._instrument.write('*OPC')
    
    def _operation_complete_query(self) -> str:
        return str(self._instrument.query('*OPC?'))
    
    def _reset_command(self) -> None:
        self._instrument.write('*RST')
        
    def _service_request_enable_command(self) -> None:
        self._instrument.write('*SRE')

    def _service_request_enable_query(self) -> str:
        return str(self._instrument.query('*SRE?'))
    
    def _read_status_byte_query(self) -> str:
        return str(self._instrument.query('*STB?'))
    
    def _self_test_query(self) -> str:
        return str(self._instrument.query('*TST?'))
    
    def _wait_to_continue_command(self) -> None:
        self._instrument.write('*WAI')

    # def cal(self) -> str:
    #     return str(self._instrument.query('*CAL?')

    # def ddt(self) -> str:
    #     return str(self._instrument.query('*DDT?')

    # def emc(self) -> str:
    #     return str(self._instrument.query('*EMC?')

    # def gmc(self) -> str:
    #     return str(self._instrument.query('*GMC?')

    # def ist(self) -> str:
    #     return str(self._instrument.query('*IST?')

    # def lmc(self) -> str:
    #     return str(self._instrument.query('*LMC?')

    # def lrn(self) -> str:
    #     return str(self._instrument.query('*LRN?')

    # def opt(self) -> str:
    #     return str(self._instrument.query('*OPT?')

    # def pre(self) -> str:
    #     return str(self._instrument.query('*PRE?')

    # def psc(self) -> str:
    #     return str(self._instrument.query('*PSC?')

    # def pud(self) -> str:
    #     return str(self._instrument.query('*PUD?')

    # def rdt(self) -> str:
    #     return str(self._instrument.query('*RDT?')

@dataclasses.dataclass
class RawData:
    '''
    wavelength (m)
    revs: number of measurement cycles
    timestamp: milliseconds since start?
    paxOpMode: operation mode of the polarimeter
    paxFlags: status and error flags
    paxTIARange: current setting of the transimpedance amplifier TIA - indicates gain level (e.g low/medium/high sensitivity)
    adcMin/Max: min and max raw ADC values across detectors - for monitor saturation or signal range
    revTime: time for one measurement cycle
    misAdj: misalignment adjustment metric/quality metric
    theta: orientation angle of the polarisation ellipse
    eta: ellipticity angle of the polarisation ellipse
    dop: degree of polarisation
    ptotal: total optical power
    '''
    wavelength: str = '0'
    revs: str = '0'
    timestamp: str = '0'
    paxOpMode: str = '0'
    paxFlags: str = '0'
    paxTIARange: str = '0'
    adcMin: str = '0'
    adcMax: str = '0'
    revTime: str = '0'
    misAdj: str = '0'
    theta: str = '0'
    eta: str = '0'
    dop: str = '0'
    ptotal: str = '0'

    def serialise(self) -> bytes:
        def encode_string(s: str):
            b = s.encode()
            return struct.pack(f'I{len(b)}s', len(b), b)

        return (
            encode_string(self.wavelength) +
            encode_string(self.revs) +
            encode_string(self.timestamp) +
            encode_string(self.paxOpMode) +
            encode_string(self.paxFlags) +
            encode_string(self.paxTIARange) +
            encode_string(self.adcMin) +
            encode_string(self.adcMax) +
            encode_string(self.revTime) +
            encode_string(self.misAdj) +
            encode_string(self.theta) +
            encode_string(self.eta) +
            encode_string(self.dop) +
            encode_string(self.ptotal)
        )
    
    @classmethod
    def deserialise(cls, payload: bytes) -> 'RawData':
        offset = 0
        fields = []
        for _ in range(14):
            length = struct.unpack_from('I', payload, offset)[0]
            offset += 4
            value = struct.unpack_from(
                f'{length}s',
                payload,
                offset
            )[0].decode()
            offset += length
            fields.append(value)
        return RawData(*fields)

@dataclasses.dataclass
class Data:
    timestamp: float = 0.0
    wavelength: Metres = Metres(0.0)
    azimuth: Degrees = Degrees(0.0)
    ellipticity: Degrees = Degrees(0.0)
    degree_of_polarisation: Percent = Percent(0.0)
    degree_of_linear_polarisation: Percent = Percent(0.0)
    degree_of_circular_polarisation: Percent = Percent(0.0)
    power: DecibelMilliwatts = DecibelMilliwatts(0.0)
    power_polarised: DecibelMilliwatts = DecibelMilliwatts(0.0)
    power_unpolarised: DecibelMilliwatts = DecibelMilliwatts(0.0)
    normalised_s1: float = 0.0
    normalised_s2: float = 0.0
    normalised_s3: float = 0.0
    S0: Watts = Watts(0.0)
    S1: Watts = Watts(0.0)
    S2: Watts = Watts(0.0)
    S3: Watts = Watts(0.0)
    power_split_ratio: float = 0.0
    phase_difference: Degrees = Degrees(0.0)
    circularity: Percent = Percent(0.0)

    @classmethod
    def from_raw_data(cls, raw_data: RawData) -> 'Data':
        wavelength = Metres(float(raw_data.wavelength))
        revs = float(raw_data.revs)
        timestamp = float(raw_data.timestamp)
        paxOpMode = float(raw_data.paxOpMode)
        paxFlags = float(raw_data.paxFlags)
        paxTIARange = float(raw_data.paxTIARange)
        adcMin = float(raw_data.adcMin)
        adcMax = float(raw_data.adcMax)
        revTime = float(raw_data.revTime)
        misAdj = float(raw_data.misAdj)
        theta = float(raw_data.theta)
        eta = float(raw_data.eta)
        dop = float(raw_data.dop)
        ptotal = float(raw_data.ptotal)

        try:
            S0 = ptotal
            S1 = ptotal * math.cos(2*theta) * math.cos(2*eta)
            S2 = ptotal * math.sin(2*theta) * math.cos(2*eta)
            S3 = ptotal * math.sin(2*eta)
            return cls(
                timestamp=timestamp,
                wavelength=wavelength,
                azimuth=Degrees(math.degrees(theta)),
                ellipticity=Degrees(math.degrees(eta)),
                degree_of_polarisation=Percent(dop * 100),
                degree_of_linear_polarisation=Percent(math.sqrt(S1**2 + S2**2)/S0 * 100),
                degree_of_circular_polarisation=Percent(abs(S3)/S0 * 100),
                power=decibel_milliwatts(Watts(ptotal)),
                power_polarised=decibel_milliwatts(Watts(dop*ptotal)),
                power_unpolarised=decibel_milliwatts(Watts((1-dop)*ptotal)),
                normalised_s1=S1/S0,
                normalised_s2=S2/S0,
                normalised_s3=S3/S0,
                S0=Watts(S0),
                S1=Watts(S1),
                S2=Watts(S2),
                S3=Watts(S3),
                power_split_ratio=math.tan(eta)**2,
                phase_difference=Degrees(math.degrees(math.atan2(S3,S2))),
                circularity=Percent(abs(math.tan(eta)) * 100)
            )
        except:
            return cls()

class Polarimeter(SCPIDevice):
    class WaveplateRotation(enum.Enum):
        OFF = '0'
        ON = '1'

    class AveragingMode(enum.Enum):
        H512 = '1' # (half waveplate rotation with 512 point FFT)
        H1024 = '2'
        H2048 = '3'
        F512 = '4'
        F1024 = '5' # (one full waveplate rotation with 1024 point FFT)
        F2048 = '6'
        D512 = '7'
        D1024 = '8'
        D2048 = '9' # (two waveplate rotations with 2048 point FFT)

    class AutoRange(enum.Enum):
        OFF = '0'
        ON = '1'
        ONCE = '2'

    def __init__(
            self,
            serial_number: str,
            id: str = '4883:32817',
            waveplate_rotation: WaveplateRotation = WaveplateRotation.ON,
            averaging_mode: AveragingMode = AveragingMode.F1024
        ) -> None:
        super().__init__(
            id=id,
            serial_number=serial_number
        )
        self._input_rotation_state(state=waveplate_rotation.value)
        self._sense_calculate_mode(mode=averaging_mode.value)

    def disconnect(self) -> None:
        if self.is_connected():
            self._input_rotation_state(state=self.WaveplateRotation.OFF.value)
            super().disconnect()

    def __del__(self) -> None:
        self.disconnect()

    def is_connected(self) -> bool:
        try:
            self._identification_query()
        except:
            return False
        else:
            return True

    def measure(self) -> RawData:
        if self.is_connected():
            wavelength = self._sense_correction_wavelength_query().removesuffix('\n')
            response = self._sense_data_latest().removesuffix('\n').split(',')
            return RawData(
                wavelength=wavelength,
                revs=response[0],
                timestamp=response[1],
                paxOpMode=response[2],
                paxFlags=response[3],
                paxTIARange=response[4],
                adcMin=response[5],
                adcMax=response[6],
                revTime=response[7],
                misAdj=response[8],
                theta=response[9],
                eta=response[10],
                dop=response[11],
                ptotal=response[12]
            )
        else:
            return RawData()
    
    def set_wavelength(self, wavelength: Metres) -> None:
        self._sense_correction_wavelength(wavelength=str(wavelength))

    def _system_error_next(self) -> str:
        return str(self._instrument.query('SYST:ERR:NEXT?'))
    
    def _system_version(self) -> str:
        return str(self._instrument.query('SYST:VERS?'))
    
    def _status_operation_event(self) -> str:
        return str(self._instrument.query('STAT:OPER:EVEN?'))
    
    def _status_operation_condition(self) -> str:
        return str(self._instrument.query('STAT:OPER:COND?'))
    
    def _status_operation_enable_query(self) -> str:
        return str(self._instrument.query('STAT:OPER:ENAB?'))
    
    def _status_questionable_event(self) -> str:
        return str(self._instrument.query('STAT:QUES:EVEN?'))
    
    def _status_questionable_condition(self) -> str:
        return str(self._instrument.query('STAT:QUES:COND?'))
    
    def _status_questionable_enable_query(self) -> str:
        return str(self._instrument.query('STAT:QUES:ENAB?'))
    
    def _status_auxiliary_event(self) -> str:
        return str(self._instrument.query('STAT:AUX:EVEN?'))
    
    def _status_auxiliary_condition(self) -> str:
        return str(self._instrument.query('STAT:AUX:CON?'))
    
    def _status_auxiliary_enable_query(self) -> str:
        return str(self._instrument.query('STAT:AUX:ENAB?'))

    def _sense_calculate_mode(self, mode: str) -> None:
        self._instrument.write(f'SENS:CALC:MOD {mode}')

    def _sense_calculate_mode_query(self) -> str:
        return str(self._instrument.query('SENS:CALC:MOD?'))
    
    def _sense_correction_wavelength(self, wavelength: str) -> None:
        self._instrument.write(f'SENS:CORR:WAV {wavelength}')
    
    def _sense_correction_wavelength_query(self) -> str:
        return str(self._instrument.query('SENS:CORR:WAV?'))
    
    def _sense_power_range_upper(self, value: str) -> None:
        self._instrument.write(f'SENS:POW:RANG:UPP {value}')
    
    def _sense_power_range_upper_query(self) -> str:
        return str(self._instrument.query('SENS:POW:RANG:UPP?'))
    
    def _sense_power_range_auto(self, value: str) -> None:
        self._instrument.write(f'SENS:POW:RANG:AUTO {value}')
    
    def _sense_power_range_auto_query(self) -> str:
        return str(self._instrument.query('SENS:POW:RANG:AUTO?'))
    
    def _sense_power_range_index_query(self) -> str:
        return str(self._instrument.query('SENS:POW:RANG:IND?'))
    
    def _sense_power_range_nominal_query(self) -> str:
        return str(self._instrument.query('SENS:POW:RANG:NOM?'))
    
    def _sense_data_latest(self) -> str:
        return str(self._instrument.query('SENS:DATA:LAT?'))

    def _calibration_string(self) -> str:
        return str(self._instrument.query('CAL:STR?'))
    
    def _input_rotation_state(self, state: str) -> None:
        self._instrument.write(f'INP:ROT:STAT {state}')

    def _input_rotation_state_query(self) -> str:
        return str(self._instrument.query('INP:ROT:STAT?'))
    
    def _input_rotation_velocity_query(self) -> str:
        return str(self._instrument.query('INP:ROT:VEL?'))
    
    def _input_rotation_velocity_limits(self) -> str:
        return str(self._instrument.query('INP:ROT:VEL:LIM?'))

def list_devices() -> list[SCPIDevice]:
    devices = []
    resources = pyvisa.ResourceManager().list_resources()
    for r in resources:
        r_parts = r.split('::')
        id = ':'.join([r_parts[1],r_parts[2]])
        serial_number = r_parts[3]
        
        match id:
            case '4883:32817':
                devices.append(
                    Polarimeter(
                        serial_number=serial_number,
                        waveplate_rotation=Polarimeter.WaveplateRotation.OFF
                    )
                )
            case _:
                devices.append(
                    SCPIDevice(
                        id=id,
                        serial_number=serial_number
                    )
                )
                pass
    return devices

if __name__ == '__main__':
    devices = list_devices()
    for d in devices:
        print(d.device_info)
        d.disconnect()
    # print(pax.is_connected())
    # pprint.pprint(pax.device_info)
    # print(Data().from_raw_data(raw_data=pax.measure()))
    # time.sleep(5)