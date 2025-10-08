Data Available in ``homeassistant-powersensor``
================================================
The data provided in the home assistant integration should be reflective of exactly the data available
in the devices screen of the powersensor app with the exception of the top level view provided by the virtual
household

Virtual Household
------------------
Built on top of the sensors, the API provided by `powersensor_local <https://github.com/DiUS/python-powersensor_local>`_
provides a ``virtual household``. This view is captures the key data most users want to capture at the household level
This includes

* Energy imported from the grid
* Total home energy usage
* Energy exported to the grid (from solar)
* Total solar production

As well as the corresponding instantaneous power consumption/production.

Plugs
-----
Each plug exposes 6 entities reflecting the different measurements made by the plug these are

* Active Current
* Apparent Current
* Power
* Reactive Current
* Total Energy Consumption
* Voltage

This is the full extend of data available via the plug api, but much of this data is redundant and future
releases intend to make these optional selections when the integration is configured


Sensors
-------

Each sensor exposes

* Sensor battery level
* Power
* Total Energy

Any of these entities can be used in automation workflows