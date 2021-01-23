#ifndef _STOP_OP_H
#define _STOP_OP_H

#include <stdbool.h>

#include "Sensor.h"

class StopOp: public Sensor {
	int pin;
	int pressStatus;
public:
	StopOp();
	StopOp(int);
	void loop();
	int getValue();
private:
	void check();
};

#endif
