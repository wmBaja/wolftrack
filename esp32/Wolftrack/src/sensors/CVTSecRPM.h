#ifndef _CVT_SEC_RPM_H
#define _CVT_SEC_RPM_H

#include <stdbool.h>

#include "Sensor.h"

class CVTSecRPM : public Sensor
{
  // the digital pin that the RPM sensor is connected to
  int pin;
  // whether or not the shaft's magnet is currently passing
  bool magIsPassing = false;
  // the last time that a magnet pass occurred (in us)
  unsigned long lastMagPassTime = 0;
  // the number of magnet passes recorded during the current update interval
  int numMagPasses = 0;
  // the sum of all magnet pass intervals (in us) recorded during current the update interval
  unsigned long magPassIntervalSum = 0;
  // the most recently calculated CVT secondary RPM
  int cvtSecRPM;
  // the next time to calculate the RPM (in ms)
  unsigned long nextUpdateTime;

public:
  CVTSecRPM();
  CVTSecRPM(int);
  void loop();
  int getValue();

private:
  void checkForMagPasses();
  void updateRPM();
};

#endif
