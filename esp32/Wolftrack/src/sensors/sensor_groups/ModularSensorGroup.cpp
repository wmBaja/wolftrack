#include "ModularSensorGroup.h"
#include "../../../config.h"

ModularSensorGroup::ModularSensorGroup():
	adc()
{
	adc.begin(MCP3008_SPI_CS, MCP3008_SPI_MOSI, MCP3008_SPI_MISO, MCP3008_SPI_SCLK);
	sensorList = strToVec(std::vector<std::string>(std::begin(DEFAULT_SENSOR_GROUP), std::end(DEFAULT_SENSOR_GROUP)));
}

void ModularSensorGroup::loop() {
	for (Sensor* sensor: this->sensorList) {
		sensor->loop();
	}
}

void ModularSensorGroup::reinit(std::vector<Sensor*> newSensorList) {
	for (std::vector<Sensor*>::iterator sensor = this->sensorList.begin(); sensor != this->sensorList.end(); sensor++) {
		this->sensorList.erase(sensor);
		delete (*sensor);
	}
	for (Sensor* sensor: newSensorList) {
		this->sensorList.push_back(sensor);
	}
}

std::vector<Sensor*> ModularSensorGroup::strToVec(std::vector<std::string> sensorNames) {
	std::vector<Sensor*> newSensorList;
	for (std::string sensorName: sensorNames) {
		if (sensorName == "accelerometer") {
			newSensorList.push_back(new Accelerometer);
		}
		else if (sensorName == "front_brake") {
			newSensorList.push_back(new BrakePressure(&(this->adc), FRONT_BRAKE_PRESSURE_CHANNEL));
		}
		else if (sensorName == "rear_brake") {
			newSensorList.push_back(new BrakePressure(&(this->adc), REAR_BRAKE_PRESSURE_CHANNEL));
		}
		else if (sensorName == "fuel") {
			newSensorList.push_back(new Fuel(&(this->adc), FUEL_HALL_EFFECT_CHANNEL));
		}
		else if (sensorName == "engine_rpm") {
			newSensorList.push_back(new EngineRPM(ENGINE_RPM_PIN));
		}
		else if (sensorName == "cvt_sec_rpm") {
			newSensorList.push_back(new CVTSecRPM(CVT_SEC_RPM_PIN));
		}
		else if (sensorName == "cvt_temp") {
			newSensorList.push_back(new CVTTemperature);
		}
		else if (sensorName == "front_left_shock") {
			newSensorList.push_back(new ShockCompression(&(this->adc), FL_SHOCK_COMPRESSION_CHANNEL));
		}
		else if (sensorName == "front_right_shock") {
			newSensorList.push_back(new ShockCompression(&(this->adc), FR_SHOCK_COMPRESSION_CHANNEL));
		}
	}
}

void ModularSensorGroup::buildDataPacket(DataPacket* dataPacket) {
	for (Sensor* sensor: sensorList) {
		if (sensor->getMoreValues() == IS_ACCELEROMETER) {
			Accelerometer* accel = (Accelerometer*) sensor;
			dataPacket->addValue(accel->getXAccel(), accel->getDataBits());
			dataPacket->addValue(accel->getYAccel(), accel->getDataBits());
			dataPacket->addValue(accel->getZAccel(), accel->getDataBits());
		}
		else {
		dataPacket->addValue(sensor->getValue(), sensor->getDataBits());
		}
	}
}

