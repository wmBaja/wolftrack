#include <Arduino.h>
#include <stdlib.h>
#include "defs.h"
#include "rpm.h"

// the current time (in ms)
unsigned long curTime = 0;
// the time at which the next data packet should be sent to the RPi
unsigned long nextTransmissionTime = 0;
// the next time to calculate the RPM (engine and secondary) (in ms)
unsigned long nextRPMUpdateTime = 0;
// the most recently calculated engine RPM
int engineRPM = 0;
// the most recently calculated CVT secondary RPM
int cvtSecRPM = 0;

////----------------ENGINE RPM---------------------------
// the last time that a voltage spike occurred (in ms)
unsigned long lastSpikeTime = 0;
// the total number of sparks in this update period
int numSparks = 0;

////----------------END ENGINE RPM---------------------------
// whether or not a magnet is currently passing
bool magIsPassing = false;
// the total number of magnet passes in this update period
int numMagPasses = 0;
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
