#ifndef _FUEL_H
#define _FUEL_H

#include <stdbool.h>

#include "Sensor.h"

class Fuel: public Sensor {
    // the most recently calculated fuel
    int fuel;
  public:
    Fuel();
    void loop();
    int getValue();
};

#endif
