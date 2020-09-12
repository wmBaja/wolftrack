#include <Arduino.h>
#include <stdlib.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

#include "config.h"
#include "defs.h"
#include "src/sensors/EngineRPM.h"
#include "src/sensors/CVTSecRPM.h"


////---------------BLE------------
BLEServer* pServer = NULL;
BLECharacteristic* pCharacteristic = NULL;
bool deviceConnected = false;

#define SERVICE_UUID        "12345678-1234-5678-1234-56789abcdef0"
#define CHARACTERISTIC_UUID "12345678-1234-5678-1234-56789abcdef1"

class MyServerCallbacks: public BLEServerCallbacks {
  void onConnect(BLEServer* pServer) {
    deviceConnected = true;
  };

  void onDisconnect(BLEServer* pServer) {
    deviceConnected = false;

    // restart advertising
    delay(500); // the bluetooth stack needs a bit of time to get things ready
    pServer->startAdvertising();
  }
};

////---------------TIME-------------------
// the current time (in ms)
unsigned long curTime = 0;
// the time at which the next data packet should be sent to the RPi
unsigned long nextTransmissionTime = 0;

////---------------SENSORS----------------
EngineRPM* engineRPMSensor = NULL;
CVTSecRPM* cvtSecRPMSensor = NULL;

void setup() {
  // start serial connection
  Serial.begin(BAUD_RATE);

  // initialize sensor classes
  engineRPMSensor = new EngineRPM(ENGINE_RPM_PIN);
  cvtSecRPMSensor = new CVTSecRPM(CVT_SEC_RPM_PIN);

  // time variable initialization
  curTime = millis();
  nextTransmissionTime = curTime + TRANSMISSION_INTERVAL;

  // BLE Stuff
  // Create the BLE Device
  BLEDevice::init("NCSU Wolftrack");

  // Create the BLE Server
  pServer = BLEDevice::createServer();
  pServer->setCallbacks(new MyServerCallbacks());

  // Create the BLE Service
  BLEService *pService = pServer->createService(SERVICE_UUID);

  // Create a BLE Characteristic
  pCharacteristic = pService->createCharacteristic(
                      CHARACTERISTIC_UUID,
                      BLECharacteristic::PROPERTY_READ   |
                      BLECharacteristic::PROPERTY_NOTIFY
                    );

  // Create a BLE Descriptor
  pCharacteristic->addDescriptor(new BLE2902());

  // Start the service
  pService->start();

  // Start advertising
  BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
  pAdvertising->addServiceUUID(SERVICE_UUID);
  pAdvertising->setScanResponse(false);
  pAdvertising->setMinPreferred(0x0);  // set value to 0x00 to not advertise this parameter
  BLEDevice::startAdvertising();

}

#if _ENABLE_PERFORMANCE_PROFILING
bool profilingDone = false;
unsigned long loopCount = 0;
#endif

void loop() {
  curTime = millis();

  // call the loop() method for each sensor
  // engineRPMSensor->loop()
  // cvtSecRPMSensor->loop()

  // if it's time to transmit and there's a BLE connection
  if (curTime > nextTransmissionTime && deviceConnected) {
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
    pCharacteristic->setValue((uint8_t*) arr, sizeof(arr));
    pCharacteristic->notify();

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
