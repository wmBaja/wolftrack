#ifndef _CVT_TEMPERATURE_H
#define _CVT_TEMPERATURE_H

#include <stdbool.h>
#include <OneWire.h>
#include <DallasTemperature.h>

#include "Sensor.h"

// amount of time between sensor reads
#define READ_INTERVAL 1000

class CVTTemperature: public Sensor {
    // the most recently calculated CVT temperature
    int cvtTemp;
    // Setup a oneWire instance to communicate with any OneWire devices
    OneWire oneWire;
    // Pass our oneWire reference to Dallas Temperature sensor 
    DallasTemperature sensors;
    // the time at which to read a new value from the sensor
    unsigned long nextReadTime;
  public:
    CVTTemperature();
    void loop();
    int getValue();
	int getMoreValues();
	int getDataBits();
};

#endif
