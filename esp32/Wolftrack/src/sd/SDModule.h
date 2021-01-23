#ifndef _SD_MODULE_H
#define _SD_MODULE_H

#include <stdbool.h>

#include "../ble/DataPacket.h"

#define MAX_WRITE_BUFFER_SIZE 2048

class SDModule {
    bool cardConnected;
    char curDataFileName[32];
    // the write buffer
    uint8_t buffer[MAX_WRITE_BUFFER_SIZE];
    // the size of the write buffer
    size_t bufferSize;
  public:
    SDModule();
    void addCurDataFileNameToOrderFile();
    void write(DataPacket*);
    bool isCardConnected();
};

#endif
