#include <Arduino.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>
#include <bitset>

#include "BLEModule.h"
#include "../../config.h"

// NOTE: If you construct this outside of the setup() method in the main .ino
// file, then the ESP32 will continously turn off and back on.
// NOTE: C++ will automatically call the default constructor when declaring
// a global variable with a class (like BLEModule) as its type.
BLEModule::BLEModule() {
  this->deviceConnected = false;
  this->sensorGroup = nullptr;

  // Create the BLE Device
  BLEDevice::init(BLE_DEVICE_NAME);
  // Create the BLE Server
  this->pServer = BLEDevice::createServer();
  this->pServer->setCallbacks(new ServerCallbacks(&this->deviceConnected));
  // Create the BLE Service
  this->pService = this->pServer->createService(SERVICE_UUID);
  // Create a BLE Characteristic
  this->pCharacteristic = this->pService->createCharacteristic(
                      PACKET_CHARACTERISTIC_UUID,
                      BLECharacteristic::PROPERTY_READ   |
                      BLECharacteristic::PROPERTY_NOTIFY
                    );
  // Create a BLE Descriptor
  this->pCharacteristic->addDescriptor(new BLE2902());

 this->rCharacteristic = this->pService->createCharacteristic(
					  PROFILE_CHARACTERISTIC_UUID,
                      BLECharacteristic::PROPERTY_READ   |
                      BLECharacteristic::PROPERTY_NOTIFY |
                      BLECharacteristic::PROPERTY_WRITE
                    );
  this->rCharacteristic->addDescriptor(new BLE2902());

  // Start the service
  this->pService->start();

  // Start advertising
  BLEAdvertising* pAdvertising = BLEDevice::getAdvertising();
  pAdvertising->addServiceUUID(SERVICE_UUID);
  pAdvertising->setScanResponse(false);
  pAdvertising->setMinPreferred(0x0);  // set value to 0x00 to not advertise this parameter
  BLEDevice::startAdvertising();
}

void BLEModule::update(DataPacket* dataPacket) {
  uint8_t arr[MAX_BYTES_IN_PACKET];
  size_t size = dataPacket->toByteArray(arr);
  this->pCharacteristic->setValue(arr, size);
  this->pCharacteristic->notify();
}

void BLEModule::setSensorGroup(ModularSensorGroup* sensorGroup) {
	this->sensorGroup = sensorGroup;
	rCharacteristic->setCallbacks(new CharacteristicCallbacks(sensorGroup));
}

bool BLEModule::isDeviceConnected() {
  return this->deviceConnected;
}

ServerCallbacks::ServerCallbacks(bool* deviceConnected) {
  this->deviceConnected = deviceConnected;
}

void ServerCallbacks::onConnect(BLEServer* pServer) {
  *deviceConnected = true;
}

void ServerCallbacks::onDisconnect(BLEServer* pServer) {
  *deviceConnected = false;

  // restart advertising
  delay(500); // the bluetooth stack needs a bit of time to get things ready
  pServer->startAdvertising();
}

CharacteristicCallbacks::CharacteristicCallbacks(ModularSensorGroup* sensorGroup) {
	this->sensorGroup = sensorGroup;
}

void CharacteristicCallbacks::onWrite(BLECharacteristic* characteristic) {
	if (this->sensorGroup != nullptr) {
		uint32_t* data = (uint32_t*)characteristic->getData();
		Serial.println(data[0]);
		//TODO - handle 	this->sensorGroup->reinit(data);
		this->sensorGroup->processData(*data);

	}
}
