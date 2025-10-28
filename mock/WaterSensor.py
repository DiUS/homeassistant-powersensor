import random

from MockSensor import MockSensor


class WaterSensor(MockSensor):
    """Simulates a water sensor"""

    def __init__(self, mac: str, update_interval: float = 30.0):
        super().__init__(mac, 'water',  update_interval)

    def get_unit(self):
        return 'L'
