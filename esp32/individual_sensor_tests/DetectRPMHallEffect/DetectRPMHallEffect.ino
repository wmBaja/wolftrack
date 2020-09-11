// the number of milliseconds in a second
int MILLIS_IN_SEC = 1000;
// the number of seconds in a minute
int SECS_IN_MIN = 60;

// the amount of time between updates (in ms)
int UPDATE_PERIOD = 1000;
// the conversion factor for spikes per update period to spikes per minute
int SPIKES_PER_UPDATE_TO_SPIKES_PER_MIN = SECS_IN_MIN / (UPDATE_PERIOD / MILLIS_IN_SEC);

// voltage spike threshold (in terms of a range of 0-5V mapped into a 0-1023 range)
int LOWTHRESHOLD = 100; // (min 7 max 210)
int HIGHTHRESHOLD = 120
// the maximum amount of time between spikes (in ms)
int MAX_SPIKE_INTERVAL = 5;

// the current time (in ms)
unsigned long curTime = 0;
// the next time to print an update (in ms)
unsigned long nextUpdateTime = 0;
// the last time that a voltage spike occurred (in ms)
//unsigned long lastSpikeTime = 0;
// the total number of spikes in this update period
int numSpikes = 0;
// To see whether the magnet is currently close or not, initialized to false
bool isClose= false;


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
  // Serial.println(sensorValue);
  // get the current time
  curTime = millis();
  
  //if the sensor value has dropped below the threshold indicating the magnet is close
  if ((sensorValue < LOWTHRESHOLD) && !isClose) {
    // then change the current state of the magnet to close
    isClose= true;
    //increment how many spikes have happened, will only be performed once per rotation
    ++numSpikes;
  }
  // If the sensor value is above the threshold indicating the magnet is no longer close
  else if ((sensorValue > HIGHTHRESHOLD) && isClose) {
    // then change the current state of the magnet to not close
    isClose = false;
  }
  
  // update every update period
  if (curTime > nextUpdateTime) {
    // calculate the RPM from the num spikes in this update period
    int rpm = numSpikes * SPIKES_PER_UPDATE_TO_SPIKES_PER_MIN;
    // report RPM
    Serial.println(rpm);
    // calculate the next update time
    nextUpdateTime = curTime + UPDATE_PERIOD;
    // reset num of spikes
    numSpikes = 0;
  }
}
