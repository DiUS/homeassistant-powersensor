import random

import numpy as np

from ElectricitySensor import ElectricitySensor


class SolarSensor(ElectricitySensor):
    """Simulates a magnetic sensor"""

    def __init__(self, mac: str, update_interval: float = 30.0):
        super().__init__(mac, 'solar',  update_interval)
        self._current_summation = -683508996

    def power(self):
        if self._last_power is None:
            self._last_power = -512
        self._last_power -= int(np.round(np.random.normal(0, 60),0))
        return self._last_power