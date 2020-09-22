#include <Arduino.h>

#include "BLEModule.h"

#define BAUD_RATE 115200

#define DATA_PACKET_SIZE 250

BLEModule* bleModule = NULL;

void setup() {
  // start serial connection
  Serial.begin(BAUD_RATE);

  // initialize BLE
  bleModule = new BLEModule();
}

int count = 0;

void loop() {
  unsigned long curTime = millis();

  // build the data packet
  byte arr[DATA_PACKET_SIZE];

  for (int i = 0; i < DATA_PACKET_SIZE; i++) {
    arr[i] = (byte) count++;
  }

  // update the GATT characteristic and notify client
  bleModule->updateAndNotify((uint8_t*) arr, sizeof(arr));

  delay(10);
}
