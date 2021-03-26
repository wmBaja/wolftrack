import DataDecoder from './DataDecoder.js';


//import { COMPETITION_PACKET_DEFINITION } from './PACKET_DEFINITIONS.js';

export default class DataGenerator {
  static generateRandomData(currentData) {
    // generate random values for the integers
    // 1. fuel sensor reading
    const fuelReading = Math.round(Math.random() * 100);
    // 2. engine RPM
    const engineRPM = Math.round(Math.random() * 3000 + 1000);
    // 3. CVT secondary RPM
    const secRPM = Math.round(engineRPM / (Math.random() * 2.6 + 0.9));
    // 4. CVT temperature reading
    const cvtTempReading = Math.round(Math.random() * 255);
    // 5. brake pressure sensor 1 reading
    const brakePressureReading1 = Math.round(Math.random() * 2000);
    // 6. brake pressure sensor 2 reading
    const brakePressureReading2 = Math.round(Math.random() * 2000);

    const sensors = {
      fuel: fuelReading,
      engine_rpm: engineRPM,
      cvt_rpm: secRPM,
      cvt_temp: cvtTempReading,
      front_brake_pressure: brakePressureReading1,
      rear_brake_pressure: brakePressureReading2,
    };

    return {
      sensorRawValues: sensors,
      fuel: DataDecoder.calculateFuelData(sensors.fuel, currentData.fuel.remainingEMALiters),
      drivetrain: DataDecoder.calculateDrivetrainData(sensors.engine_rpm, sensors.cvt_rpm, sensors.cvt_temp),
      brakes: DataDecoder.calculateBrakesData(sensors.front_brake_pressure, sensors.rear_brake_pressure),
      // suspension: DataDecoder.calculateSuspensionData(shockActuationReading1, shockActuationReading2),
    };
  }
}