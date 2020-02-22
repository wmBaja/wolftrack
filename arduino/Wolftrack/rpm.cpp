#include "rpm.h"

void checkForSpikesAndSparks() {
  int sensorValue = analogRead(ENGINE_RPM_INDUCTION_PIN);
  // determine if there is currently a voltage spike
  bool isSpiking = sensorValue > SPIKE_THRESHOLD;

  // if a voltage spike is detected
  if (isSpiking) {
    // if the last spike occurred over MAX_SPIKE_INTERVAL milliseconds ago
    if (curTime > lastSpikeTime + MAX_SPIKE_INTERVAL) {
      // then a new spark is starting
      numSparks++;
    }
    // this time is the new last spike time
    lastSpikeTime = curTime;
  }
}

void checkForMagnetPasses() {
  int sensorValue = analogRead(CVT_SEC_HALL_EFFECT_RPM_PIN);
  // if the value is outside of the "normal" thresholds
  if (sensorValue < LOW_THRESHOLD || sensorValue > HIGH_THRESHOLD) {
    // if the magnet is not considered passing right now
    if (!magIsPassing) {
      // then this is a new magnet pass
      numMagPasses++;
      // now the magnet is passing
      magIsPassing = true;
    }
  } else { // else the value is in within the "normal" thresholds
    // thus the magnet is not passing
    magIsPassing = false;
  }
}

////------------------END CVT SECONDARY RPM---------------

void updateRPMs() {
  // if it's time to update the RPMs
  if (curTime > nextRPMUpdateTime) {
    // calculate the engine RPM from the num sparks in this update period
    engineRPM = numSparks * REVS_PER_UPDATE_TO_REVS_PER_MIN;
    // reset the number of sparks
    numSparks = 0;

    // calculate the secondary RPM from the num magnet passes in this update period
    cvtSecRPM = numMagPasses * REVS_PER_UPDATE_TO_REVS_PER_MIN;
    // reset the number of magnet passes
    numMagPasses = 0;

    // calculate the next update time
    nextRPMUpdateTime = curTime + RPM_UPDATE_INTERVAL;
  }
}
