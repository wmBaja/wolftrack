#ifndef _SHOCK_COMPRESSION_H
#define _SHOCK_COMPRESSION_H

#include <stdbool.h>

#include "Sensor.h"

class ShockCompression: public Sensor {
    // the most recently calculated shock compression
    int shockCompression;
  public:
    ShockCompression();
    void loop();
    int getValue();
};

#endif
