#ifndef _CVT_TEMPERATURE_H
#define _CVT_TEMPERATURE_H

#include <stdbool.h>

#include "Sensor.h"

class CVTTemperature: public Sensor {
    // the most recently calculated CVT temperature
    int cvtTemp;
  public:
    CVTTemperature();
    void loop();
    int getValue();
};

#endif
