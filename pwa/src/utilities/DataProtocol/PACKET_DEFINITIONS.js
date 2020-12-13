const COMPETITION_PACKET_DEFINITION = [
  {valueName: 'fuel', bitLength: 7},
  {valueName: 'engine_rpm', bitLength: 13},
  {valueName: 'cvt_sec_rpm', bitLength: 13},
  {valueName: 'cvt_temp', bitLength: 8},
  {valueName: 'front_brake_pressure', bitLength: 11},
  {valueName: 'rear_brake_pressure', bitLength: 11},
];

const BUSCO_2020_12_PACKET_DEFINITION = [
  {valueName: 'x_accel', bitLength: 11},
  {valueName: 'y_accel', bitLength: 11},
  {valueName: 'z_accel', bitLength: 11},
  {valueName: 'fl_shock_compression', bitLength: 10},
  {valueName: 'front_brake_pressure', bitLength: 11},
];

export { COMPETITION_PACKET_DEFINITION, BUSCO_2020_12_PACKET_DEFINITION };
