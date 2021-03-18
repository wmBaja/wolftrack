#ifndef _BUSCO_2020_12_SENSOR_GROUP_H
#define _BUSCO_2020_12_SENSOR_GROUP_H

#include <MCP3XXX.h>

#include "SensorGroup.h"
#include "../BrakePressure.h"
#include "../ShockCompression.h"
#include "../Accelerometer.h"
#include "../CVTTemperature.h"

class Busco2020_12SensorGroup: public SensorGroup {
    MCP3008 adc;
    Accelerometer accelerometer;
    ShockCompression shockCompression;
	CVTTemperature cvtTempSensor;
    BrakePressure frontBrakeSensor;
  public:
    Busco2020_12SensorGroup();
    void loop();
    void buildDataPacket(DataPacket*);
};

#endif
