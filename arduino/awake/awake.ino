 /* awake
  by Kyungwon Chun <kwchun@biobrain.kr>
  Mon. Aug. 12, 2019

  Move servo as an actuator every random period to keep 
  awake the Oculus DK.
*/

#include <Servo.h>

Servo stimulant;  // create servo object to control a servo

int MIN_ANGLE = 30; // degree
int MAX_ANGLE = 150; // degree
long PERIOD = 1L * 60L * 1000L; // milliseconds
long MOVING_PERIOD = 1000L; // milliseconds
bool go_max = true;
long alarm; // random value

void setup() {
  Serial.begin(9600); // open the serial port at 9600 bps:
  
  // input pin 0 is unconnected to get random analog noise
  // which causes the call to randomSeed() to generate
  // different seed numbers each time the sketch runs.
  randomSeed(analogRead(0));

  // the signal pin of servo should be attached to pin 9
  stimulant.attach(9);
  stimulant.write(MIN_ANGLE);
}

void loop() {
  Serial.print("PERIOD: ");
  Serial.println(PERIOD);
  
  alarm = random(PERIOD - MOVING_PERIOD);
  
  Serial.print("alarm: ");
  Serial.println(alarm);
  
  delay(alarm);

  if (go_max) {
    stimulant.write(MAX_ANGLE);  // tell servo to go to position in variable 'pos'
    go_max = false;
  } else {
    stimulant.write(MIN_ANGLE);
    go_max = true;
  }
  
  Serial.print("MOVING_PERIOD: ");
  Serial.println(MOVING_PERIOD);
  
  delay(MOVING_PERIOD);  // waits 1s for the servo to reach the position
   
  Serial.print("residual: ");
  Serial.println(PERIOD - alarm - MOVING_PERIOD);
  delay(PERIOD - alarm - MOVING_PERIOD);
}
