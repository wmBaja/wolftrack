#ifndef _MODULAR_SENSOR_GROUP_H
#define _MODULAR_SENSOR_GROUP_H

#include <MCP3XXX.h>

#include "SensorGroup.h"
#include "../Sensor.h"

#include "../Accelerometer.h"
#include "../BrakePressure.h"
#include "../CVTSecRPM.h"
#include "../CVTTemperature.h"
#include "../EngineRPM.h"
#include "../Fuel.h"
#include "../ShockCompression.h"

class ModularSensorGroup: public SensorGroup {
	MCP3008 adc;
	std::vector<Sensor*> sensorList;
	public:
		ModularSensorGroup();
		void loop();
		void reinit(std::vector<Sensor*> newSensorList);
		std::vector<Sensor*> strToVec(std::vector<std::string>);
		void buildDataPacket(DataPacket*);
		void processData(uint32_t data);
};

#endif
