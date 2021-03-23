export default class SensorProfile {
  sensors = [
    {valueName: 'x_accel', bitLength: 11, running: false},
    {valueName: 'y_accel', bitLength: 11, running: false},
    {valueName: 'z_accel', bitLength: 11, running: false},
    {valueName: 'fl_shock_compression', bitLength: 10, running: false},
    {valueName: 'front_brake_pressure', bitLength: 11, running: false},
    {valueName: 'engine_rpm', bitLength: 13, running: false},
    {valueName: 'fuel', bitLength: 7, running: false},
    {valueName: 'cvt_temperature', bitLength: 8, running: false},
    {valueName: 'cvt_sec_rpm', bitLength: 13, running: false},
  ];
  seralize = () => {
    let binString = "";
    this.sensors.forEach(element => {
      if(element.running){
        binString.concat("1");
      } else {
        binString.concat("0");
      }
    });
    return binString;
  }

}