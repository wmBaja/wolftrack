#include "CompetitionSensorGroup.h"
#include "../../../config.h"

CompetitionSensorGroup::CompetitionSensorGroup() {
  this->fuelSensor = Fuel();
  this->engineRPMSensor = EngineRPM(ENGINE_RPM_PIN);
  this->cvtSecRPMSensor = CVTSecRPM(CVT_SEC_RPM_PIN);
  this->cvtTempSensor = CVTTemperature();
  this->brakeSensor1 = BrakePressure();
  this->brakeSensor2 = BrakePressure();
}

void CompetitionSensorGroup::loop() {
  fuelSensor->loop();
  engineRPMSensor->loop();
  cvtSecRPMSensor->loop();
  cvtTempSensor->loop();
  brakeSensor1->loop();
  brakeSensor2->loop();
}

void CompetitionSensorGroup::buildDataPacket(DataPacket* dataPacket) {
  *dataPacket = DataPacket();

  // add fuel data to the packet
  dataPacket->addValue(fuelSensor->getValue(), FUEL_DATA_BITS);

  // add engine RPM data to the packet
  dataPacket->addValue(engineRPMSensor->getValue(), ENGINE_RPM_DATA_BITS);

  // add CVT secondary RPM data to the packet
  dataPacket->addValue(cvtSecRPMSensor->getValue(), CVT_SEC_DATA_BITS);

  // add CVT temperature data to the packet
  dataPacket->addValue(cvtTempSensor->getValue(), CVT_TEMP_DATA_BITS);

  // add front brake pressure data to the packet
  dataPacket->addValue(brakeSensor1->getValue(), BRAKE_PRESSURE_DATA_BITS);

  // add rear brake pressure data to the packet
  dataPacket->addValue(brakeSensor2->getValue(), BRAKE_PRESSURE_DATA_BITS);
}