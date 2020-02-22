#include <Arduino.h>
#include <stdlib.h>
#include "defs.h"
#include "rpm.h"

////---------------TIME-------------------
// the current time (in ms)
unsigned long curTime = 0;
// the time at which the next data packet should be sent to the RPi
unsigned long nextTransmissionTime = 0;
// the next time to calculate the RPM (engine and secondary) (in ms)
unsigned long nextRPMUpdateTime = 0;

////----------------ENGINE RPM---------------------------
// the most recently calculated engine RPM
int engineRPM = 0;

////----------------CVT SEC RPM---------------------------
// the most recently calculated CVT secondary RPM
int cvtSecRPM = 0;


void setup() {
  // start serial connection
  Serial.begin(BAUD_RATE);
  
  // digital pin setup
  pinMode(ENGINE_RPM_PIN, INPUT);
  pinMode(CVT_SEC_RPM_PIN, INPUT);

  // time variable initialization
  curTime = millis();
  nextTransmissionTime = curTime + TRANSMISSION_INTERVAL;
  nextRPMUpdateTime = curTime + RPM_UPDATE_INTERVAL;
}

// REMOVE: ONLY FOR PROFILING
bool profilingDone = false;
unsigned long loopCount = 0;

void loop() {
  curTime = millis();

  // update RPMs
  checkForSparks();
  checkForMagPasses();
  updateRPMs();

  // update all sensor values
  int fuel = analogRead(FUEL_HALL_EFFECT_PIN);
  int cvtTemp = analogRead(CVT_TEMP_PIN);
  int brake1 = analogRead(BRAKE_PRESSURE_1_PIN);
  int brake2 = analogRead(BRAKE_PRESSURE_2_PIN);
  int shock1 = analogRead(SHOCK_ACTUATION_1_PIN);
  int shock2 = analogRead(SHOCK_ACTUATION_2_PIN);

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
//    Serial.write(arr, DATA_PACKET_SIZE);

    // calculate the next transmission time
    nextTransmissionTime = curTime + TRANSMISSION_INTERVAL;
  }

  // REMOVE: ONLY FOR PROFILING
  loopCount++;
  unsigned long timePassed = micros();
  if (timePassed > 5000000 && !profilingDone) {
    Serial.println("\nTime passed (microseconds): ");
    Serial.print(timePassed);
    Serial.println("\nLoop count: ");
    Serial.println(loopCount);
    profilingDone = true;
  }
}
