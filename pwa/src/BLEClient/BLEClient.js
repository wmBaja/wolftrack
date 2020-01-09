export default class BLEClient {
  constructor() {
    this.connected = false;
    this.simulating = false;
    this._callbacks = [];
    this.currentData = {
      fuelData: {
        remainingPercentage: 0,
        remainingLiters: 0,
        remainingLitersEMA: 0,
      },
      gpsData: {
        latitude: 0,
        longitude: 0,
        speed: 0,
        trackAngle: 0,
      },
    };
  }

  /**
   * Registers the given callback so that it is called when new data arrives.
   * @param {func} callback the callback function to register
   */
  register(callback) {
    if (!this._callbacks.includes(callback)) {
      this._callbacks.push(callback);
      callback(this.currentData);
      return true;
    }
    return false;
  }

  /**
   * Removes the given callback so that it is no longer called.
   * @param {func} callback the callback function to unregister
   */
  unregister(callback) {
    const idxOfCb = this._callbacks.findIndex((cb) => cb === callback);
    if (idxOfCb !== -1) {
      this._callbacks.splice(idxOfCb, 1);
      return true;
    }
    return false;
  }

  /**
   * Calls each of the registered callbacks with the given data.
   * @param {object} data the data to pass to each callback
   */
  _callCallbacks(data) {
    console.log('Updating data', data);
    this.currentData = data;
    this._callbacks.forEach((cb) => {
      cb(data);
    });
  }

  static generateRandomData() {
    return {
      fuelData: {
        remainingPercentage: Math.random(),
        remainingLiters: 0,
        remainingLitersEMA: 0,
      },
      gpsData: {
        latitude: 0,
        longitude: 0,
        speed: Math.random() * 40,
        trackAngle: 0,
      },
    };
  }

  _startSimulation() {
    const simulate = () => {
      const generatedData = BLEClient.generateRandomData();
      this._callCallbacks(generatedData);
    };
    this.simulationIntervalId = setInterval(simulate, 1000);
  }

  _endSimulation() {
    clearInterval(this.simulationIntervalId);
  }

  static decodeData(rawData) {
    const hexReps = [];
    const twoByteInts = [];
    for (let i = 0; i < rawData.byteLength; i++) {
      hexReps.push(('0' + rawData.getUint8(i).toString(16)).slice(-2));
      if (i % 2 === 0) {
        twoByteInts.push(rawData.getUint16(i));
      }
    }
    console.log('HexRep: ' + hexReps.join(' '));
    console.log('Uint16: ' + twoByteInts.join(' '));

    // TODO this needs to be modified to actually get the correct values from the raw data
    return {
      fuelData: {
        remainingPercentage: Math.random(),
        remainingLiters: 0,
        remainingLitersEMA: 0,
      },
      gpsData: {
        latitude: 0,
        longitude: 0,
        speed: Math.random() * 40,
        trackAngle: 0,
      },
    };
  }

  async _startConnection() {
    const handleNotifications = (event) => {
      const rawData = event.target.value;
      const decodedData = BLEClient.decodeData(rawData);
      this._callCallbacks(decodedData);
    };

    try {
      console.log('Requesting Bluetooth device from user...');
      this.bledevice = await navigator.bluetooth.requestDevice({
        acceptAllDevices: true,
        optionalServices: ['12345678-1234-5678-1234-56789abcdef0'],
      });

      console.log('Connecting to GATT server...');
      const server = await this.bledevice.gatt.connect();

      console.log('Getting Service...');
      const serviceUuid = '12345678-1234-5678-1234-56789abcdef0';
      const service = await server.getPrimaryService(serviceUuid);

      console.log('Getting Characteristic...');
      const characteristicUuid = '12345678-1234-5678-1234-56789abcdef1';
      const myCharacteristic = await service.getCharacteristic(characteristicUuid);

      console.log('Starting notifications...');
      await myCharacteristic.startNotifications();

      console.log('Notifications started.');
      myCharacteristic.addEventListener('characteristicvaluechanged',
          handleNotifications);

      return true;
    } catch(error) {
      console.log(error);
      return false;
    }
  }

  async _endConnection() {
    await this.bledevice.gatt.disconnect();
    return !this.bledevice.gatt.connected;
  }

  async connect(simulate) {
    if (!this.connected) {
      if (simulate) {
        console.log('Starting simulation...');
        this._startSimulation();
        this.simulating = true;
        console.log('Simulation started.');
      } else {
        console.log('Establishing connection...');
        const success = await this._startConnection();
        if (!success) {
          console.log('Unable to establish connection.')
          return false;
        }
        console.log('Connection established.');
      }
      this.connected = true;
      return true;
    }
    return false;
  }

  async disconnect() {
    if (this.connected) {
      if (this.simulating) {
        console.log('Ending simulation...');
        this._endSimulation();
        this.simulating = false;
        console.log('Simulation ended.');
      } else {
        console.log('Ending connection...');
        const success = await this._endConnection();
        if (!success) {
          console.log('Failed to end connection.')
          return false;
        }
        console.log('Connection ended.');
      }
      this.connected = false;
      return true;
    }
    return false;
  }
}
