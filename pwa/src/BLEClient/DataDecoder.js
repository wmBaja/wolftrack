import { MAX_ANALOG_VALUE, NEUTRAL_MAGNETISM_VALUE, MAX_FUEL_CAPACITY, MAGICAL_CONSTANT_FOR_SPEED, MAX_LIN_POT_ACTUATION_IN } from './DEFAULT_DATA.js';

const FUEL_EMA_WEIGHT = 0.1;

export default class DataDecoder {
  static decodeData(rawData, currentData) {
    if (rawData.byteLength !== 16) {
      console.log('Non-protocol number of bytes in data array: ' + rawData.byteLength);
      console.log('Undefined behavior expected...');
    }
    const curRemainingEMALiters = currentData.fuel.remainingEMALiters;
    // const hexReps = [];
    const twoByteInts = [];
    for (let i = 0; i < rawData.byteLength; i++) {
      // hexReps.push(('0' + rawData.getUint8(i).toString(16)).slice(-2));
      if (i % 2 === 0) {
        twoByteInts.push(rawData.getUint16(i));
      }
    }
    // console.log('HexRep: ' + hexReps.join(' '));
    // console.log('Uint16: ' + twoByteInts.join(' '));

    /*
    The data protocol specifies that the array of 8 16-bit integers correspond to:
    1. fuel gauge Hall-effect sensor reading
    2. engine RPM
    3. CVT RPM
    4. CVT thermistor reading
    5. brake pressure sensor 1 reading
    6. brake pressure sensor 2 reading
    7. shock actuation sensor 1 reading
    8. shock actuation sensor 2 reading
    */

    const fuelHallEffectReading = twoByteInts[0];
    const engineRPM = twoByteInts[1];
    const cvtRPM = twoByteInts[2];
    const cvtThermistorReading = twoByteInts[3];
    const brakePressureReading1 = twoByteInts[4];
    const brakePressureReading2 = twoByteInts[5];
    const shockActuationReading1 = twoByteInts[6];
    const shockActuationReading2 = twoByteInts[7];

    return {
      rawData,
      fuel: DataDecoder.calculateFuelData(fuelHallEffectReading, curRemainingEMALiters),
      drivetrain: DataDecoder.calculateDrivetrainData(engineRPM, cvtRPM, cvtThermistorReading),
      brakes: DataDecoder.calculateBrakesData(brakePressureReading1, brakePressureReading2),
      suspension: DataDecoder.calculateSuspensionData(shockActuationReading1, shockActuationReading2),
    };
  }

  static _calcRemainingLiters(distFromCenterValue) {
    return (distFromCenterValue / 513) * MAX_FUEL_CAPACITY;
  }

  static _calcRemainingEMALiters(curAvg, newVal) {
    return FUEL_EMA_WEIGHT * newVal + (1 - FUEL_EMA_WEIGHT) * curAvg;
  }

  static calculateFuelData(sensorReading, curRemainingEMALiters) {
    const distFromCenterValue = Math.abs(sensorReading - NEUTRAL_MAGNETISM_VALUE);

    const remainingLiters = DataDecoder._calcRemainingLiters(distFromCenterValue);
    const remainingEMALiters = DataDecoder._calcRemainingEMALiters(curRemainingEMALiters, remainingLiters);
    const remainingEMAPercentage = remainingEMALiters / MAX_FUEL_CAPACITY;

    return {
      remainingLiters,
      remainingEMALiters,
      remainingEMAPercentage,
    };
  }

  // TODO need to implement CVT temp calculation
  static calculateDrivetrainData(engineRPM, secRPM, cvtThermistorReading) {
    const cvtRatio = engineRPM / secRPM;

    const speedMPH = secRPM * MAGICAL_CONSTANT_FOR_SPEED;

    return {
      engineRPM,
      secRPM,
      cvtRatio,
      speedMPH,
      cvtTemperatureCelsius: cvtThermistorReading,
    };
  }

  // TODO need to implement
  static calculateBrakesData(sensorReading1, sensorReading2) {
    return {
      frontBrakePressurePsi: sensorReading1,
      rearBrakePressurePsi: sensorReading2,
    };
  }

  // TODO need to implement
  static calculateSuspensionData(sensorReading1, sensorReading2) {
    return {
      shock1actuationInches: MAX_LIN_POT_ACTUATION_IN - (sensorReading1 / MAX_ANALOG_VALUE) * MAX_LIN_POT_ACTUATION_IN,
      shock2actuationInches: MAX_LIN_POT_ACTUATION_IN - (sensorReading2 / MAX_ANALOG_VALUE) * MAX_LIN_POT_ACTUATION_IN,
    };
  }
}