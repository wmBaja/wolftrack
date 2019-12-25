# Raspberry Pi Configuration
This folder contains files and instructions helpful for configuring the Raspberry Pi to behave correctly.  These resources are vitally important because, in the past, we have found that getting a Raspberry Pi into a state where certain things are possible has been tedious and time consuming.

## Bluetooth Low Energy (BLE)
Below you will find some helpful information related to Bluetooth Low Energy.

### Set Bluetooth adapter name
Edit (or create) `/etc/machine-info' and add:
  `PRETTY_HOSTNAME={DEVICE_NAME}`

Then restart the Bluetooth service:
`sudo service bluetooth restart`

### Show Bluetooth adapter info
See HCI device info:
`hciconfig -a`

See other Bluetooth info:
`bluetoothctl`
`show`

### Show all advertisement and connection info
You can use the hcidump tool to see all of the steps in the advertisement and connection processes.  This is invaluable for debugging Bluetooth.
Install hcidump:
`sudo apt-get install bluez-hcidump`

Run hcidump:
`hcidump -X`

### Enable BLE advertising
`sudo hciconfig hciX leadv`
