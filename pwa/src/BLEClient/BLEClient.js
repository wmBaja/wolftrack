export default class BLEClient {
  constructor() {
    this.connected = false;
    this.simulating = false;
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

  startSimulation(callback) {
    function simulate() {
      callback(BLEClient.generateRandomData());
    }
    this.simulationIntervalId = setInterval(simulate, 1000);
  }

  endSimulation() {
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

  async startConnection(callback) {

    function handleNotifications(event) {
      const rawData = event.target.value;
      const decodedData = BLEClient.decodeData(rawData);
      callback(decodedData);
    }

    try {
      console.log('Requesting Bluetooth device from user...');
      const device = await navigator.bluetooth.requestDevice({
        acceptAllDevices: true,
        optionalServices: ['12345678-1234-5678-1234-56789abcdef0'],
      });

      console.log('Connecting to GATT server...');
      const server = await device.gatt.connect();

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

  async connect(callback, simulate) {
    if (!this.connected) {
      if (simulate) {
        console.log('Starting simulation...');
        this.startSimulation(callback);
        this.simulating = true;
        console.log('Simulation started.');
      } else {
        console.log('Establishing connection...');
        const success = await this.startConnection(callback);
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
      this.connected = false;
      if (this.simulating) {
        this.endSimulation();
        this.simulating = false;
        console.log('Simulation ended.');
      }
      return true;
    }
    return false;
  }
}
