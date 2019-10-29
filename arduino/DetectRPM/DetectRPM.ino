// the number of milliseconds in a second
int MILLIS_IN_SEC = 1000;
// the number of seconds in a minute
int SECS_IN_MIN = 60;

// the amount of time between updates (in ms)
int UPDATE_PERIOD = 1000;
// the conversion factor for sparks per update period to sparks per minute
int SPARKS_PER_UPDATE_TO_SPARKS_PER_MIN = SECS_IN_MIN / (UPDATE_PERIOD / MILLIS_IN_SEC);

// voltage spike threshold (in terms of a range of 0-5V mapped into a 0-1023 range)
int THRESHOLD = 900; // (1 volt)

// the maximum amount of time between spikes (in ms)
int MAX_SPIKE_INTERVAL = 5;

// the current time (in ms)
unsigned long curTime = 0;
// the next time to print an update (in ms)
unsigned long nextUpdateTime = 0;
// the last time that a voltage spike occurred (in ms)
unsigned long lastSpikeTime = 0;
// the total number of sparks in this update period
int numSparks = 0;



void setup() {
  // establish serial connection
  Serial.begin(9600);
  // calculate the next print time
  curTime = millis();
  nextUpdateTime = curTime + UPDATE_PERIOD;
}



void loop() {
  // get sensor reading
  int sensorValue = analogRead(A0);
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
    int rpm = numSparks * SPARKS_PER_UPDATE_TO_SPARKS_PER_MIN;
    // report RPM
    Serial.println(rpm);
    // calculate the next update time
    nextUpdateTime = curTime + UPDATE_PERIOD;
    // reset num of sparks
    numSparks = 0;
  }
}
