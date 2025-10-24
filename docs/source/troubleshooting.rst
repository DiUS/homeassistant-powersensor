Troubleshooting
===============

If the Powersensor integration isn't showing as expected, here are
some things to check.

No Powersensor integration/devices are discovered
-------------------------------------------------
The Powersensor integration should automatically appear in the Discovered
section on the Settings > Devices & services page. If it does not, this
might mean the integration isn't installed in Home Assistant at all, in
which case the installation steps should be reviewed. In particular, verify
that the devices all have a sufficiently new firmware version.

If the Powersensor integration is installed, double check that the Powersensor
plug(s) are plugged in and switched on. If no plugs are switched on, Home
Assistant won't be able to auto-discover that the Powersensor integration is
available.

The other likely explanation is that the Home Assistant runs on a different
local network than what the Powersensor devices are on. If this is the case,
Home Assistant is unlikely to be able to find and talk to the devices. Either
the Powersensor devices or Home Assistant will need to be moved so they are
on the same network.


A sensor is not discovered
--------------------------
If a Powersensor sensor is not showing up in Home Assistant despite being
installed and visible in the Powersensor app, check the following in the app:

* That the sensor still has battery charge.

  If necessary, recharge and then reinstall the sensor using the app.

* That the sensor has a plug it is relaying its data through; and
* That the reported Bluetooth signal strength is good (ideally > -90dB).

  If no plug is available in range of the sensor, either relocate the plug
  closer to the sensor, or consider installing an extra plug closer to
  the sensor.


A plug is not discovered
------------------------
Plugs are discovered automatically using the standard Zeroconf (also known as
Bonjour) protocol on the local network. If a plug is not being discovered,
check:

* That the plug is actually powered.
* That Home Assistant is connected to the same local network as the plug.
* Whether switching the plug off and back on again helps. A plug will
  reannounce itself on the network at startup, which might help discovery.


The plug totals don't match with the app
-----------------------------------------
The "Total energy" plug readings, are unlikely to perfectly match what is
shown in the app. The values reported by the plug to Home Assistant only show
the energy since the plug was last restarted, while the app reports aggregated
values for individual intervals.

Home Assistant performs the same type of calculations, which are accessible
via the History view.


The household energy doesn't match with the app
-----------------------------------------------
This is a result of different architectural design decisions between
Powersensor and Home Assistant. Please refer to :ref:`this note <vhh-net-issue>`.


The household view doesn't show solar even though I have a solar kit
--------------------------------------------------------------------
There are a couple of likely explanations for this.

First, ensure that your solar sensor has been discovered correctly. If it
isn't, refer to the previous section for advise on how to address that.

The second likely cause is that the solar sensor isn't aware of its assigned
role as a solar sensor. The sensor role gets set during installation via the
app. However, the first generation of sensor hardware loses this information
if the sensor runs out of battery charge completely. Note that this is not
the case with the current generation of sensors. To see if this might be
the cause, go to Settings > Devices & services > Powersensor and select
the sensor in question. If the diagnostic entry "Device role" says "<unknown>"
this means the sensor does not have current role information.

In this case, go back to the main Powersensor integration page, and select
"Reconfigure" from the meat ball menu (three dots vertically). From this
dialog the proper role can be assigned to the sensor.

.. note::
  Role information provided directly by a sensor will override any manual
  configuration done. If the sensor's own role needs to be changed, it is
  necessary to go through a reinstall via the app instead.


The household view just says "unavailable"
------------------------------------------
This is indicative of the Powersensor mains sensor not being reachable, or
lacking its role information. Check:

* That the sensor still has battery charge.

  If necessary, recharge and then reinstall the sensor using the app.

* That the sensor has a plug it is relaying its data through; and
* That the reported Bluetooth signal strength is good (ideally > -95).

  If no plug is available in range of the sensor, either relocate the plug
  closer to the sensor, or consider installing an extra plug closer to
  the sensor.

* Whether the sensor has the role "house-net", in the "Device role" diagnostic
  found under Settings > Devices & services > Powersensor for the sensor
  in question.

  If the role is listed as unknown, go back to the main Powersensor integration
  page, and select "Reconfigure" from the meat ball menu (three dots
  vertically). From this dialog change the device role to "house-net".

.. note::
  Role information provided directly by a sensor will override any manual
  configuration done. If the sensor's own role needs to be changed, it is
  necessary to go through a reinstall via the app instead.


A plug is not showing current or voltage readings
-------------------------------------------------
While a plug reports both current and voltage readings, they are not
automatically visible on the dashboard. If they are of interest, go to
Settings > Devices & services > Powersensor and select the plug. In the
Sensor section, click on the current or voltage entity you wish to see, then
the gear icon (⚙) and ensure both Enabled and Visible are toggled on.
