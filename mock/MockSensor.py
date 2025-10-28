import asyncio
import datetime
import logging
from abc import abstractmethod, ABC


logger = logging.getLogger(__name__)

class MockSensor(ABC):
    """Base class for mock sensors most methods are meant to be overridden"""

    def __init__(self, mac: str, role: str | None=None,  update_interval: float = 30.0):
        self.mac = mac
        self.role = role
        self.update_interval = update_interval

    @abstractmethod
    def get_unit(self)->str:
        pass

    def get_raw_rssi(self):
        return -95

    def get_rssi(self):
        return  -95.31663879935132

    def summation_start(self):
        return 1761122290

    def battery_microvolt(self):
        return 4057056

    def duration(self):
        return self.update_interval

    def power(self):
        return 728

    def summation(self):
        return 215449157

    def generate_reading(self) -> dict:
        return {'starttime': datetime.datetime.now(datetime.timezone.utc).timestamp(),
         'raw_rssi': self.get_raw_rssi(),
         'device': 'sensor',
         'rssi': self.get_rssi(),
         'type': 'instant_power',
         'summation_start': self.summation_start(),
         'batteryMicrovolt': self.battery_microvolt(),
         'mac': self.mac,
         'duration': self.duration(),
         'role': self.role,
         'power': self.power(),
         'unit': self.get_unit(),
         'summation': self.summation()}

    async def run(self, callback):
        """
        Continuously generate sensor readings and call the callback.

        Args:
            callback: async function to call with each reading
        """
        logger.info(f"Sensor {self.mac} starting (interval: {self.update_interval}s)")
        while True:
            try:
                await asyncio.sleep(self.update_interval)
                reading = self.generate_reading()
                logger.debug(f"Sensor {self.mac} calling callback with reading: {reading}")
                await callback(reading)
                logger.debug(f"Sensor {self.mac} callback completed")
            except Exception as e:
                logger.error(f"Sensor {self.mac} error in run loop: {e}", exc_info=True)