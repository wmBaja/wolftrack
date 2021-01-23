#include <Arduino.h>
#include <Wire.h>

#include "StopOp.h"
#include "../../config.h"
#include "../utils.h"

StopOp::StopOp(int pin):
	pin(pin),
	pressStatus(0)
{
	pinMode(pin, INPUT);
}

StopOp::StopOp():
	StopOp::StopOp(STOP_OP_PIN)
{}

void StopOp::loop() {
	this->check();
}

void StopOp::check() {
	if (digitalRead(STOP_OP_PIN) == HIGH) {
		this->pressStatus = 1;
		return;
	}
	this->pressStatus = 0;
}	

int StopOp::getValue() {
	return this->pressStatus;
}
