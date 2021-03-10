#include "Busco2020_12SensorGroup_halfshaft.h"
#include "../../../config.h"

Busco2020_12SensorGroup_halfshaft::Busco2020_12SensorGroup_halfshaft():
  strainGauge(HX711_DATA, HX711_CLK, HX711_CALIBRATION_FACTOR)
{}

void Busco2020_12SensorGroup_halfshaft::loop() {
  strainGauge.loop();
}

void Busco2020_12SensorGroup_halfshaft::buildDataPacket(DataPacket* dataPacket) {
  *dataPacket = DataPacket();

  // add x acceleration data to the packet
  dataPacket->addValue(strainGauge.getValue(), STRAIN_DATA_BITS);
}
