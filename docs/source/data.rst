Data Available in ``homeassistant-powersensor``
================================================
The data provided in the home assistant integration should be reflective of exactly the data available
in the devices screen of the powersensor app with the exception of the top level view provided by the virtual
household.

Virtual Household
------------------
Built on top of the sensors, the API provided by `powersensor_local <https://github.com/DiUS/python-powersensor_local>`_
provides a ``virtual household``. This view is captures the key data most users want to capture at the household level.
This includes

* Energy imported from the grid
* Total home energy usage
* Energy exported to the grid (from solar)
* Total solar production

as well as the corresponding instantaneous power consumption/production.

.. note::

  Powersensor deals with *net* readings, meaning that the energy import and
  export direction is determined by the sign of value. Home Assistant however
  requires *gross* readings, where values are always positive and divided
  into separate import and export values instead.

  The Virtual Household view performs the necessary calculations to match
  Home Assistant's needs in order to easily use Powersensor data in its
  Energy dashboard. However, you will find that the Total Energy shown for
  the sensor(s) generally do not match what's shown under the household
  view. This is expected and is a consequence of going from net to gross.
  The energy readings will reset to zero whenever Home Assistant is restarted,
  but HomeAssistant tracks the overall total correctly.

The household readings update as sensor data becomes available.

Plugs
-----
Each plug exposes 6 entities reflecting the different measurements made by the plug these are

* Power
* Total Energy Consumption
* Active Current
* Reactive Current
* Apparent Current
* Voltage

Of these only the power and total energy are commonly of interest, and future
releases intend to make the others optional inclusions when the integration
is configured.

The plug readings typically update every second.

Sensors
-------

Each sensor exposes

* Sensor battery level
* Power
* Total Energy

The sensor readings typically update every 30 seconds, but are dependent on the
sensor being within range of a plug to act as a relay for it. If sensors aren't
showing up as expected, use the mobile app to check which plug it's trying
to relay though, and the signal strength. If necessary, relocate a plug to
somewhere closer to the sensor to improve the signal strength.

Automations
-----------

Any of the plug, sensor or virtual household  entities can be used in
automation workflows.
