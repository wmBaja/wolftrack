#ifndef _SHOCK_COMPRESSION_H
#define _SHOCK_COMPRESSION_H

#include <stdbool.h>
#include <MCP3XXX.h>

#include "Sensor.h"

// amount of time between sensor reads
#define READ_INTERVAL 1000

class ShockCompression : public Sensor
{
  MCP3008 *adc;
  uint8_t adcChannel;
  // the most recently calculated shock compression
  int shockCompression;
  // the time at which to read a new value from the sensor
  unsigned long nextReadTime;

public:
  ShockCompression(MCP3008 *, uint8_t);
  void loop();
  int getValue();
};

#endif
