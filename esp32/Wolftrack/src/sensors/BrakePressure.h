#ifndef _BRAKE_PRESSURE_H
#define _BRAKE_PRESSURE_H

#include <stdbool.h>

#include "Sensor.h"

class BrakePressure: public Sensor {
    // the most recently calculated brake pressure
    int brakePressure;
  public:
    BrakePressure();
    void loop();
    int getValue();
};

#endif
