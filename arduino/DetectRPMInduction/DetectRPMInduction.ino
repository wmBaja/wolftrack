// number of microseconds in a minute
#define MICROS_IN_MIN 60000000
// the baud rate for the serial connection
#define BAUD_RATE 115200
// amount of time between transmissions to RPi (in ms)
#define TRANSMISSION_INTERVAL 1000

// the current time (in ms)
unsigned long curTime = 0;
// the time at which the next data packet should be sent to the RPi (in ms)
unsigned long nextTransmissionTime = 0;


// amount of time between RPM (engine and CVT secondary) updates (in ms)
#define RPM_UPDATE_INTERVAL 1000
// the pin used to measure engine RPM
#define ENGINE_RPM_INDUCTION_PIN 2

// the next time to calculate the RPM (engine and secondary) (in ms)
unsigned long nextRPMUpdateTime = 0;
// the most recently calculated engine RPM
int engineRPM = 0;

// whether or not the engine is currently sparking
bool sparking = false;
// the number of sparks recorded during the current update interval
int numSparks = 0;
// the sum of all spark intervals (in us) recorded during current the update interval
unsigned long sparkIntervalSum = 0;
// the last time a spark was detected (in us)
unsigned long lastSparkTime = 0;

void checkForSparks() {
  int pinState = digitalRead(ENGINE_RPM_INDUCTION_PIN);

  // if the pin is high
  if (pinState) {
    // if the engine is not considered sparking
    if (!sparking) {
      // then this is a new spark
      numSparks++;

      // get the current time
      unsigned long curTimeMicros = micros();
      // add the last spark interval to the sum
      sparkIntervalSum += curTimeMicros - lastSparkTime;
      // update the last spark time to be this time
      lastSparkTime = curTimeMicros;

      // now we need to consider the engine as sparking
      sparking = true;
    }
  } else { // else the pin is low
    // thus the engine is not sparking
    sparking = false;
  }
}

void updateRPMs() {
  // if it's time to update the RPMs
  if (curTime > nextRPMUpdateTime) {
    // calculate the average spark interval
    unsigned long avgSparkInterval = sparkIntervalSum / numSparks; // could increase accuracy by using floating point ops

    // calculate the engine RPM based on the average spark interval
    engineRPM = MICROS_IN_MIN / avgSparkInterval; // could increase accuracy by using floating point ops

    // reset the number of sparks and spark interval sum
    numSparks = 0;
    sparkIntervalSum = 0;

    // calculate the next update time
    nextRPMUpdateTime = curTime + RPM_UPDATE_INTERVAL;
  }
}

void setup() {
  Serial.begin(BAUD_RATE);
  pinMode(ENGINE_RPM_INDUCTION_PIN, INPUT);
  curTime = millis();
  nextTransmissionTime = curTime + TRANSMISSION_INTERVAL;
  nextRPMUpdateTime = curTime + RPM_UPDATE_INTERVAL;
}

void loop() {
  curTime = millis();

  checkForSparks();
  updateRPMs();

  // if it's time to transmit
  if (curTime > nextTransmissionTime) {
    Serial.println(engineRPM);
    // calculate the next transmission time
    nextTransmissionTime = curTime + TRANSMISSION_INTERVAL;
  }
}
