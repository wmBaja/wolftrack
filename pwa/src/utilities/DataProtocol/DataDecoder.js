import { MAX_ANALOG_VALUE, MAX_FUEL_CAPACITY, MAGICAL_CONSTANT_FOR_SPEED,
  MAX_LIN_POT_ACTUATION_IN } from './DEFAULT_DATA.js';

import { BUSCO_2020_12_PACKET_DEFINITION } from './PACKET_DEFINITIONS.js';
import { ACCEL_REAL_START, ACCEL_INT_START, ACCEL_REAL_INT_RATIO } from './REAL_INT_RANGE_MAPPINGS.js';
import { mapRangeToRangeWithRatio } from '../utils.js';

const FUEL_EMA_WEIGHT = 0.1;

const BIT_MASKS = [
  0b11111111, 0b01111111, 0b00111111, 0b00011111,
  0b00001111, 0b00000111, 0b00000011, 0b00000001
];

/**
 * Converts a buffer into hex values.
 * @param {*} buffer the buffer to convert to hex
 * @return {string} hex values as a string
 */
// function bufToHex(buffer) {
//   return [...new Uint8Array(buffer)]
//       .map(b => b.toString(16).padStart(2, '0'))
//       .join(' ');
// }

export default class DataDecoder {
  static extractSensorReadings(byteArray, packetDefinition) {
    const values = {};
  
    let bitOffset = 0;
    for (let {valueName, bitLength} of packetDefinition) {
      let value = 0;

      // extract the bits for this value from the byte array
      let bitsLeftToExtract = bitLength;
      let curByteIdx = Math.floor(bitOffset / 8);
      let nextBitInCurByteToExtractIdx = bitOffset % 8;
      while (bitsLeftToExtract > 0) {
        const numBitsToExtractFromCurByte = Math.min(8 - nextBitInCurByteToExtractIdx, bitsLeftToExtract);
        // pull the needed bits out of the current byte
        const curByte = byteArray[curByteIdx];
        let extractedBits = curByte & BIT_MASKS[nextBitInCurByteToExtractIdx];
        // shift out any extra bits that weren't needed on the least significant side
        extractedBits = extractedBits >>> (8 - (nextBitInCurByteToExtractIdx + numBitsToExtractFromCurByte));
        // shift the value left to fit the new bits
        value = value << numBitsToExtractFromCurByte;
        // OR in the new bits
        value = value | extractedBits;
        // decrement the bits left to extract
        bitsLeftToExtract -= numBitsToExtractFromCurByte;
        // then go to the next byte
        curByteIdx++;
        nextBitInCurByteToExtractIdx = 0;
      }

      values[valueName] = value; // add the value to the dict of values
      bitOffset += bitLength; // update the bit offset into the byte array
    }
    return values;
  }

  static decodeData(rawData, currentData, rawDataBufferByteOffset, rawDataBufferLength) {
    const byteArray = new Uint8Array(rawData.buffer, rawDataBufferByteOffset, rawDataBufferLength);

    const sensors = DataDecoder.extractSensorReadings(byteArray, BUSCO_2020_12_PACKET_DEFINITION);

    return {
      rawData,
      fuel: DataDecoder.calculateFuelData(sensors.fuel, currentData),
      drivetrain: DataDecoder.calculateDrivetrainData(sensors.engine_rpm, sensors.cvt_sec_rpm, sensors.cvt_temp),
      brakes: DataDecoder.calculateBrakesData(sensors.front_brake_pressure, sensors.rear_brake_pressure),
      suspension: DataDecoder.calculateSuspensionData(
        sensors.fl_shock_compression, sensors.fr_shock_compression,
        sensors.rl_shock_compression, sensors.rr_shock_compression
      ),
      acceleration: DataDecoder.calculateAccelerationData(sensors),
    };
  }

  static calculateFuelData(sensorReading, curData) {
    let curRemainingEMALiters = 0;
    if (curData && curData.fuel) {
      curRemainingEMALiters = curData.fuel.remainingEMALiters;
    }

    const remainingLiters = sensorReading / 100 * MAX_FUEL_CAPACITY;
    const remainingEMALiters = FUEL_EMA_WEIGHT * remainingLiters + (1 - FUEL_EMA_WEIGHT) * curRemainingEMALiters;
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

  static calculateAccelerationData(sensors) {
    const data = {};
    if (!isNaN(sensors.x_accel)) {
      data.xAccelms2 = mapRangeToRangeWithRatio(ACCEL_INT_START, ACCEL_REAL_START, ACCEL_REAL_INT_RATIO, sensors.x_accel);
    }
    if (!isNaN(sensors.y_accel)) {
      data.yAccelms2 = mapRangeToRangeWithRatio(ACCEL_INT_START, ACCEL_REAL_START, ACCEL_REAL_INT_RATIO, sensors.y_accel);
    }
    if (!isNaN(sensors.z_accel)) {
      data.zAccelms2 = mapRangeToRangeWithRatio(ACCEL_INT_START, ACCEL_REAL_START, ACCEL_REAL_INT_RATIO, sensors.z_accel);
    }
    return data;
  }
}