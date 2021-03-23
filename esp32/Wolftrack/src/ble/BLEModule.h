#ifndef _BLE_MODULE_H
#define _BLE_MODULE_H

#include <stdbool.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

#include "DataPacket.h"
#include "../sensors/sensor_groups/ModularSensorGroup.h"

class BLEModule {
    BLEServer* pServer;
    BLEService* pService;
    BLECharacteristic* pCharacteristic;
	BLECharacteristic* rCharacteristic;
    bool deviceConnected;
	ModularSensorGroup* sensorGroup;
  public:
    BLEModule();
    void update(DataPacket*);
	void setSensorGroup(ModularSensorGroup*);
    bool isDeviceConnected();
};

class ServerCallbacks: public BLEServerCallbacks {
    bool* deviceConnected;
  public:
    ServerCallbacks(bool*);
    void onConnect(BLEServer*);
    void onDisconnect(BLEServer*);
};

class CharacteristicCallbacks: public BLECharacteristicCallbacks {
	ModularSensorGroup* sensorGroup;
  public:
	CharacteristicCallbacks(ModularSensorGroup*);
	void onWrite(BLECharacteristic* characteristic);
};

#endif
