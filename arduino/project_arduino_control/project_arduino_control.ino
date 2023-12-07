#include <Adafruit_NeoPixel.h>

#define DIR_PIN 19  // Direction pin
#define STEP_PIN 18 // Step pin
#define STEPS_PER_REV 200 // Change this to fit the number of steps per revolution for your motor

#define PIN_NEO_PIXEL  5  // pin 11 connected to NeoPixel
#define NUM_PIXELS     100  // The number of LEDs (pixels) on NeoPixel

Adafruit_NeoPixel strip(NUM_PIXELS, PIN_NEO_PIXEL, NEO_GRB + NEO_KHZ800);

long ang = 0;
int delaytime = 1000;


void blue_green_gradient(int all_on=0) {
  strip.clear();
  for (int i = 0; i < NUM_PIXELS; i++) {
    int greenValue = map(i, 0, NUM_PIXELS / 2, 255, 0);
    int blueValue = map(i, 0, NUM_PIXELS / 2, 0, 255);
    
    strip.setPixelColor(i, strip.Color(0, greenValue, blueValue));
    strip.show();
    delay(50); 
  }
  for (int i = 0; i < NUM_PIXELS; i++) {
    
    strip.setPixelColor(NUM_PIXELS - i - 1, strip.Color(0, 0, 0));
    strip.show();
    delay(50); 
  }
}

void set_strip(int pixel, int R, int G, int B) {
  strip.setPixelColor(pixel, strip.Color(R, G, B));
  strip.show();
}

void setup() {
  pinMode(DIR_PIN, OUTPUT);
  pinMode(STEP_PIN, OUTPUT);
  Serial.begin(115200);
  strip.begin();
}

void loop() {
//  TODO: remove
  while (true)
    blue_green_gradient(0);
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n'); // Read the command from serial
    //    L:<Pixel Number>:R:G:B     -- 3 per digit
    if ((char) command[0] == 'L') {
      int pixel = command.substring(2, 5).toInt();
      int R = command.substring(6, 9).toInt();
      int G = command.substring(10, 13).toInt();
      int B = command.substring(14, 17).toInt();
      set_strip(pixel, R, G, B);
    } else {
      readSerial(command, &ang, &delaytime);
      rotate(ang, delaytime);
    }
  }
}

// +:000360:01000


void readSerial(String command, long * ang, int * delaytime) {
  command.trim(); // Trim any whitespace

  if (command.length() >= 1 + 1 + 6 + 1 + 5) {
    int multiplier = ((char) command[0]) == '+' ? 1 : -1; // Get the direction, + or -
    
    long steps = command.substring(2, 8).toInt(); // Get the 6 digit number

    *ang = multiplier * steps;
    
    *delaytime = command.substring(9, 14).toInt();
  
    Serial.printf("Got Command: Angle: %d, delay: %d\n", *ang,*delaytime);
  } else {
    Serial.println("Invalid command format. Use <+/->:<6 digit number>");
  }
}

void rotate(long ang, int delaytime) {
  int dir = ang < 0;
  digitalWrite(DIR_PIN, dir); // Set the direction

  int ang_pos = ang < 0 ? ang * -1 : ang;

  long n_steps = (ang_pos * STEPS_PER_REV) / 360;
  for (long i = 0; i < n_steps; i++) {
    digitalWrite(STEP_PIN, HIGH);
    delayMicroseconds(delaytime);
    digitalWrite(STEP_PIN, LOW);
    delayMicroseconds(delaytime);
  }
}
