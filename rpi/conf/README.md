# Raspberry Pi Configuration
This folder contains files and instructions helpful for configuring the Raspberry Pi to behave correctly.  These resources are vitally important because, in the past, we have found that getting a Raspberry Pi into a state where certain things are possible has been tedious and time consuming.

## Setup Steps
These are the general steps that you should follow after initially booting into the Raspberry Pi and going through the initial setup.
### 1. Make sure that you're connected to the Internet
This should be taken care of by the initial setup steps, but sometimes the Internet can still be wonky.  Just open up Chromium and make sure you can get to Google or YouTube.  If not, fix it by connecting to another network or doing what you gotta do.
### 2. Update all packages
1. Update the package listings for the Pi by running `sudo apt-get update`.
2. Upgrade all packages by running `sudo apt-get upgrade`.
### 3. Enable SSH, Serial Port, and Serial Console
Run the Raspberry Pi Configuration tool and enable SSH, Serial Port, and Serial Console.
### 4. Make sure that the Pi's time is automatically synced through NTP
Run `timedatectl status` to see if the Pi's time is synced through NTP.  If not, you can check out [this article](https://raspberrytips.com/time-sync-raspberry-pi/) to see how to sync it.
### 5. Setup Bluetooth and bluez
The Bluetooth and bluez stack on the Pi are probably out-of-date (the package manager does not keep the most up-to-date versions).  The Wolftrack software requires at least version 5.47 of bluez.  You can check the version of bluez by running `bluetoothctl --version`.  If 5.47 or higher is already installed, then you're probably fine.  But if you have some extra time on your hands, then it's probably best to run through the steps for compiling bluez from source below in the Bluetooth section.

Regardless, you'll still need to modify the Bluetooth service file to add the `--experimental` flag, so look at step 10 in the "Building bluez from source" section.

You'll also want to modify the Bluetooth device name, so follow the steps in the "Set Bluetooth device name" section.
### 6. Download the Wolftrack software
Now you can download the actual Wolftrack software Git repository.
1. Make sure that you're in pi user's home directory by running `cd`.
2. Now download the repo by running `git clone https://github.com/wmBaja/wolftrack.git`.  The repo should be copied into a directory called wolftrack.

It's imperative that the repo is setup in this exact location (the service file (step 8) is written to use this location).  Ensure that the wolftrack repo's absolute path is `/home/pi/wolftrack`.
### 7. Setup a Python virtual environment for Wolftrack
Now you need to setup a Python virtual environment for Wolftrack so that it can have its own isolated packages.
1. First you want to make sure that you have Python 3.5 or higher installed (Raspbian should come with it pre-installed) by running `python3 --version`.  If the python3 command isn't found or if your version is lower than 3.5, then install the latest version of Python 3.
2. Next make sure that you're in the root of the repo.  Run `cd /home/pi/wolftrack`.
3. Next create a virtual environment called "venv" by running `python3 -m venv venv`.
4. Now you need to activate the virtual environment by running `source venv/bin/activate`.  Now when you run the `python` or `pip` commands, it uses the copy of Python 3 that was setup in the virtual environment.  If you need to deactivate the virtual environment, then just run `deactivate`.
5. Now you need to install the Python dependencies for Wolftrack by running `pip install -r rpi/requirements.txt`.  You may get errors during this process due to missing libraries, but there should be commands included in the output to tell you want you need to install.  Some libraries that you will probably need to install with `apt-get` for the PyGObject Python library are: `libglib2.0-dev`, `libgirepository1.0-dev`, and `libcairo2-dev`.

If you'd like to manually run the software for whatever reason you can do so by changing into the rpi/ directory (`cd rpi`) and running `python app.py`.  However, this is not how the software should typically run.  Step 8 will show you how to setup Wolftrack to run as a systemd service.

More information about Python virtual environments can be found [here](https://realpython.com/python-virtual-environments-a-primer/).
### 8. Install the Wolftrack systemd service
Wolftrack runs best as a systemd service.  A service file has already been created and is included in the rpi/conf/ folder of the repository.
1. You need to copy this file to /etc/systemd/system/ by running `sudo cp wolftrack.service /etc/systemd/system/` (assuming that you're in the rpi/conf/ directory).
2. Then you need to modify the file permissions by running `sudo chmod 664 /etc/systemd/system/wolftrack.service`.
3. Then reload the systemd configuration by running `sudo systemctl daemon-reload`.
4. And enable Wolftrack so that it starts automatically at boot by running `sudo systemctl enable wolftrack`.

Now you can start, stop, restart, and check the status of Wolftrack just like any other systemd service.  Use the following commands: `sudo systemctl start wolftrack`, `sudo systemctl stop wolftrack`, `sudo systemctl restart wolftrack`, `systemctl status wolftrack`.  You can also check the live logs of the service by running `journalctl -u wolftrack`.

More information about custom systemd services can be found [here](https://www.shellhacks.com/systemd-service-file-example/).

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
10. Now you need to modify the Bluetooth service configuration file to enable experimental features (which may be needed for certain aspects of the software): `sudo nano /lib/systemd/system/bluetooth.service`.  Add `--experimental` to the end of the  ExecStart line so that it looks like `ExecStart=/usr/local/libexec/bluetooth/bluetoothd --experimental` and save the file.  Now reload the systemd configuration by running `sudo systemctl daemon-reload`.
11. Now reboot the Pi (`sudo reboot`) and everything should be ready to go.  If you have any problems check the Troubleshooting section below.

#### Troubleshooting
After installing the new version of bluez, the Bluetooth adapter may be blocked by rfkill.  Run `rfkill list` to see if it is.  Now you can run `rfkill unblock bluetooth` to unblock it.

You may also need to power up the Bluetooth adapter, but the software for the RPi should also take care of this.  If necessary, you can run either `sudo hciconfig hciX up` or {`bluetoothctl`, `power on`, `exit`}.

### Set Bluetooth device name
Edit (or create) `/etc/machine-info` and add:
  `PRETTY_HOSTNAME={DEVICE_NAME}`
Ex: `PRETTY_HOSTNAME=NCSU Baja`

Then restart the Bluetooth service:
`sudo service bluetooth restart`

### Useful Bluetooth commands
#### Show Bluetooth adapter info
See HCI device info:
`hciconfig -a`

See other Bluetooth info:
`bluetoothctl`
`show`

#### Show all advertisement and connection info
You can use the hcidump tool to see all of the steps in the advertisement and connection processes.  This is invaluable for debugging Bluetooth.
Install hcidump:
`sudo apt-get install bluez-hcidump`

Run hcidump:
`hcidump -X`

#### Enable BLE advertising
`sudo hciconfig hciX leadv`
