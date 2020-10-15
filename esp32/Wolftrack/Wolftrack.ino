#include <Arduino.h>
#include <stdlib.h>
#include <stdbool.h>

#include "config.h"
#include "src/ble/BLEModule.h"
#include "src/sensors/sensor_groups/SensorGroup.h"
#include "src/sensors/sensor_groups/CompetitionSensorGroup.h"

// the time at which the next data packet should be sent to the RPi
unsigned long nextTransmissionTime = 0;

////---------------BLE--------------------
BLEModule bleModule;

////---------------SENSORS----------------
SensorGroup* sensorGroup;

void setup() {
  // start serial connection
  Serial.begin(BAUD_RATE);

  // initialize sensor group
  sensorGroup = new CompetitionSensorGroup();

  // initialize first transmission time
  nextTransmissionTime = millis() + TRANSMISSION_INTERVAL;

  // initialize BLE
  bleModule = BLEModule();
}

#if _ENABLE_PERFORMANCE_PROFILING
#define PROFILING_REPORT_INTERVAL 5000000
unsigned long nextProfilingReportTime = PROFILING_REPORT_INTERVAL;
unsigned long loopCount = 0;
#endif

void loop() {
  unsigned long curTime = millis();

  // call the loop() method for each sensor
  sensorGroup->loop();

  // if it's time to transmit and there's a BLE connection
  if (curTime > nextTransmissionTime && bleModule.isDeviceConnected()) {
    // build the data packet
    DataPacket dataPacket;
    sensorGroup->buildDataPacket(&dataPacket);

    // update the GATT characteristic and notify client
    bleModule.update(&dataPacket);

    // calculate the next transmission time
    nextTransmissionTime = curTime + TRANSMISSION_INTERVAL;
  }

#if _ENABLE_PERFORMANCE_PROFILING
  loopCount++;
  unsigned long curMicroTime = micros();
  if (curMicroTime > nextProfilingReportTime) {
    unsigned long timePassed = curMicroTime - nextProfilingReportTime;
    Serial.println("\nTime passed (microseconds): ");
    Serial.print(timePassed);
    Serial.println("\nLoop count: ");
    Serial.print(loopCount);
    Serial.println("\nLoops per second: ");
    Serial.println(loopCount / (timePassed / 1000000));

    loopCount = 0;
    nextProfilingReportTime = curMicroTime + PROFILING_REPORT_INTERVAL;
  }
#endif
}
