#include <Arduino.h>

#include "ShockCompression.h"
#include "../../config.h"

ShockCompression::ShockCompression(MCP3008 *adc, uint8_t adcChannel) : adc(adc),
                                                                       adcChannel(adcChannel),
                                                                       shockCompression(0),
                                                                       nextReadTime(0)
{
}

void ShockCompression::loop()
{
#if GENERATE_RANDOM_VALUES
  this->shockCompression = random(1024);
#else
  unsigned long curTime = millis();

  if (curTime > this->nextReadTime)
  {
    uint32_t sensorValue = this->adc->analogRead(this->adcChannel);
    double actuationIn = 6 - (sensorValue / 1023.0) * 6; // range: 0 - 6
    // TODO implement conversion from real value to integer value
    this->shockCompression = (int)actuationIn;

    // calculate the next read time
    this->nextReadTime = curTime + READ_INTERVAL;
  }
#endif
}

int ShockCompression::getValue()
{
  return this->shockCompression;
}
