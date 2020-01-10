const MAX_FUEL_CAPACITY = 3.45;
const MAX_DETECTABLE_FUEL_CAPACITY = 1.6;

const NEUTRAL_MAGNETISM_VALUE = 512;
const LOWEST_MAGNETISM_VALUE = 16;
const HIGHEST_MAGNETISM_VALUE = 623;

const DEFAULT_DATA = {
  fuel: {
    remainingLiters: MAX_DETECTABLE_FUEL_CAPACITY,
    remainingEMALiters: MAX_DETECTABLE_FUEL_CAPACITY,
    remainingEMAPercentage: MAX_DETECTABLE_FUEL_CAPACITY / MAX_FUEL_CAPACITY,
  },
  drivetrain: {
    engineRPM: 0,
    cvtRPM: 0,
    cvtRatio: 0,
    speedMPH: 0,
    cvtTemperatureCelsius: 0,
  },
  brakes: {
    frontBrakePressurePsi: 0,
    rearBrakePressurePsi: 0,
  },
  suspension: {
    shock1actuationMillimeters: 0,
    shock2actuationMillimeters: 0,
  },
};

export { DEFAULT_DATA, MAX_FUEL_CAPACITY, MAX_DETECTABLE_FUEL_CAPACITY,
  NEUTRAL_MAGNETISM_VALUE, LOWEST_MAGNETISM_VALUE, HIGHEST_MAGNETISM_VALUE };
