#include <Arduino.h>

#include "ModularSensorGroup.h"
#include "../../../config.h"

ModularSensorGroup::ModularSensorGroup():
	adc()
{
	adc.begin(MCP3008_SPI_CS, MCP3008_SPI_MOSI, MCP3008_SPI_MISO, MCP3008_SPI_SCLK);
//	sensorList = this->strToVec(std::vector<std::string>(std::begin(DEFAULT_SENSOR_GROUP), std::end(DEFAULT_SENSOR_GROUP)));
}

void ModularSensorGroup::loop() {
	for (Sensor* sensor: this->sensorList) {
		sensor->loop();
	}
}

void ModularSensorGroup::reinit(std::vector<Sensor*> *newSensorList) {
	this->sensorList.clear();
	for (Sensor* sensor: *newSensorList) {
		this->sensorList.push_back(sensor);
	}
	delete newSensorList;
}

std::vector<Sensor*> *ModularSensorGroup::strToVec(std::vector<std::string> sensorNames) {
	std::vector<Sensor*> *newSensorList = new std::vector<Sensor*>;
	for (std::string sensorName: sensorNames) {
		if (sensorName == "accelerometer") {
			newSensorList->push_back(new Accelerometer);
		}
		else if (sensorName == "front_brake") {
			newSensorList->push_back(new BrakePressure(&(this->adc), FRONT_BRAKE_PRESSURE_CHANNEL));
		}
		else if (sensorName == "rear_brake") {
			newSensorList->push_back(new BrakePressure(&(this->adc), REAR_BRAKE_PRESSURE_CHANNEL));
		}
		else if (sensorName == "fuel") {
			newSensorList->push_back(new Fuel(&(this->adc), FUEL_HALL_EFFECT_CHANNEL));
		}
		else if (sensorName == "engine_rpm") {
			newSensorList->push_back(new EngineRPM(ENGINE_RPM_PIN));
		}
		else if (sensorName == "cvt_sec_rpm") {
			newSensorList->push_back(new CVTSecRPM(CVT_SEC_RPM_PIN));
		}
		else if (sensorName == "cvt_temp") {
			newSensorList->push_back(new CVTTemperature);
		}
		else if (sensorName == "front_left_shock") {
			newSensorList->push_back(new ShockCompression(&(this->adc), FL_SHOCK_COMPRESSION_CHANNEL));
		}
		else if (sensorName == "front_right_shock") {
			newSensorList->push_back(new ShockCompression(&(this->adc), FR_SHOCK_COMPRESSION_CHANNEL));
		}
	}
	return newSensorList;
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

void ModularSensorGroup::processData(uint32_t data) {
	uint32_t mask = 0b1;
	Serial.println(data, BIN);
	std::vector<std::string> newSensorList;
	std::string sensorOrderedList[]  = {"cvt_sec_rpm", "cvt_temp", "fuel", "engine_rpm", "front_brake", "front_left_shock", "accelerometer"};
	Serial.print("Changing sensors to ");
	size_t len = sizeof(sensorOrderedList)/sizeof(sensorOrderedList[0]);
	for (size_t i = 0; i < len; i++) {
		data = data >> 1;
		uint32_t state = data & mask;
		if (state == 1) {
			Serial.print(sensorOrderedList[i].c_str());
			Serial.print(" ");
			newSensorList.push_back(sensorOrderedList[i]);
		}
	}
	Serial.println("\nFinished updating sensors");
	this->reinit(this->strToVec(newSensorList));
	return;
}

void ModularSensorGroup::printSensorList() {
	Serial.println("Current Sensor Profile:");
	for (Sensor* sensor: this->sensorList) {
		sensor->printType();
	}
}
