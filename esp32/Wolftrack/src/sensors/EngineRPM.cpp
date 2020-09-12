#include <Arduino.h>

#include "EngineRPM.h"
#include "../../defs.h"

// amount of time between RPM updates (in ms)
#define RPM_UPDATE_INTERVAL 1000

EngineRPM::EngineRPM(int pin) {
  pinMode(pin, INPUT);
  this->pin = pin;
  this->sparking = false;
  this->lastSparkTime = 0;
  this->numSparks = 0;
  this->sparkIntervalSum = 0;
  this->engineRPM = 0;
  this->nextUpdateTime = 0;
}

/**
 * Checks whether or not the engine is sparking;
 */
void EngineRPM::checkForSparks() {
  int pinState = digitalRead(this->pin);

  // if the pin is high
  if (pinState) {
    // if the engine is not considered sparking
    if (!this->sparking) {
      // then this is a new spark
      this->numSparks++;
      // and now we need to consider the engine as sparking
      this->sparking = true;

      // get the current time
      unsigned long curTimeMicros = micros();
      // add the last spark interval to the sum
      this->sparkIntervalSum += curTimeMicros - this->lastSparkTime;
      // update the last spark time to be this time
      this->lastSparkTime = curTimeMicros;
    }
  } else { // else the pin is low
    // thus the engine is not sparking
    this->sparking = false;
  }
}

/**
 * Updates the engine RPM;
 */
void EngineRPM::updateRPM() {
  // if it's time to update the RPM
  if (curTime > this->nextUpdateTime) {
    if (this->numSparks > 0) { // if there have been sparks
      // calculate the average spark interval
      unsigned long avgSparkInterval = this->sparkIntervalSum / this->numSparks; // could increase accuracy by using floating point ops

      // calculate the engine RPM based on the average spark interval
      this->engineRPM = MICROS_IN_MIN / avgSparkInterval; // could increase accuracy by using floating point ops
    }
    // reset the number of sparks and spark interval sum
    this->numSparks = 0;
    this->sparkIntervalSum = 0;

    // calculate the next update time
    this->nextUpdateTime = curTime + RPM_UPDATE_INTERVAL;
  }
}

void EngineRPM::loop() {
  this->checkForSparks();
  this->updateRPM();
}

int EngineRPM::getValue() {
  return this->engineRPM;
}
