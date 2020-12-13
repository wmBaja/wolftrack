import { DEFAULT_DATA } from '../DataProtocol/DEFAULT_DATA.js';
import DataDecoder from '../DataProtocol/DataDecoder.js';
import DataGenerator from '../DataProtocol/DataGenerator.js';

// the interval on which random data is generated for a simulated connection (ms)
const SIMULATION_INTERVAL = 200;

export default class BLEClient {
  constructor() {
    this.connected = false;
    this.simulating = false;
    this._callbacks = [];
    this.currentData = DEFAULT_DATA;
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
    // console.log('Updating data', data);
    this.currentData = data;
    this._callbacks.forEach((cb) => {
      cb(data);
    });
  }

  _startSimulation() {
    const simulate = () => {
      const generatedData = DataGenerator.generateRandomData(this.currentData);
      this._callCallbacks(generatedData);
    };
    this.simulationIntervalId = setInterval(simulate, SIMULATION_INTERVAL);
  }

  _endSimulation() {
    clearInterval(this.simulationIntervalId);
  }

  async _startConnection() {
    const handleNotifications = (event) => {
      const rawIncomingData = event.target.value;
      const decodedData = DataDecoder.decodeData(rawIncomingData, this.currentData);
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
      this.currentData = DEFAULT_DATA;
      return true;
    }
    return false;
  }
}
