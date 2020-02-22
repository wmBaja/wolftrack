#include <Arduino.h>
#include <stdbool.h>

#include "defs.h"

// amount of time between RPM (engine and CVT secondary) updates (in ms)
#define RPM_UPDATE_INTERVAL 1000

// the next time to calculate the RPM (engine and secondary) (in ms)
extern unsigned long nextRPMUpdateTime;


////----------------ENGINE RPM GLOBALS---------------
// the most recently calculated engine RPM
extern int engineRPM;
// whether or not the engine is currently sparking
extern bool sparking;
// the last time that an engine spark occurred (in us)
extern unsigned long lastSparkTime;
// the number of sparks recorded during the current update interval
extern int numSparks;
// the sum of all spark intervals (in us) recorded during current the update interval
extern unsigned long sparkIntervalSum;


////----------------CVT SECONDARY RPM GLOBALS---------------
// the most recently calculated CVT secondary RPM
extern int cvtSecRPM;
// whether or not the shaft's magnet is currently passing
extern bool magIsPassing;
// the last time that a magnet pass occurred (in us)
extern unsigned long lastMagPassTime;
// the number of magnet passes recorded during the current update interval
extern int numMagPasses;
// the sum of all magnet pass intervals (in us) recorded during current the update interval
extern unsigned long magPassIntervalSum;

/**
 * Checks for engine sparks for measuring engine RPM;
 */
void checkForSparks();

/**
 * Checks for magnet passes for measuring CVT secondary RPM;
 */
void checkForMagPasses();

/**
 * Updates both engine and CVT secondary RPMs;
 */
void updateRPMs();
