"""Constants for the Powersensor integration."""

DOMAIN = "powersensor"
DEFAULT_NAME = "Powersensor"
DEFAULT_PORT = 49476
DEFAULT_SCAN_INTERVAL = 30

CREATE_PLUG_SIGNAL = f"{DOMAIN}_create_plug"
CREATE_SENSOR_SIGNAL = f"{DOMAIN}_create_sensor"
DATA_UPDATE_SIGNAL_FMT_MAC_EVENT = f"{DOMAIN}_data_update_%s_%s"
ROLE_UPDATE_SIGNAL = f"{DOMAIN}_update_role"
PLUG_ADDED_TO_HA_SIGNAL = f"{DOMAIN}_plug_added_to_homeassistant"
SENSOR_ADDED_TO_HA_SIGNAL = f"{DOMAIN}_sensor_added_to_homeassistant"
SOLAR_SENSOR_DETECTED_SIGNAL = f"{DOMAIN}_solar_sensor_detected"
SOLAR_ADDED_TO_VHH_SIGNAL = f"{DOMAIN}_solar_added_to_virtual_household"
ZEROCONF_ADD_PLUG_SIGNAL = f"{DOMAIN}_zeroconf_add_plug"
ZEROCONF_REMOVE_PLUG_SIGNAL = f"{DOMAIN}_zeroconf_remove_plug"
ZEROCONF_UPDATE_PLUG_SIGNAL = f"{DOMAIN}_zeroconf_update_plug"


SENSOR_NAME_FORMAT = "Powersensor Sensor (ID: %s) ⚡"
