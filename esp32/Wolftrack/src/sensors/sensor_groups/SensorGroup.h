#ifndef _SENSOR_GROUP_H
#define _SENSOR_GROUP_H

#include "../../ble/DataPacket.h"

class SensorGroup {
  public:
    virtual void loop() = 0;
    virtual void buildDataPacket(DataPacket*) = 0;
	virtual int getStopValue();
    // TODO add a similar method for building a data entry for writing to SD card
};

#endif
