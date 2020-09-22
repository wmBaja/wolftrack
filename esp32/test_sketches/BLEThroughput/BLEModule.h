#include <stdbool.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

class BLEModule {
    BLEServer* pServer;
    BLEService* pService;
    BLECharacteristic* pCharacteristic;
    bool deviceConnected;
  public:
    BLEModule();
    void updateAndNotify(uint8_t*,size_t);
    bool isDeviceConnected();
};

class Callbacks: public BLEServerCallbacks {
    bool* deviceConnected;
  public:
    Callbacks(bool*);
    void onConnect(BLEServer*);
    void onDisconnect(BLEServer*);
};
