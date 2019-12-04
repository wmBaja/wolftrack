#include <Arduino.h>


const int analogInPin = A0;

void setup() {
    Serial.begin(9600);
    randomSeed(analogRead(1));
}

void loop() {
  //Actual code to use
  
  int potentiameter1 = analogRead(analogInPin);
  
  byte high = highByte(potentiameter1);
  byte low = lowByte(potentiameter1);
  byte arr[] = {high, low};
  
  Serial.write(arr, 2);
  
  
  delay(100);
}
