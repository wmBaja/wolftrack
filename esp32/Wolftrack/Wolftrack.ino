#include <Arduino.h>
#include <stdlib.h>

#include "config.h"
#include "defs.h"
#include "rpm.h"

#include "src/sensors/EngineRPM.h"
#include "src/sensors/CVTSecRPM.h"

#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

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
EngineRPM engineRPMSensor = NULL;
CVTSecRPM cvtSecRPMSensor = NULL;

#define ANALOG_READ_OFFSET 25

#define FUEL_UPDATE_INTERVAL 5000
#define CVT_TEMP_UPDATE_INTERVAL 1000
#define BRAKE1_UPDATE_INTERVAL 100
#define BRAKE2_UPDATE_INTERVAL 100
#define SHOCK1_UPDATE_INTERVAL 100
#define SHOCK2_UPDATE_INTERVAL 100

int fuel = 0;
// the next time to calculate the fuel level (in ms)
unsigned long nextFuelUpdateTime = 0;
int cvtTemp = 0;
// the next time to calculate the CVT temp (in ms)
unsigned long nextCvtTempUpdateTime = 0;
int brake1 = 0;
// the next time to calculate the brake pressure 1 (in ms)
unsigned long nextBrake1UpdateTime = 0;
int brake2 = 0;
// the next time to calculate the brake pressure 2 (in ms)
unsigned long nextBrake2UpdateTime = 0;
int shock1 = 0;
// the next time to calculate the shock actuation 1 (in ms)
unsigned long nextShock1UpdateTime = 0;
int shock2 = 0;
// the next time to calculate the shock actuation 2 (in ms)
unsigned long nextShock2UpdateTime = 0;

void updateAnalogValue(int analogPin, unsigned long *nextUpdateTimePtr, int updateInterval, int *valuePtr) {
  // if it's time to update
  if (curTime > *nextUpdateTimePtr) {
    // read the value
    *valuePtr = analogRead(analogPin);
    // calculate the next update time
    *nextUpdateTimePtr = curTime + updateInterval;
  }
}

void updateAnalogValues() {
  updateAnalogValue(FUEL_HALL_EFFECT_PIN, &nextFuelUpdateTime, FUEL_UPDATE_INTERVAL, &fuel);
  updateAnalogValue(CVT_TEMP_PIN, &nextCvtTempUpdateTime, CVT_TEMP_UPDATE_INTERVAL, &cvtTemp);
  updateAnalogValue(BRAKE_PRESSURE_1_PIN, &nextBrake1UpdateTime, BRAKE1_UPDATE_INTERVAL, &brake1);
  updateAnalogValue(BRAKE_PRESSURE_2_PIN, &nextBrake2UpdateTime, BRAKE2_UPDATE_INTERVAL, &brake2);
  updateAnalogValue(SHOCK_ACTUATION_1_PIN, &nextShock1UpdateTime, SHOCK1_UPDATE_INTERVAL, &shock1);
  updateAnalogValue(SHOCK_ACTUATION_2_PIN, &nextShock2UpdateTime, SHOCK2_UPDATE_INTERVAL, &shock2);
}


void setup() {
  // start serial connection
  Serial.begin(BAUD_RATE);

  // initialize sensor classes
  engineRPMSensor = EngineRPM(ENGINE_RPM_PIN);
  cvtSecRPMSensor = CVTSecRPM(CVT_SEC_RPM_PIN);

  // time variable initialization
  curTime = millis();
  nextTransmissionTime = curTime + TRANSMISSION_INTERVAL;

  nextFuelUpdateTime = curTime + FUEL_UPDATE_INTERVAL;
  nextCvtTempUpdateTime = curTime + CVT_TEMP_UPDATE_INTERVAL + ANALOG_READ_OFFSET;
  nextBrake1UpdateTime = curTime + BRAKE1_UPDATE_INTERVAL + ANALOG_READ_OFFSET * 2;
  nextBrake2UpdateTime = curTime + BRAKE2_UPDATE_INTERVAL + ANALOG_READ_OFFSET * 3;
  nextShock1UpdateTime = curTime + SHOCK1_UPDATE_INTERVAL + ANALOG_READ_OFFSET * 4;
  nextShock2UpdateTime = curTime + SHOCK2_UPDATE_INTERVAL + ANALOG_READ_OFFSET * 5;


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
  // engineRPMSensor.loop()
  // cvtSecRPMSensor.loop()

  // // update analog values
  // updateAnalogValues();

  fuel = random(1024);
  int engineRPM = random(1000, 4000);
  int cvtSecRPM = engineRPM / (random(26) / 10.0 * 0.9);
  cvtTemp = random(1024);
  brake1 = random(1024);
  brake2 = random(1024);
  shock1 = random(1024);
  shock2 = random(1024);

  // if it's time to transmit and there's a BLE connection
  if (curTime > nextTransmissionTime && deviceConnected) {
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
