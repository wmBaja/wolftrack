#ifndef _COMP_SENSOR_GROUP_H
#define _COMP_SENSOR_GROUP_H

#include "SensorGroup.h"

#include "../Fuel.h"
#include "../EngineRPM.h"
#include "../CVTSecRPM.h"
#include "../CVTTemperature.h"
#include "../BrakePressure.h"

class CompetitionSensorGroup: public SensorGroup {
    Fuel fuelSensor;
    EngineRPM engineRPMSensor;
    CVTSecRPM cvtSecRPMSensor;
    CVTTemperature cvtTempSensor;
    BrakePressure brakeSensor1;
    BrakePressure brakeSensor2;
  public:
    void loop();
    void buildDataPacket(DataPacket*);
};

#endif
