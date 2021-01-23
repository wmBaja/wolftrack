// all of the possible settings
const POSSIBLE_SETTINGS = {
  driverDisplay: {
    base: ['PURE_INFO', 'OVERHEAD_VEHICLE_GRAPHIC', 'MAP'],
    'PURE_INFO': {
      displayedValues: [
        'PERCENT_FUEL', 'LITERS_FUEL', 'SPEED', 'ENGINE_RPM', 'SEC_RPM', 'CVT_RATIO',
        'CVT_TEMPERATURE', 'ACCELERATION_X', 'ACCELERATION_Y', 'ACCELERATION_Z', 'SHOCK_ACTUATION_1', 'SHOCK_ACTUATION_2',
        'FRONT_BRAKE_PRESSURE', 'REAR_BRAKE_PRESSURE'
      ],
    },
    'OVERHEAD_VEHICLE_GRAPHIC': {
      displayedValues: [
        'PERCENT_FUEL', 'SPEED', 'CVT_TEMPERATURE', 'ACCELERATION',
        'SHOCK_ACTUATION_1', 'SHOCK_ACTUATION_2', 'FRONT_BRAKE_PRESSURE',
        'REAR_BRAKE_PRESSURE'
      ],
    },
    'MAP': {
      displayedValues: ['PERCENT_FUEL', 'SPEED'],
    },
  },
};

// the default settings
const DEFAULT_SETTINGS = {
  driverDisplay: {
    base: 'PURE_INFO',
    'PURE_INFO': {
      displayedValues: ['ENGINE_RPM', 'SPEED',  'SEC_RPM', 'CVT_RATIO'],
    },
    'OVERHEAD_VEHICLE_GRAPHIC': {
      displayedValues: ['PERCENT_FUEL', 'SPEED', 'ACCELERATION'],
    },
    'MAP': {
      displayedValues: ['PERCENT_FUEL', 'SPEED'],
    },
  },
};

export { POSSIBLE_SETTINGS, DEFAULT_SETTINGS };
