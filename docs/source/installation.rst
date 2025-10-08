Installation
============

In its current form, the only supported installation method for the ``homeassistant-powersensor`` integration is
manual. In the near future, we intend to support installation via `HACS <https://hacs.xyz/>`_
however that is not yet possible.

Prerequisites
--------------
Before installing this integration, ensure you have:

* Home Assistant 2024.1.0 or newer
* Access to your Home Assistant configuration directory
* `powersensor_local <https://github.com/DiUS/python-powersensor_local>`_ 2.0.0 or later installed in your Home Assistant instance's python environment
* Firmware updated to version 8107 or later on powersensor hardware (plugs and sensors)

From Source
------------
Clone or download this repo e.g
.. code-block:: bash

   git clone https://github.com/DiUS/homeassistant-powersensor.git

Copy or symlink the directory ``custom_components/powersensor`` to your Home Assistant configuration directory.
When launching homeassistant, e.g.
.. code-block:: bash

   hass --config ./config

Home assistant should automatically discover powersensor devices on the same network.
Follow the links for Settings/Devices&Services. At the top you should be prompted add ``powersensor`` to your
homeassistant instance.