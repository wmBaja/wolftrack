#include <Arduino.h>
#include <stdlib.h>
#include <stdbool.h>

#include "config.h"
#include "src/ble/BLEModule.h"
#include "src/sd/SDModule.h"
#include "src/sensors/sensor_groups/SensorGroup.h"
#include "src/sensors/sensor_groups/Busco2020_12SensorGroup.h"


////---------------BLE--------------------
BLEModule* bleModule;
// the time at which the next data packet should be sent over BLE
unsigned long nextTransmissionTime = 0;

////---------------SD---------------------
SDModule* sdModule;
// the time at which the next data packet should be written to the SD card
unsigned long nextSDWriteTime = 0;

////---------------SENSORS----------------
SensorGroup* sensorGroup;

void setup() {

#if TESTING
  // start serial connection
  Serial.begin(BAUD_RATE);
  Serial.println("Starting testing...");
#endif

  // initialize sensor group
  sensorGroup = new Busco2020_12SensorGroup();

  // initialize first transmission time
  nextTransmissionTime = millis() + TRANSMISSION_INTERVAL;

  // initialize BLE
  bleModule = new BLEModule();

  // initialize SD
  sdModule = new SDModule();
}

#if ENABLE_PERFORMANCE_PROFILING
#define PROFILING_REPORT_INTERVAL 5000000
unsigned long nextProfilingReportTime = PROFILING_REPORT_INTERVAL;
unsigned long loopCount = 0;
#endif

void loop() {
  unsigned long curTime = millis();
  DataPacket dataPacket;

  // run sensor code
  sensorGroup->loop();

  // if it's time to transmit and there's a BLE connection
  if (curTime > nextTransmissionTime && bleModule->isDeviceConnected()) {
    // build the data packet
    sensorGroup->buildDataPacket(&dataPacket);

    // update the GATT characteristic and notify client
    bleModule->update(&dataPacket);

    // calculate the next transmission time
    nextTransmissionTime = curTime + TRANSMISSION_INTERVAL;
  }

  // if it's time to write to the SD card and a card is connnected
  if (curTime > nextSDWriteTime && sdModule->isCardConnected()) {
    // build the data packet
    sensorGroup->buildDataPacket(&dataPacket);

    // buffer the write to the SD card
    sdModule->write(&dataPacket);

    nextSDWriteTime = curTime + SD_WRITE_INTERVAL;
  }

#if ENABLE_PERFORMANCE_PROFILING
  loopCount++;
  unsigned long curMicroTime = micros();
  if (curMicroTime > nextProfilingReportTime) {
    unsigned long timePassed = curMicroTime - nextProfilingReportTime + PROFILING_REPORT_INTERVAL;
    Serial.println("\nTime passed (microseconds): ");
    Serial.print(timePassed);
    Serial.println("\nLoop count: ");
    Serial.print(loopCount);
    Serial.println("\nLoops per second: ");
    Serial.println((int) (loopCount / (timePassed / 1000000.0)));

    loopCount = 0;
    nextProfilingReportTime = curMicroTime + PROFILING_REPORT_INTERVAL;
  }
#endif
}
