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
* Firmware updated to version 8129 or later on powersensor hardware (plugs and sensors)

From Source
------------
If you have commandline access to the machine running Home Assistant, simply clone or download this repo e.g.

.. code-block:: bash

   git clone https://github.com/DiUS/homeassistant-powersensor.git

Copy or symlink the directory ``custom_components/powersensor`` to your Home Assistant configuration directory.
When launching homeassistant, e.g.

.. code-block:: bash

   hass --config ./config

Home assistant should automatically discover powersensor devices on the same network.
Follow the links for Settings/Devices & Services. At the top you should be prompted add ``powersensor`` to your
homeassistant instance. Alternatively, you can can click the +Add Integration button and search for ``powersensor``

HA OS
-----
If you are installing on a dedicated device running HA OS such as Home Assistant Green, you may need to take a few extra steps.
If you have ssh access to the box, you can follow the command line instructions above. However, the recommended
option for most users is to install the `Samba Add-on <https://www.home-assistant.io/common-tasks/os/#installing-and-using-the-samba-add-on>`_.
Once installed, you should be able to mount your Home Assistant root directory as a network drive. From there,
clone or download this repo and copy the ``custom_components/powersensor`` directory to your config folder.