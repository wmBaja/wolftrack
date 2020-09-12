#include <Arduino.h>

#include "CVTSecRPM.h"
#include "../../config.h"

// amount of time between RPM updates (in ms)
#define RPM_UPDATE_INTERVAL 1000

CVTSecRPM::CVTSecRPM(int pin) {
  pinMode(pin, INPUT);
  this->pin = pin;
  this->magIsPassing = false;
  this->lastMagPassTime = 0;
  this->numMagPasses = 0;
  this->magPassIntervalSum = 0;
  this->cvtSecRPM = 0;
  this->nextUpdateTime = 0;
}

/**
 * Checks whether or not the shaft's magnet is passing;
 */
void CVTSecRPM::checkForMagPasses() {
  int pinState = digitalRead(CVT_SEC_RPM_PIN);

  // if the pin is high
  if (pinState) {
    // if the shaft's magnet is not currently considered passing
    if (!this->magIsPassing) {
      // then this is a new magnet pass
      this->numMagPasses++;
      // and now we need to consider the shaft's magnet as passing
      this->magIsPassing = true;

      // get the current time
      unsigned long curTimeMicros = micros();
      // add the last magnet pass interval to the sum
      this->magPassIntervalSum += curTimeMicros - this->lastMagPassTime;
      // update the last magnet pass time to be this time
      this->lastMagPassTime = curTimeMicros;
    }
  } else { // else the pin is low
    // thus the shaft's magnet is not passing
    this->magIsPassing = false;
  }
}

/**
 * Updates the CVT secondary RPM;
 */
void CVTSecRPM::updateRPM() {
  unsigned long curTime = millis();

  // if it's time to update the RPM
  if (curTime > this->nextUpdateTime) {
    if (this->numMagPasses > 0) { // if there have been sparks
      // calculate the average magnet pass interval
      unsigned long avgMagPassInterval = this->magPassIntervalSum / this->numMagPasses; // could increase accuracy by using floating point ops

      // calculate the CVT secondary RPM based on the average magnet pass interval
      this->cvtSecRPM = MICROS_IN_MIN / avgMagPassInterval; // could increase accuracy by using floating point ops
    }
    // reset the number of magnet passes and magnet pass interval sum
    this->numMagPasses = 0;
    this->magPassIntervalSum = 0;

    // calculate the next update time
    this->nextUpdateTime = curTime + RPM_UPDATE_INTERVAL;
  }
}

void CVTSecRPM::loop() {
  this->checkForMagPasses();
  this->updateRPM();
}

int CVTSecRPM::getValue() {
  return this->cvtSecRPM;
}
