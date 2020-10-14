#ifndef _BLE_MODULE_H
#define _BLE_MODULE_H

#include <stdbool.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

#include "DataPacket.h"

class BLEModule {
    BLEServer* pServer;
    BLEService* pService;
    BLECharacteristic* pCharacteristic;
    bool deviceConnected;
  public:
    BLEModule();
    void update(DataPacket*);
    bool isDeviceConnected();
};

class Callbacks: public BLEServerCallbacks {
    bool* deviceConnected;
  public:
    Callbacks(bool*);
    void onConnect(BLEServer*);
    void onDisconnect(BLEServer*);
};

#endif
