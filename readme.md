[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)

# Unify Home Assistant Integration

The Unify Framework provides software source code and binary packages for Raspberry Pi 4 to help build an IoT gateway product. The Unify Framework enables an IoT service to control and manage end nodes in several wireless PHY radios (e.g., Z-Wave, Zigbee, and so on) supported by Silicon Labs. For information and access to the Unify Framework please refer to [https://github.com/SiliconLabs/UnifySDK](https://github.com/SiliconLabs/UnifySDK).

The Unify Home Assistant Integration enables any device on Unify Framework to be utilised by Home Assistant.
This allows for easy use and integration of the Unify Framework exposing numerous devices running on multiple wireless protocols.

## Requirements

It integrates into an existing Home Assistant environment.
To enable the Unify bridge the components requirements must be met:

* MQTT-Broker
* Home Assistant
* Unify Framework with a Protocol Controller (PC) e.g. ZPC (Z-Wave), ZigPC (ZigBee).

## Installation

### HACS (recommended)
Currently only custom repository is supported.
To install:
* Add [https://github.com/SiliconLabs/Unify_HomeAssistant](https://github.com/SiliconLabs/Unify_HomeAssistant) as a custom repository in the "Integration" category
* Find the Unify integration and in install it by clicking "Download"
* Restart Home Assistant

In Home Assistant Integration section (Settings->Devices & Services->Integration):
* Add MQTT Integration if not already installed and make sure it points to the Unify MQTT server
* Unify Integration should be automatically discovered - click Configure

### Manual installation
* Copy `this` folder to `custom_components` on your HA installation. If custom_components does not exist, create it in the root of the HA config folder, ie. same level as the `configuration.yaml` file.
* In the Home Assistant UI add Unify integration or MQTT intrgration and setup the MQTT integration to use the Unify MQTT server.

Word of caution, it is very verbose on log level `_LOGGER.debug`.

## Supported Clusters

Unify is based on the Zigbee Cluster Library. The clusters supported in the Unify bridge is listed below.

| ZCL Cluster            | Home Assistant Device |
| ---------------------- | --------------------- |
| OnOff                  | Switch                |
| Level                  | Light                 |
| ColorControl           | Light                 |
| OccupancySensing       | BinarySensor          |
| PowerConfiguration     | Sensor (Battery)      |
| TemperatureMeasurement | Sensor (Temperature)  |
| Scene                  | Sensor (Binary)       |

In addition ZCL NameAndLocation is used to set Name of Home Assistant Devices.
