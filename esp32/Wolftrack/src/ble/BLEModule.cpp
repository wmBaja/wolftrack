#include <Arduino.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

#include "BLEModule.h"
#include "../../config.h"

// NOTE: If you construct this outside of the setup() method in the main .ino
// file, then the ESP32 will continously turn off and back on.
// NOTE: C++ will automatically call the default constructor when declaring
// a global variable with a class (like BLEModule) as its type.
BLEModule::BLEModule()
{
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
      BLECharacteristic::PROPERTY_READ |
          BLECharacteristic::PROPERTY_NOTIFY);
  // Create a BLE Descriptor
  this->pCharacteristic->addDescriptor(new BLE2902());

  // Start the service
  this->pService->start();

  // Start advertising
  BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
  pAdvertising->addServiceUUID(SERVICE_UUID);
  pAdvertising->setScanResponse(false);
  pAdvertising->setMinPreferred(0x0); // set value to 0x00 to not advertise this parameter
  BLEDevice::startAdvertising();
}

void BLEModule::update(DataPacket *dataPacket)
{
  uint8_t arr[MAX_BYTES_IN_PACKET];
  size_t size = dataPacket->toByteArray(arr);
  this->pCharacteristic->setValue(arr, size);
  this->pCharacteristic->notify();
}

bool BLEModule::isDeviceConnected()
{
  return this->deviceConnected;
}

Callbacks::Callbacks(bool *deviceConnected)
{
  this->deviceConnected = deviceConnected;
}

void Callbacks::onConnect(BLEServer *pServer)
{
  *deviceConnected = true;
}

void Callbacks::onDisconnect(BLEServer *pServer)
{
  *deviceConnected = false;

  // restart advertising
  delay(500); // the bluetooth stack needs a bit of time to get things ready
  pServer->startAdvertising();
}
