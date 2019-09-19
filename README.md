# wolftrack
Keep track of the Wolfpack...on the track ;))

## Installation
These are the steps for installation on a Raspberry Pi.
### Assumptions
 - Python 3.5 or higher is installed on your machine.
 - SPI is enabled.

1. Clone this repository onto your machine.
2. Create a Python virtual environment in the root directory of the project by running `python3 -m venv venv`.
3. Activate the virtual environment by running `source venv/bin/activate`.
4. Download the dependencies by running `pip install -r requirements.txt`.
5. Start the web server and hardware polling by running `python server/app.py`.
