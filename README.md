# wolftrack
Keep track of the Wolfpack...on the track ;)


## Working with ESP32
The steps below assume that you are using the HiLetgo ESP-WROOM-32 ESP32 ESP-32S Development Board that you can purchase on Amazon [here](https://www.amazon.com/dp/B0718T232Z).  If you're working with a different board, then these instructions may be slightly different.

### Set up the Arduino IDE
1. Make sure you have the Arduino IDE installed.  You can install it [here](https://www.arduino.cc/en/Main/Software).
2. Next you need to install the ESP32 board definitions.  Open the Arduino IDE and go to File > Preferences.
3. In the "Additional Board Manager URLs" field, add "https://dl.espressif.com/dl/package_esp32_index.json" and click OK.
4. Now go to Tools > Boards > Boards Manager...
5. Search for "esp32" and install the package called "esp32 by Espressif Systems".

### Test connecting and uploading to the ESP32
1. Connect your ESP32 to your computer with a USB cable.
2. Go to Tools > Board and select "Node32s".  Quite a few of these board selections should work with the HiLetgo board (like the "DOIT ESP32 DEVKIT V1"), but Node32s is the one that others have recommended on the Amazon page for the HiLetgo board.
3. Next, select the port that your ESP32 is connected to under Tools > Port.  The port name will be different based on if you are Mac, Linux, or Windows.  If the correct port doesn't show up, then you may need to install some drivers (see the Testing Installation section of [this article](https://randomnerdtutorials.com/installing-the-esp32-board-in-arduino-ide-windows-instructions/)).
4. Next, we'll open an example sketch that scans for nearby WiFi networks.  Go to File > Examples.  Under the "Examples for Node32s" section, go to WiFi > WiFiScan.
5. Click the "Upload" button to upload the sketch to the ESP32.  If everything worked correctly, you should see a "Done uploading." message.  Now you can see the output by going to Tools > Serial Monitor and setting the baud rate to 115200.  If the output looks jumbled, then press the "EN" button (enable/reset button) on the ESP32 to restart it and also clear the output in the Serial Monitor.

### Troubleshooting uploading sketches
- If you get an error along the lines of: "ImportError: cannot import serial" or something like it, then make sure that your default Python installation has pyserial installed.  You can install it by running the following command: "pip install pyserial".
- If you get an error along the lines of: "[Errno 13] Permission denied: '<the port your EPS32 is connected to>'", then check out [this post](https://sudomod.com/forum/viewtopic.php?t=6075).  You basically need to allows certain permissions on that port.  Note that if this occurs on Windows, then this post probably won't be useful sense it's discussing the issue on Linux.
- If it seems like the Arduino IDE is not connecting to the board or uploading the sketch (you see "Connecting...___...___..." for a while), then you may need to press or hold the BOOT/FLASH button (not the EN (enable) button) on the ESP32.  See [this article](https://randomnerdtutorials.com/solved-failed-to-connect-to-esp32-timed-out-waiting-for-packet-header/) for more info.
