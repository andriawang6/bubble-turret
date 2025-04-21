#include <Servo.h>

Servo upDown;
Servo leftRight;
Servo bubbleSpin;

const int udPin = 5;
const int lrPin = 6;
const int bubbleSpinPin = 7;
const int bubblePotPin = A0; 

int udPos = 90; // Start at middle
int lrPos = 90;
int targetUd = 90;
int targetLr = 90;

const int stepSize = 2;        // Smaller step for smoother motion
const int updateDelay = 15;    // ms between servo updates

unsigned long lastUpdate = 0;

int bubbleSpinOn;
int bubbleSpinSpeed;
int change = 0;
int prevPot = 0;
long time = 0;

void setup() {
  pinMode(bubblePotPin, INPUT);
  bubbleSpin.attach(bubbleSpinPin);
  bubbleSpin.writeMicroseconds(1500);
  bubbleSpinOn = 0;
  time = millis(); 

  upDown.attach(udPin);
  leftRight.attach(lrPin);
  upDown.write(udPos);
  leftRight.write(lrPos);

  Serial.begin(9600);
  Serial1.begin(9600);
  Serial.println("Arduino Bluetooth Receiver Ready");
}

void loop() {
  if (Serial1.available()) {
    char command = Serial1.read();
    switch (command) {
      case 'r': targetLr = constrain(targetLr - 10, 0, 180); break;
      case 'l': targetLr = constrain(targetLr + 10, 0, 180); break;
      case 'u': targetUd = constrain(targetUd - 10, 0, 180); break;
      case 'd': targetUd = constrain(targetUd + 10, 0, 180); break;
      case 'c': 
        targetUd = 90; 
        targetLr = 90; 
        break;
      case 'x': bubbleSpinOn = 0; break; 
      case 's': bubbleSpinOn = 1; break; 
    }
  }

  long temp = millis();
  if (temp - time > 100) {
    toggleBubbleSpeed();
    time = temp;
  }
  
  unsigned long now = millis();
  if (now - lastUpdate > updateDelay) {
    lastUpdate = now;

    if (udPos != targetUd) {
      udPos += (targetUd > udPos) ? stepSize : -stepSize;
      udPos = constrain(udPos, 80, 100);
      upDown.write(udPos);
    }

    if (lrPos != targetLr) {
      lrPos += (targetLr > lrPos) ? stepSize : -stepSize;
      lrPos = constrain(lrPos, 0, 180);
      leftRight.write(lrPos);
    }
  }
}

void toggleBubbleSpeed() {
  int potValue = analogRead(bubblePotPin);
  if (prevPot != potValue) {
    prevPot = potValue;
  }

  if (bubbleSpinOn == 1) { 
    int servoSpeed = map(potValue, 0, 1023, 1500, 2000);  
    bubbleSpin.writeMicroseconds(servoSpeed);
  } else {
    bubbleSpin.writeMicroseconds(1500);
  }
}
