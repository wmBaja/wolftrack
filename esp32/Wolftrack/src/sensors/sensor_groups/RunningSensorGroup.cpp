#include "RunningSensorGroup.h"
#include "../../../config.h"
#include <iostream>


RunningSensorGroup::RunningSensorGroup() : adc(), sensorArray(){
    adc.begin(MCP3008_SPI_CS, MCP3008_SPI_MOSI, MCP3008_SPI_MISO,
              MCP3008_SPI_SCLK);
}

void RunningSensorGroup::loop() {
    for (int i = 0; i < sensorArray; i++) {
        if (sensorArray[i] != NULL) {
            sensorArray[i].loop();
        }
    }
}
void buildDataPacket(DataPacket * datapacket) {
    *dataPacket = DataPacket();
    for (int i = 0; i < sensorArray; i++) {
        if (sensorArray[i] != NULL) {
            dataPacket->addValue(sensorArray[i].getValue(), sensorArray[i].getDataBits());
        }
    }
}
void RunningSensorGroup::initDefaultSensorArray() {
    sensorArray[1] = new Fuel(&adc, FUEL_HALL_EFFECT_CHANNEL);
    sensorArray[2] = new EngineRPM(ENGINE_RPM_PIN);
    sensorArray[3] = new CVTSecRPM(CVT_SEC_RPM_PIN);
    sensorArray[4] = new CVTTemperature();
    sensorArray[5] = new BrakePressure(&adc, FRONT_BRAKE_PRESSURE_CHANNEL);
    sensorArray[6] = new BrakePressure(&adc, REAR_BRAKE_PRESSURE_CHANNEL);

}

void RunningSensorGroup::initCustomSensorArray(Sensor * inputArr, int arrLength) {
    // Bounds checking for the array
    try{
        if(arrLength > MAX_SENSORS){
            throw(arrLength)
        }
    } catch(arrLength) {
        std::cout << "Too many sensors! The maximum amount is" << MAX_SENSORS;
        std::cout << arrLength << " sensors found";
    }
    for(int i = 0; i < arrLength; i++) {
        sensorArray[i] = inputArr[i];
    }
}
