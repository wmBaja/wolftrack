#ifndef _COMP_SENSOR_GROUP_H
#define _COMP_SENSOR_GROUP_H

#include <MCP3XXX.h>

#include "SensorGroup.h"
#include "../Fuel.h"
#include "../EngineRPM.h"
#include "../CVTSecRPM.h"
#include "../CVTTemperature.h"
#include "../BrakePressure.h"

class CompetitionSensorGroup : public SensorGroup
{
  MCP3008 adc;
  Fuel fuelSensor;
  EngineRPM engineRPMSensor;
  CVTSecRPM cvtSecRPMSensor;
  CVTTemperature cvtTempSensor;
  BrakePressure brakeSensor1;
  BrakePressure brakeSensor2;

public:
  CompetitionSensorGroup();
  void loop();
  void buildDataPacket(DataPacket *);
};

#endif
