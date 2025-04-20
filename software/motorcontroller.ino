#include <Servo.h>

Servo upDown;
Servo leftRight;

const int udPin = 5;
const int lrPin = 6;

int udPos = 90; // Start at middle
int lrPos = 90;
int targetUd = 90;
int targetLr = 90;

const int stepSize = 2;        // Smaller step for smoother motion
const int updateDelay = 15;    // ms between servo updates

unsigned long lastUpdate = 0;

void setup() {
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
    Serial.print("Received: ");
    Serial.println(command);

    switch (command) {
      case 'r': targetLr = constrain(targetLr - 10, 0, 180); break;
      case 'l': targetLr = constrain(targetLr + 10, 0, 180); break;
      case 'u': targetUd = constrain(targetUd - 10, 0, 180); break;
      case 'd': targetUd = constrain(targetUd + 10, 0, 180); break;
      case 'c': 
        targetUd = 90; 
        targetLr = 90; 
        break;
    }
  }

  unsigned long now = millis();
  if (now - lastUpdate > updateDelay) {
    lastUpdate = now;

    if (udPos != targetUd) {
      udPos += (targetUd > udPos) ? stepSize : -stepSize;
      udPos = constrain(udPos, 0, 180);
      upDown.write(udPos);
    }

    if (lrPos != targetLr) {
      lrPos += (targetLr > lrPos) ? stepSize : -stepSize;
      lrPos = constrain(lrPos, 0, 180);
      leftRight.write(lrPos);
    }
  }
}
