#ifndef _BUSCO_2020_12_SENSOR_GROUP_HALFSHAFT_H
#define _BUSCO_2020_12_SENSOR_GROUP_HALFSHAFT_H

#include "SensorGroup.h"
#include "../StrainGauge_HX711.h"

class Busco2020_12SensorGroup_halfshaft: public SensorGroup {
    StrainGauge_HX711 strainGauge;
  public:
    Busco2020_12SensorGroup_halfshaft();
    void loop();
    void buildDataPacket(DataPacket*);
};

#endif
