#ifndef _ENGINE_RPM_H
#define _ENGINE_RPM_H

#include <stdbool.h>

#include "Sensor.h"

class EngineRPM: public Sensor {
    // the digital pin that the RPM sensor is connected to
    int pin;
    // whether or not the engine is currently sparking
    bool sparking;
    // the last time that an engine spark occurred (in us)
    unsigned long lastSparkTime;
    // the number of sparks recorded during the current update interval
    int numSparks;
    // the sum of all spark intervals (in us) recorded during current the update interval
    unsigned long sparkIntervalSum;
    // the most recently calculated engine RPM
    int engineRPM;
    // the next time to calculate the RPM (in ms)
    unsigned long nextUpdateTime;
  public:
    EngineRPM();
    EngineRPM(int);
    void loop();
    int getValue();
  private:
    void checkForSparks();
    void updateRPM();
};

#endif
