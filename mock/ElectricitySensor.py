import random

from MockSensor import MockSensor


class ElectricitySensor(MockSensor):
    """Simulates a magnetic sensor"""

    def __init__(self, mac: str, role=None, update_interval: float = 30.0):
        super().__init__(mac, role,  update_interval)

    def get_unit(self):
        return 'w'
