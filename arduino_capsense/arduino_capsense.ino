/**
 * Detect whether a single key has been pressed on an IBM Beam Spring keyboard
 *
 * @author  Hamish Morgan
 * @date    16/01/2021
 * @license BSD
 */


// Clock output pin
#ifdef __AVR_ATmega2560__
  const byte CLOCKOUT = 11;  // Mega 2560
#else
  const byte CLOCKOUT = 9;   // Uno, Duemilanove, etc.
#endif

// Sense pins
const byte COMPARATOR_OUT = 4;

// Timing variables
volatile unsigned long start_time = 0;
volatile unsigned long end_time = 0;


void setup_clockout()
{
  /**
   * Configure the arduno to output the clock signal
   */
  // set up 8 MHz timer on CLOCKOUT (OC1A)
  pinMode (CLOCKOUT, OUTPUT); 
  // set up Timer 1
  TCCR1A = bit (COM1A0);  // toggle OC1A on Compare Match
  TCCR1B = bit (WGM12) | bit (CS10);   // CTC, no prescaling
  OCR1A = 256;       // output every 256th cycle
}


void setup_sense_pin(byte sense_pin)
{
  /**
   * Configure the sensing pin
   */
  pinMode(sense_pin, INPUT_PULLUP);
}


void setup()
{
  setup_clockout();
  setup_sense_pin(COMPARATOR_OUT);
  Serial.begin(38400);
}


void loop()
{
  if (digitalRead(COMPARATOR_OUT) == HIGH) {
    Serial.print(micros());
    Serial.println("Key pressed!");
  }
  delay(100);
}


void rise()
{
  start_time = micros();
}


void fall()
{
  end_time = micros();
  
}
