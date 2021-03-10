#ifndef _STRAIN_GAUGE_H
#define _STRAIN_GAUGE_H

#include <stdbool.h>
#include "HX711.h"

#include "Sensor.h"

// amount of time between sensor reads
#define READ_INTERVAL 10

class StrainGauge_HX711: public Sensor {
    HX711 gauge;
    // the most recently calculated strain gauge reading
    int gaugeReading;
    uint8_t dataPin;
    uint8_t clockPin;
    int calibrationFactor;
    // the time at which to read a new value from the sensor
    unsigned long nextReadTime;
  public:
    StrainGauge_HX711(uint8_t, uint8_t, int);
    void loop();
    int getValue();
};

#endif
