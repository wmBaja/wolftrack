#include <Arduino.h>
#include <stdlib.h>
#include <stdbool.h>

#include "config.h"
#include "src/ble/BLEModule.h"
#include "src/sensors/EngineRPM.h"
#include "src/sensors/CVTSecRPM.h"

// the time at which the next data packet should be sent to the RPi
unsigned long nextTransmissionTime = 0;

////---------------BLE--------------------
BLEModule* bleModule = NULL;

////---------------SENSORS----------------
EngineRPM* engineRPMSensor = NULL;
CVTSecRPM* cvtSecRPMSensor = NULL;

void setup() {
  // start serial connection
  Serial.begin(BAUD_RATE);

  // initialize sensor classes
  engineRPMSensor = new EngineRPM(ENGINE_RPM_PIN);
  cvtSecRPMSensor = new CVTSecRPM(CVT_SEC_RPM_PIN);

  // initialize first transmission time
  nextTransmissionTime = millis() + TRANSMISSION_INTERVAL;

  // initialize BLE
  bleModule = new BLEModule();
}

#if _ENABLE_PERFORMANCE_PROFILING
bool profilingDone = false;
unsigned long loopCount = 0;
#endif

void loop() {
  unsigned long curTime = millis();

  // call the loop() method for each sensor
  // engineRPMSensor->loop()
  // cvtSecRPMSensor->loop()

  // if it's time to transmit and there's a BLE connection
  if (curTime > nextTransmissionTime && bleModule->isDeviceConnected()) {
    // get sensor values
    // int engineRPM = engineRPMSensor->getValue();
    // int cvtSecRPM = cvtSecRPMSensor->getValue();
    int fuel = random(1024);
    int engineRPM = random(1000, 4000);
    int cvtSecRPM = engineRPM / (random(26) / 10.0 * 0.9);
    int cvtTemp = random(1024);
    int brake1 = random(1024);
    int brake2 = random(1024);
    int shock1 = random(1024);
    int shock2 = random(1024);

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
    };

    // update the GATT characteristic and notify client
    bleModule->updateAndNotify((uint8_t*) arr, sizeof(arr));

    // calculate the next transmission time
    nextTransmissionTime = curTime + TRANSMISSION_INTERVAL;
  }

#if _ENABLE_PERFORMANCE_PROFILING
  loopCount++;
  unsigned long timePassed = micros();
  if (timePassed > 5000000 && !profilingDone) {
    Serial.println("\nTime passed (microseconds): ");
    Serial.print(timePassed);
    Serial.println("\nLoop count: ");
    Serial.print(loopCount);
    Serial.println("\nLoops per second: ");
    Serial.println(loopCount / (timePassed / 1000000));
    profilingDone = true;
  }
#endif
}
