#ifndef _BRAKE_PRESSURE_H
#define _BRAKE_PRESSURE_H

#include <stdbool.h>
#include <MCP3XXX.h>

#include "Sensor.h"

// amount of time between sensor reads
#define READ_INTERVAL 10

class BrakePressure: public Sensor {
    MCP3008* adc;
    uint8_t adcChannel;
    // the most recently calculated brake pressure
    int brakePressure;
    // the time at which to read a new value from the sensor
    unsigned long nextReadTime;
  public:
    BrakePressure(MCP3008*, uint8_t);
    void loop();
    int getValue();
};

#endif
