// number of milliseconds in a second
#define MILLIS_IN_SEC 1000.0
// number of seconds in a minute
#define SECS_IN_MIN 60.0
// the baud rate for the serial connection
#define BAUD_RATE 115200
// amount of time between transmissions to RPi (in ms)
#define TRANSMISSION_INTERVAL 1000
// the pin used to measure engine RPM
#define ENGINE_RPM_INDUCTION_PIN 2

// the current time (in ms)
unsigned long curTime = 0;
// the time at which the next data packet should be sent to the RPi
unsigned long nextTransmissionTime = 0;


// amount of time between RPM (engine and CVT secondary) updates (in ms)
#define RPM_UPDATE_INTERVAL 1000
// the conversion factor for revs per update to revs per minute
#define REVS_PER_UPDATE_TO_REVS_PER_MIN (SECS_IN_MIN / (RPM_UPDATE_INTERVAL / MILLIS_IN_SEC))

// the next time to calculate the RPM (engine and secondary) (in ms)
unsigned long nextRPMUpdateTime = 0;
// the most recently calculated engine RPM
int engineRPM = 0;

// whether or not the engine is currently sparking
bool sparking = false;
// the total number of sparks in this update period
int numSparks = 0;

void checkForSparks() {
  int pinState = digitalRead(ENGINE_RPM_INDUCTION_PIN);

  // if the pin is high
  if (pinState) {
    // if the engine is not considered sparking
    if (!sparking) {
      // then this is a new spark
      numSparks++;
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
    // calculate the engine RPM from the num sparks in this update period
    engineRPM = numSparks * REVS_PER_UPDATE_TO_REVS_PER_MIN;
    // reset the number of sparks
    numSparks = 0;

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
