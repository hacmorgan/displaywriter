/**
 * @file
 *
 * Arduino interface for the IBM DisplayWriter (capacitive beam-spring) keyboard.
 *
 * @author Hamish Morgan
 * @date   09/01/2021
 */


/// Test pins
const int VOutPin = A2;
const int CapacitorVoltagePin = A0;

/// Basic values
const int KeyPressedTime = 500;  // key is down if charge time > this value
const int TargetVoltage = 1.0;

/// Capacitor monitoring
unsigned long time = 0;
float capacitorVoltage = 0;


/**
 * Drain capacitor
 */
void drainCapacitor()
{
  digitalWrite(VOutPin, LOW);
  delay(1);
}


/**
 * Find how long it takes for the capacitor to reach 50% charge
 */
int printChargeTime()
{
  time = micros();

  digitalWrite(VOutPin, HIGH);

  while (true) {
    capacitorVoltage = analogRead(CapacitorVoltagePin) / 1024.0 * 5.0;
    if (capacitorVoltage > (TargetVoltage / 5 * 1024)) {
      break;
    }
    /* Serial.print("Capacitor Voltage: "); */
    /* Serial.print(capacitorVoltage); */
    /* Serial.println("V"); */
  }
  
  time = micros() - time;

  digitalWrite(VOutPin, LOW);

  /* if (time > KeyPressedTime) { */
  /*   Serial.print("Key pressed!"); */
  /*   Serial.println(millis()); */
  /* } */
  
  Serial.print("Capacitor voltage took ");
  Serial.print(time);
  Serial.println(" microseconds to charge.");
}


void setup()
{
  Serial.begin(9600);
  
  pinMode(VOutPin, OUTPUT);
  pinMode(CapacitorVoltagePin, INPUT);

  drainCapacitor();
}


void loop()
{
  printChargeTime();
  /* delay(2); */
}
