/**
 * @file
 *
 * Arduino interface for the IBM DisplayWriter (capacitive beam-spring) keyboard.
 *
 * @author Hamish Morgan
 * @date   09/01/2021
 */


/// Test pins
const int CapacitorVoltagePin = A0;
const int ChargePin = A1;
const int DischargePin = A2;

/// Basic values
const int KeyPressedTime = 500;  // key is down if charge time > this value
const int TargetVoltage = 1.0;

/// Capacitor monitoring
unsigned long start_time = 0;
unsigned long elapsed_time = 0;
float capacitorVoltage = 0;


/**
 * Drain capacitor
 */
void drainCapacitor()
{
  digitalWrite(ChargePin, LOW);
  pinMode(DischargePin, OUTPUT);  // Set the discharge pin to output to sink more current
  digitalWrite(DischargePin, LOW);
  while(analogRead(CapacitorVoltagePin) > 0) { ; }
  pinMode(DischargePin, INPUT);  // Set back to input mode, where it won't affect the circuitry.
}


/**
 * Find how long it takes for the capacitor to reach 50% charge
 */
int printChargeTime()
{
  // Charge capacitor
  digitalWrite(ChargePin, HIGH);

  start_time = micros();

  while (analogRead(CapacitorVoltagePin) < 200) { // 647 is 63.2% of 1023
    /* capacitorVoltage =  / 1024.0 * 5.0; */
    /* if (capacitorVoltage > (TargetVoltage / 5 * 1024)) { */
    /*   break; */
    /* } */
    Serial.print("Capacitor Voltage: ");
    Serial.print(analogRead(CapacitorVoltagePin));
    Serial.println("/1023");
  }
  
  elapsed_time = micros() - start_time;

  /* if (time > KeyPressedTime) { */
  /*   Serial.print("Key pressed!"); */
  /*   Serial.println(millis()); */
  /* } */
  
  Serial.print("Capacitor voltage took ");
  Serial.print(elapsed_time);
  Serial.println(" microseconds to charge.");
}


void setup()
{
  Serial.begin(9600);
  
  pinMode(ChargePin, OUTPUT);
  digitalWrite(ChargePin, LOW);

  drainCapacitor();
}


void loop()
{
  printChargeTime();
  drainCapacitor();
}
