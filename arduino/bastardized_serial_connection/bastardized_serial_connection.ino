#include <Arduino.h>
#include <stdlib.h>


// amount of time between outputs to RPi (in ms)
#define OUTPUT_INTERVAL 250


//--------------------PIN DEFINITIONS---------------------------
#define FUEL_HALL_EFFECT_PIN A0
#define RPM_INDUCTION_PIN A1
#define CVT_SEC_RPM_PIN A2
#define CVT_TEMP_PIN A3
#define BRAKE_PRESSURE_1_PIN A4
#define BRAKE_PRESSURE_2_PIN A5

//------------------INDUCTION RPM-----------------------------
/**
   @author Stanton Parham
   @author Trevor Leibert

   Detects the current RPM from the engine
*/
// number of milliseconds in a second
#define MILLIS_IN_SEC 1000
// number of seconds in a minute
#define SECS_IN_MIN 60

// amount of time between updates (in ms)
#define UPDATE_PERIOD 1000
// the conversion factor for sparks per update to sparks per minute
#define SPARKS_PER_UPDATE_TO_SPARKS_PER_MIN (SECS_IN_MIN / (UPDATE_PERIOD / MILLIS_IN_SEC))

// voltage spike threshold (in terms of a range of 0-5V mapped into a 0-1023 range)
#define THRESHOLD 900
// the maximum amount of time between spikes (in ms)
#define MAX_SPIKE_INTERVAL 5


// the current time (in ms)
unsigned long curTime = 0;
// the next time to calculate the induction RPM (in ms)
unsigned long nextUpdateTime = 0;
// the last time that a voltage spike occurred (in ms)
unsigned long lastSpikeTime = 0;
// the total number of sparks in this update period
int numSparks = 0;
// the most recently calculated engine RPM
int engineRPM = 0;


void getInductionRPM() {
  int sensorValue = analogRead(RPM_INDUCTION_PIN);
  // determine if there is currently a voltage spike
  bool isSpiking = sensorValue > THRESHOLD;

  // if a voltage spike is detected
  if (isSpiking) {
    // if the last spike occurred over MAX_SPIKE_INTERVAL milliseconds ago
    if (curTime > lastSpikeTime + MAX_SPIKE_INTERVAL) {
      // then a new spark is starting
      numSparks++;
    }
    // this time is the new last spike time
    lastSpikeTime = curTime;
  }

  // update every update period
  if (curTime > nextUpdateTime) {
    // calculate the RPM from the num sparks in this update period
    engineRPM = numSparks * SPARKS_PER_UPDATE_TO_SPARKS_PER_MIN;
    // calculate the next update time
    nextUpdateTime = curTime + UPDATE_PERIOD;
    // reset num of sparks
    numSparks = 0;
  }
}

//---------------------------END INDUCTION RPM---------------


// the time at which the next data packet should be sent to the RPi
unsigned long nextOutputTime = 0;

void setup() {
  Serial.begin(115200);
  curTime = millis();
  nextUpdateTime = curTime + UPDATE_PERIOD;
  nextOutputTime = curTime + OUTPUT_INTERVAL;
}

void loop() {
  curTime = millis();

  int fuel = random(1024); // TODO need to implement
  getInductionRPM();
  int cvt_rpm = round(engineRPM / ((random(101) / 100.0) * 2.6 + 0.9)); // TODO need to implement
  int cvt_temp = random(1024); // TODO need to implement
  int brake_1 = random(1024); // TODO need to implement
  int brake_2 = random(1024); // TODO need to implement
  int shock_1 = random(1024); // TODO need to implement
  int shock_2 = random(1024); // TODO need to implement

  if (curTime > nextOutputTime) {
    byte arr[] = {
      highByte(fuel), lowByte(fuel),             // fuel
      highByte(engineRPM), lowByte(engineRPM),   // engine RPM
      highByte(cvt_rpm), lowByte(cvt_rpm),       // CVT secondary RPM
      highByte(cvt_temp), lowByte(cvt_temp),     // CVT temperature
      highByte(brake_1), lowByte(brake_1),       // brake pressure 1
      highByte(brake_2), lowByte(brake_2),       // brake pressure 2
      highByte(shock_1), lowByte(shock_1),       // shock actuation 1
      highByte(shock_2), lowByte(shock_2),       // shock actuation 2
      255, 255                                   // end of sequence delimiter
    };

    //Serial.write(arr, 18);
    Serial.println(engineRPM);
    nextOutputTime = curTime + OUTPUT_INTERVAL;
  }

}
