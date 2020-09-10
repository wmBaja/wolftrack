#include "rpm.h"

////ENGINE RPM
// whether or not the engine is currently sparking
bool sparking = false;
// the last time that an engine spark occurred (in us)
unsigned long lastSparkTime = 0;
// the number of sparks recorded during the current update interval
int numSparks = 0;
// the sum of all spark intervals (in us) recorded during current the update interval
unsigned long sparkIntervalSum = 0;

/**
 * Checks whether or not the engine is sparking;
 */
void checkForSparks() {
  int pinState = digitalRead(ENGINE_RPM_PIN);

  // if the pin is high
  if (pinState) {
    // if the engine is not considered sparking
    if (!sparking) {
      // then this is a new spark
      numSparks++;
      // and now we need to consider the engine as sparking
      sparking = true;

      // get the current time
      unsigned long curTimeMicros = micros();
      // add the last spark interval to the sum
      sparkIntervalSum += curTimeMicros - lastSparkTime;
      // update the last spark time to be this time
      lastSparkTime = curTimeMicros;
    }
  } else { // else the pin is low
    // thus the engine is not sparking
    sparking = false;
  }
}


////CVT SEC RPM
// whether or not the shaft's magnet is currently passing
bool magIsPassing = false;
// the last time that a magnet pass occurred (in us)
unsigned long lastMagPassTime = 0;
// the number of magnet passes recorded during the current update interval
int numMagPasses = 0;
// the sum of all magnet pass intervals (in us) recorded during current the update interval
unsigned long magPassIntervalSum = 0;

/**
 * Checks whether or not the shaft's magnet is passing;
 */
void checkForMagPasses() {
  int pinState = digitalRead(CVT_SEC_RPM_PIN);

  // if the pin is high
  if (pinState) {
    // if the shaft's magnet is not currently considered passing
    if (!magIsPassing) {
      // then this is a new magnet pass
      numMagPasses++;
      // and now we need to consider the shaft's magnet as passing
      magIsPassing = true;

      // get the current time
      unsigned long curTimeMicros = micros();
      // add the last magnet pass interval to the sum
      magPassIntervalSum += curTimeMicros - lastMagPassTime;
      // update the last magnet pass time to be this time
      lastMagPassTime = curTimeMicros;
    }
  } else { // else the pin is low
    // thus the shaft's magnet is not passing
    magIsPassing = false;
  }
}

/**
 * Updates the engine and CVT secondary RPMs;
 */
void updateRPMs() {
  // if it's time to update the RPMs
  if (curTime > nextRPMUpdateTime) {
    //////UPDATE ENGINE RPM
    if (numSparks > 0) {
      // calculate the average spark interval
      unsigned long avgSparkInterval = sparkIntervalSum / numSparks; // could increase accuracy by using floating point ops
  
      // calculate the engine RPM based on the average spark interval
      engineRPM = MICROS_IN_MIN / avgSparkInterval; // could increase accuracy by using floating point ops
    }
    // reset the number of sparks and spark interval sum
    numSparks = 0;
    sparkIntervalSum = 0;
    
    /////////UPDATE CVT SEC RPM
    if (numMagPasses > 0) {
      // calculate the average magnet pass interval
      unsigned long avgMagPassInterval = magPassIntervalSum / numMagPasses; // could increase accuracy by using floating point ops
  
      // calculate the CVT secondary RPM based on the average magnet pass interval
      cvtSecRPM = MICROS_IN_MIN / avgMagPassInterval; // could increase accuracy by using floating point ops
    }
    
    // reset the number of magnet passes and magnet pass interval sum
    numMagPasses = 0;
    magPassIntervalSum = 0;

    ///////CALC NEXT RPM UPDATE TIME
    // calculate the next update time
    nextRPMUpdateTime = curTime + RPM_UPDATE_INTERVAL;
  }
}
