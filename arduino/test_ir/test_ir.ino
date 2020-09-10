#include <IRremote.h>


#define TRANSMITTER_IR_VALUE 632192736
#define IR_INTERVAL 100
#define MILLIS_IN_SEC 1000.0
#define IR_RECEIVER_PIN 7

// the IR receiver
IRrecv irrecv(IR_RECEIVER_PIN);
// the results from the IR decoding process
decode_results results;

// whether or not we are currently sensing the IR value
bool sensingIR = false;
// whether or not we are currently timing
bool timing = false;
// the last time that the transmitter value was received
unsigned long lastTimeSeeingTransmitterValue = 0;
// the start time for the timer
unsigned long startTime = 0;

void setup(){
  Serial.begin(9600);
  irrecv.enableIRIn();
//  irrecv.blink13(true);
}

void loop() {
  unsigned long irValue = -1;
  if (irrecv.decode(&results)) {
    irValue = results.value;
    irrecv.resume();
  }

  unsigned long curTime = millis();

  // if we see the transmitter value
  if (irValue == TRANSMITTER_IR_VALUE) {
    lastTimeSeeingTransmitterValue = curTime;

    // if we aren't sensing IR
    if (!sensingIR) {
      // now we are sensing IR
      sensingIR = true;
      // if we aren't currently timing
      if (!timing) {
        // start timing
        Serial.println("Starting timer");
        startTime = curTime;
        timing = true;
      } else { // else we have been timing
        // so stop timing
        Serial.println("Stopping timer");
        unsigned long millisElapsed = curTime - startTime;
        double secsElapsed = millisElapsed / MILLIS_IN_SEC;
        Serial.print("Time elapsed (ms) : ");
        Serial.println(millisElapsed);
        Serial.print("Time elapsed (s)  : ");
        Serial.println(secsElapsed);

        timing = false;
      }
    }
    
  } else if (curTime > lastTimeSeeingTransmitterValue + IR_INTERVAL) { // else if we haven't seen the transmitter value for IR_INTERVAL time
    // then we are no longer sensing IR
    sensingIR = false;
  }
}
