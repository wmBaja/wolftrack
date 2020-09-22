#include <Arduino.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

#include "BLEModule.h"
#include "../../config.h"


// BLE device name
#define BLE_DEVICE_NAME "NCSU Wolftrack"
// BLE service UUID
#define SERVICE_UUID        "12345678-1234-5678-1234-56789abcdef0"
// BLE characteristic UUID
#define CHARACTERISTIC_UUID "12345678-1234-5678-1234-56789abcdef1"

BLEModule::BLEModule() {
  this->deviceConnected = false;

  // Create the BLE Device
  BLEDevice::init(BLE_DEVICE_NAME);
  // Create the BLE Server
  this->pServer = BLEDevice::createServer();
  this->pServer->setCallbacks(new Callbacks(&this->deviceConnected));
  // Create the BLE Service
  this->pService = this->pServer->createService(SERVICE_UUID);
  // Create a BLE Characteristic
  this->pCharacteristic = this->pService->createCharacteristic(
                      CHARACTERISTIC_UUID,
                      BLECharacteristic::PROPERTY_READ   |
                      BLECharacteristic::PROPERTY_NOTIFY
                    );
  // Create a BLE Descriptor
  this->pCharacteristic->addDescriptor(new BLE2902());

  // Start the service
  this->pService->start();

  // Start advertising
  BLEAdvertising* pAdvertising = BLEDevice::getAdvertising();
  pAdvertising->addServiceUUID(SERVICE_UUID);
  pAdvertising->setScanResponse(false);
//  pAdvertising->setMinInterval(0x06);  // set value to 0x00 to not advertise this parameter
  pAdvertising->setMinPreferred(0x06);
//  pAdvertising->setMaxInterval(0x20);
  pAdvertising->setMaxPreferred(0x20);
  BLEDevice::startAdvertising();

  BLEDevice::setMTU(460);

  Serial.println(BLEDevice::getMTU());
}

void BLEModule::updateAndNotify(uint8_t* arr, size_t size) {
  this->pCharacteristic->setValue(arr, size);
  this->pCharacteristic->notify();
}

bool BLEModule::isDeviceConnected() {
  return this->deviceConnected;
}

Callbacks::Callbacks(bool* deviceConnected) {
  this->deviceConnected = deviceConnected;
}

void Callbacks::onConnect(BLEServer* pServer) {
  *deviceConnected = true;
};

void Callbacks::onDisconnect(BLEServer* pServer) {
  *deviceConnected = false;

  // restart advertising
  delay(500); // the bluetooth stack needs a bit of time to get things ready
  pServer->startAdvertising();
}
