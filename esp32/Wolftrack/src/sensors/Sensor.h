#ifndef _SENSOR_H
#define _SENSOR_H

class Sensor {
	public:
		virtual void loop() = 0;
		virtual int getValue() = 0;
		virtual int getDataBits() = 0;
		virtual int getMoreValues() = 0;
		virtual void printType() = 0;
};

#endif
