Data Available in ``homeassistant-powersensor``
================================================
The data provided in the home assistant integration should be reflective of exactly the data available
in the devices screen of the powersensor app with the exception of the top level view provided by the virtual
household.

Virtual Household
------------------
Built on top of the sensors, the API provided by `powersensor_local <https://github.com/DiUS/python-powersensor_local>`_
provides a "virtual household". This view captures the key data most users want to capture at the household level.
This includes

* Total home energy usage
* Energy imported from the grid
* Energy exported to the grid (from solar)
* Total solar production

as well as the corresponding instantaneous power consumption/production.

For installations lacking solar, the generation related entities will not
be available.

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
Each plug exposes several entities reflecting the different measuremens
made by the plug. By default only two are made visible:

* Power
* Total Energy

The remaining entities are:

* Volts
* Active Current
* Reactive Current
* Apparent Current

These are of secondary importance and usefulness, and hence aren't visible
by default. They can be selectively made visible by going to Settings >
Devices & services > Powersensor and selecting the plug, then clicking on
the desired entity and then the gear on the following screen. Toggle the
Visible option there.

The Volts entity shows the mains voltage as seen at that particular plug. Due
to voltage drop in wires, each plug is likely to show a slightly different
mains voltage.

Simplified, the Apparent Current entity shows the effective current going
through the plug. This is the current that may lead to a breaker tripping if
it gets excessive. The Active and Reactive measurements are the components
of it, and are likely of little interest outside of curiousity.

.. note::
  It is more common to hear of Active, Reactive and Apparent *Power*, and
  the plug's different current measurements should not be confused for power
  measurements.

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

.. note::
  Water sensors are not fully supported in the integration at this time.
  Water sensors will appear in the integration, but will only report
  sensor battery level. Development for water sensors is on-going and
  we hope to provide full support in future.

Automations
-----------

Any of the plug, sensor or virtual household  entities can be used in
automation workflows. To exercise control of other devices in your
household, first install any relevant integrations for those devices.
Then follow the usual Home Assistant steps for setting up rules:
Settings >Automations & Scenes and +Create Automation
