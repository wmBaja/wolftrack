import DataDecoder from './DataDecoder.js';

export default class DataGenerator {
  static generateRandomData(currentData) {
    // create an ArrayBuffer with a size in bytes
    const buffer = new ArrayBuffer(16);

    // create a DataView
    const dataView = new DataView(buffer);

    // generate random values for the integers
    // 1. fuel gauge Hall-effect sensor reading
    const fuelHallEffectReading = Math.round(Math.random() * 1024);
    // 2. engine RPM
    const engineRPM = Math.round(Math.random() * 3500);
    // 3. CVT RPM
    const cvtRPM = Math.round(Math.random() * 1000);
    // 4. CVT thermistor reading
    const cvtThermistorReading = Math.round(Math.random() * 1024);
    // 5. brake pressure sensor 1 reading
    const brakePressureReading1 = Math.round(Math.random() * 1024);
    // 6. brake pressure sensor 2 reading
    const brakePressureReading2 = Math.round(Math.random() * 1024);
    // 7. shock actuation sensor 1 reading
    const shockActuationReading1 = Math.round(Math.random() * 1024);
    // 8. shock actuation sensor 2 reading
    const shockActuationReading2 = Math.round(Math.random() * 1024);

    // set the values in the DataView
    dataView.setUint16(0, fuelHallEffectReading);
    dataView.setUint16(2, engineRPM);
    dataView.setUint16(4, cvtRPM);
    dataView.setUint16(6, cvtThermistorReading);
    dataView.setUint16(8, brakePressureReading1);
    dataView.setUint16(10, brakePressureReading2);
    dataView.setUint16(12, shockActuationReading1);
    dataView.setUint16(14, shockActuationReading2);

    return DataDecoder.decodeData(dataView, currentData);
  }
}