#include <Arduino.h>
#include <stdlib.h>

//-----------------GENERAL CONSTANTS---------------
// number of milliseconds in a second
#define MILLIS_IN_SEC 1000
// number of seconds in a minute
#define SECS_IN_MIN 60
// the baud rate for the serial connection
#define BAUD_RATE 115200
// amount of time between transmissions to RPi (in ms)
#define TRANSMISSION_INTERVAL 250
// the size of the data packet sent to the RPi
#define DATA_PACKET_SIZE 18


//------------------GENERAL GLOBAL VARIABLES-------------
// the current time (in ms)
unsigned long curTime = 0;
// the time at which the next data packet should be sent to the RPi
unsigned long nextTransmissionTime = 0;


//--------------------PIN DEFINITIONS---------------------------
#define FUEL_HALL_EFFECT_PIN A0
#define ENGINE_RPM_INDUCTION_PIN A1
#define CVT_SEC_HALL_EFFECT_RPM_PIN A2
#define CVT_TEMP_PIN A3
#define BRAKE_PRESSURE_1_PIN A4
#define BRAKE_PRESSURE_2_PIN A5


//------------------RPM-----------------------------
// amount of time between RPM (engine and CVT secondary) updates (in ms)
#define RPM_UPDATE_INTERVAL 1000
// the conversion factor for revs per update to revs per minute
#define REVS_PER_UPDATE_TO_REVS_PER_MIN (SECS_IN_MIN / (RPM_UPDATE_INTERVAL / MILLIS_IN_SEC))

// the next time to calculate the RPM (engine and secondary) (in ms)
unsigned long nextRPMUpdateTime = 0;
// the most recently calculated engine RPM
int engineRPM = 0;
// the most recently calculated CVT secondary RPM
int cvtSecRPM = 0;

////----------------ENGINE RPM---------------------------
// voltage spike threshold (in terms of a range of 0-5V mapped into a 0-1023 range)
#define SPIKE_THRESHOLD 900
// the maximum amount of time between spikes (in ms)
#define MAX_SPIKE_INTERVAL 5

// the last time that a voltage spike occurred (in ms)
unsigned long lastSpikeTime = 0;
// the total number of sparks in this update period
int numSparks = 0;

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
////----------------END ENGINE RPM---------------------------

////------------------CVT SECONDARY RPM---------------
// ????
#define LOW_THRESHOLD 100
// ????
#define HIGH_THRESHOLD 120

// whether or not a magnet is currently passing
bool magIsPassing = false;
// the total number of magnet passes in this update period
int numMagPasses = 0;

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
//-------------------END RPM---------------------------------


void setup() {
  Serial.begin(BAUD_RATE);
  curTime = millis();
  nextTransmissionTime = curTime + TRANSMISSION_INTERVAL;
  nextRPMUpdateTime = curTime + RPM_UPDATE_INTERVAL;
}

void loop() {
  curTime = millis();

  checkForSpikesAndSparks();
  checkForMagnetPasses();
  updateRPMs();

  // update all sensor values
  int fuel = analogRead(FUEL_HALL_EFFECT_PIN);//random(1024);
  int cvtTemp = analogRead(CVT_TEMP_PIN);//random(1024);
  int brake1 = analogRead(BRAKE_PRESSURE_1_PIN);//random(1024);
  int brake2 = analogRead(BRAKE_PRESSURE_2_PIN);//random(1024);
  int shock1 = random(1024); // TODO need to implement
  int shock2 = random(1024); // TODO need to implement

  // if it's time to transmit
  if (curTime > nextTransmissionTime) {
    // build the data packet
    byte arr[] = {
      highByte(fuel), lowByte(fuel),           // fuel
      highByte(engineRPM), lowByte(engineRPM), // engine RPM
      highByte(cvtSecRPM), lowByte(cvtSecRPM), // CVT secondary RPM
      highByte(cvtTemp), lowByte(cvtTemp),     // CVT temperature
      highByte(brake1), lowByte(brake1),       // brake pressure 1
      highByte(brake2), lowByte(brake2),       // brake pressure 2
      highByte(shock1), lowByte(shock1),       // shock actuation 1
      highByte(shock2), lowByte(shock2),       // shock actuation 2
      255, 255                                 // end of sequence delimiter
    };

    // send the data packet
    Serial.write(arr, DATA_PACKET_SIZE);

    // calculate the next transmission time
    nextTransmissionTime = curTime + TRANSMISSION_INTERVAL;
  }
}
