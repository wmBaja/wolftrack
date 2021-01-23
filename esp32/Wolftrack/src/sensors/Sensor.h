#ifndef _SENSOR_H
#define _SENSOR_H

class Sensor {
  virtual void loop() = 0;
  virtual int getValue() = 0;
};

#endif
