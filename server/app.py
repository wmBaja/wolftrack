#! /usr/bin/env python
"""
This is a Flask web server that
"""

import signal
import atexit
from flask import Flask, send_from_directory, jsonify
from flask_socketio import SocketIO, emit

from hardware.HardwareManager import HardwareManager


# monkey patch the threading library so that background threads will work with SocketIO
import eventlet
eventlet.monkey_patch()


# whether or not the program has been cleaned up yet
cleanedUp = False

def cleanup():
  """
  Cleans up the program by:
    - Shutting down the hardware manager
  """
  global cleanedUp, hwManager
  if not cleanedUp:
    print('Cleaning up')
    hwManager.stopPollers()
    cleanedUp = True

def sigint_handler(signal, frame):
  cleanup()
  quit()

# catch the kill signal to end gracefully
signal.signal(signal.SIGINT, sigint_handler)
# cleanup when exiting
atexit.register(cleanup)


app = Flask(__name__, static_url_path='')
socketio = SocketIO(app)

def onHwData(dataType, value):
  print(str(dataType) + ': ' + str(value))
  socketio.emit('hwdata', {'type': dataType, 'value': value})


hwManager = HardwareManager(onHwData)

STATIC_DIR = '../client/build'

@app.route('/')
def hello():
  return send_from_directory(STATIC_DIR, 'index.html')

@app.route('/<path>')
def send_js(path):
  return send_from_directory(STATIC_DIR, path)

@app.route('/<path:base>/<path:path>')
def send_files(base, path):
  return send_from_directory(STATIC_DIR, base + '/' + path)


@socketio.on('connect')
def handle_connection():
  print('New SocketIO connection established')

@socketio.on('message')
def handle_message(message):
  print('Received message: ' + message)

@socketio.on('json')
def handle_json(json):
  print('Received JSON: ' + str(json))

@socketio.on('blah')
def handle_custom_event(msg):
  print('Received custom_event: ' + str(msg))
  socketio.send('message received')

if __name__ == '__main__':
  hwManager.startPollers() # start the sensor pollers

  # running the app in debug mode will cause two threads to be started
  socketio.run(app, host='0.0.0.0', port='5000', debug=False)
