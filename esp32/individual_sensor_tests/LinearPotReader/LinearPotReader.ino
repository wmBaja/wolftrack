// the baud rate for the serial connection
#define BAUD_RATE 115200
// amount of time between updates (in ms)
#define UPDATE_INTERVAL 50

unsigned long nextUpdateTime;

void setup() {
  Serial.begin(BAUD_RATE);
  nextUpdateTime = millis() + UPDATE_INTERVAL;
}

void loop() {
  unsigned long curTime = millis();
  if (curTime > nextUpdateTime) {
    // read the input on analog pin 0:
    int sensorValue = analogRead(34); // range: 0 - 4095
    double actuationIn = 6 - (sensorValue / 4095.0) * 6; // range: 0 - 6
    Serial.println(actuationIn);

    nextUpdateTime = curTime + UPDATE_INTERVAL;
  }
}
