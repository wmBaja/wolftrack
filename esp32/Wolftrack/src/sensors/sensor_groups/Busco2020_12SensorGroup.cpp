#include "Busco2020_12SensorGroup.h"
#include "../../../config.h"

Busco2020_12SensorGroup::Busco2020_12SensorGroup():
  adc(),
  accelerometer(),
  shockCompression(&adc, FL_SHOCK_COMPRESSION_CHANNEL),
  frontBrakeSensor(&adc, FRONT_BRAKE_PRESSURE_CHANNEL)
{
  adc.begin(MCP3008_SPI_CS, MCP3008_SPI_MOSI, MCP3008_SPI_MISO, MCP3008_SPI_SCLK);
}

void Busco2020_12SensorGroup::loop() {
  accelerometer.loop();
  frontBrakeSensor.loop();
}

void Busco2020_12SensorGroup::buildDataPacket(DataPacket* dataPacket) {
  *dataPacket = DataPacket();

  // add x acceleration data to the packet
  dataPacket->addValue(accelerometer.getXAccel(), ACCELERATION_DATA_BITS);
  // add y acceleration data to the packet
  dataPacket->addValue(accelerometer.getYAccel(), ACCELERATION_DATA_BITS);
  // add z acceleration data to the packet
  dataPacket->addValue(accelerometer.getZAccel(), ACCELERATION_DATA_BITS);
  // add shock compression data to the packet
  dataPacket->addValue(shockCompression.getValue(), SHOCK_COMPRESSION_DATA_BITS);
  // add front brake pressure data to the packet
  dataPacket->addValue(frontBrakeSensor.getValue(), BRAKE_PRESSURE_DATA_BITS);
}
