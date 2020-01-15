#include <Arduino.h>
#include <stdlib.h>


//--------------------PINS DEFINITIONS---------------------------
#define RPM_INDUCTION_PIN A1




//------------------INDUCTION RPM-----------------------------
/**
 * @author Stanton Parham
 * @author Trevor Leibert
 * 
 * Detects the current rmp from the engine
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
// the next time to print an update (in ms)
unsigned long nextUpdateTime = 0;
// the last time that a voltage spike occurred (in ms)
unsigned long lastSpikeTime = 0;
// the total number of sparks in this update period
int numSparks = 0;

int rpm = 0;


int getInductionRPM() {
  int sensorValue = analogRead(RPM_INDUCTION_PIN);
  // determine if there is currently a voltage spike
  bool isSpiking = sensorValue > THRESHOLD ? true : false;
//  Serial.println(sensorValue);
  // get the current time
  curTime = millis();

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
    rpm = numSparks * SPARKS_PER_UPDATE_TO_SPARKS_PER_MIN;
    // report RPM
    //Serial.println(rpm);
    // calculate the next update time
    nextUpdateTime = curTime + UPDATE_PERIOD;
    // reset num of sparks
    numSparks = 0;
  }
  // get the current time
  curTime = millis();

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
    int rpm = numSparks * SPARKS_PER_UPDATE_TO_SPARKS_PER_MIN;
    // report RPM
    Serial.println(rpm);
    // calculate the next update time
    nextUpdateTime = curTime + UPDATE_PERIOD;
    // reset num of sparks
    numSparks = 0;
  }
}

//---------------------------END INDUCTION RPM---------------


unsigned long last_output_time = 0;

void setup() {
    Serial.begin(115200);
    curTime = millis();
    nextUpdateTime = curTime + UPDATE_PERIOD;
}

void loop() {
  //Actual code to use
  
  //nt potentiameter1 = analogRead(analogInPin);
  int fuel = 0;
  int engine_rpm = getInductionRPM();
  int cvt_rpm = round(engine_rpm / ((random(101) / 100.0) * 2.6 + 0.9));
  int cvt_temp = 0;
  int brake_1 = 0;
  int brake_2 = 0;
  int shock_1 = 0;
  int shock_2 = 0;

  
  //byte high = highByte(potentiameter1);
  //byte low = lowByte(potentiameter1);
  
  unsigned long currentTime = millis();
  if (currentTime - last_output_time > 500) {
    byte arr[] = {highByte(fuel), lowByte(fuel), highByte(engine_rpm), lowByte(engine_rpm), highByte(cvt_rpm), lowByte(cvt_rpm), highByte(cvt_temp), lowByte(cvt_temp),
    highByte(brake_1), lowByte(brake_1), highByte(brake_2), lowByte(brake_2), highByte(shock_1), lowByte(shock_1), highByte(shock_2), lowByte(shock_2)};
    Serial.write(arr, 16);
    last_output_time = currentTime;
    Serial.print("break");
  }
 
  
  
  
}
