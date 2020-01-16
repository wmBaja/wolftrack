# Raspberry Pi Configuration
This folder contains files and instructions helpful for configuring the Raspberry Pi to behave correctly.  These resources are vitally important because, in the past, we have found that getting a Raspberry Pi into a state where certain things are possible has been tedious and time consuming.

## Bluetooth Low Energy (BLE)
Below you will find some helpful information related to Bluetooth Low Energy.

### Installing bluez
The software for the Raspberry Pi requires that the bluez installation be at least version 5.47 or higher.  The most up-to-date version is preferred.  This means that you're probably going to need to build the latest bluez version from source because the Raspbian repositories are slow to add the new versions.

#### Building bluez from source
Many of the following steps were taken from [https://learn.adafruit.com/install-bluez-on-the-raspberry-pi/installation](https://learn.adafruit.com/install-bluez-on-the-raspberry-pi/installation).
1. Download the zipped tarball of the latest version of bluez from [http://www.bluez.org/](http://www.bluez.org/).
2. Extract the files from the tarball by using: `tar xvf bluez-<VERSION>.tar.xz`
3. Change into the extracted directory: `cd bluez-<VERSION>`
4. Install the dependencies needed for building bluez:
  - `sudo apt-get update`
  - `sudo apt-get install -y libusb-dev libdbus-1-dev libglib2.0-dev libudev-dev libical-dev libreadline-dev`
5. Run the configure script.  This will ensure that all the build dependencies are met and create the Makefile to build bluez.  `./configure`
6. Assuming that there were no errors from the configure script, you can now build bluez: `make`
7. Now install it: `sudo make install`
8. Now check the status of the Bluetooth systemd service: `sudo systemctl status bluetooth`
9. Run `sudo systemctl enable bluetooth` to ensure that Bluetooth starts up when the Pi boots.
10. Now you need to modify the Bluetooth service configuration file to enable experimental features (which may be needed for certain aspects of the software): `sudo nano /lib/systemd/system/bluetooth.service`.  Add `--experimental` to the end of the  ExecStart line so that it looks like `ExecStart=/usr/local/libexec/bluetooth/bluetoothd --experimental` and save the file.
11. Now reboot the Pi (`sudo reboot`) and everything should be ready to go.  If you have any problems check the Troubleshooting section below.

#### Troubleshooting
After installing the new version of bluez, the Bluetooth adapter may be blocked by rfkill.  Run `rfkill list` to see if it is.  Now you can run `rfkill unblock bluetooth` to unblock it.

You may also need to power up the Bluetooth adapter, but the software for the RPi should also take care of this.  If necessary, you can run either `sudo hciconfig hciX up` or {`bluetoothctl`, `power on`, `exit`}.


### Set Bluetooth adapter name
Edit (or create) `/etc/machine-info` and add:
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
