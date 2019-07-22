#! /usr/bin/env python

from flask import Flask, send_from_directory
app = Flask(__name__, static_url_path='')

STATIC_DIR = 'client/build'

@app.route('/')
def hello():
    return send_from_directory(STATIC_DIR, 'index.html')

@app.route('/<path>')
def send_js(path):
    return send_from_directory(STATIC_DIR, path)

@app.route('/<path:base>/<path:path>')
def send_files(base, path):
    return send_from_directory(STATIC_DIR, base + '/' + path)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port='5000', debug=True)
