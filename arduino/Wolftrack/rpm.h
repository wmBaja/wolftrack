#include <Arduino.h>
#include <stdbool.h>

#include "defs.h"


//------------------ALL RPM CONSTANTS-----------------------
// amount of time between RPM (engine and CVT secondary) updates (in ms)
#define RPM_UPDATE_INTERVAL 1000
// the conversion factor for revs per update to revs per minute
#define REVS_PER_UPDATE_TO_REVS_PER_MIN (SECS_IN_MIN / (RPM_UPDATE_INTERVAL / MILLIS_IN_SEC))

//-------------------ALL RPM GLOBALS---------------------
// the next time to calculate the RPM (engine and secondary) (in ms)
extern unsigned long nextRPMUpdateTime;
// the most recently calculated engine RPM
extern int engineRPM;
// the most recently calculated CVT secondary RPM
extern int cvtSecRPM;

//-----------------ENGINE RPM CONSTANTS------------------------------------
// voltage spike threshold (in terms of a range of 0-5V mapped into a 0-1023 range)
#define SPIKE_THRESHOLD 900
// the maximum amount of time between spikes (in ms)
#define MAX_SPIKE_INTERVAL 5

//----------------ENGINE RPM GLOBALS---------------
// the last time that a voltage spike occurred (in ms)
extern unsigned long lastSpikeTime;
// the total number of sparks in this update period
extern int numSparks;

////------------------CVT SECONDARY RPM---------------
// ????
#define LOW_THRESHOLD 100
// ????
#define HIGH_THRESHOLD 120

extern bool magIsPassing;

extern int numMagPasses;

/**
 * Checks for voltage spikes indicating engine sparks
 */
void checkForSpikesAndSparks();

void checkForMagnetPasses();

void updateRPMs();

