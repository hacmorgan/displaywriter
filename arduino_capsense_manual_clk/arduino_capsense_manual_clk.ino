/**
 * Run the shift register
 *
 * @author  Hamish Morgan
 * @date    16/01/2021
 * @license BSD
 */


/* // Clock output pin */
/* #ifdef __AVR_ATmega2560__ */
/*   const byte CLOCKOUT = 11;  // Mega 2560 */
/* #else */
/*   const byte CLOCKOUT = 9;   // Uno, Duemilanove, etc. */
/* #endif */

// Shift register control pins
const byte SHIFT_A = A0;
const byte SHIFT_CLOCK = A2;
const byte SHIFT_RESET = A5;

// Comparator output pins
const byte ROW_PIN = 4;
const byte ANALOG_PIN = A3;

// Key states
byte key_state = 0;
int cap_voltage = 0;
/* const byte ROWS = 8; */
/* const byte COLUMNS = 12; */
/* byte key_state[ROWS][COLUMNS]; */


void setup()
{
  /* setup_clockout(); */
  setup_pins();
  Serial.begin(38400);
}


void loop()
{
  /* reset_key_state(); */
  scan_keyboard();
  /* print_keyboard(); */
  /* delay(500); */
}


/* void setup_clockout() */
/* { */
/*   /\** */
/*    * Configure the arduno to output the clock signal */
/*    *\/ */
/*   // set up 8 MHz timer on CLOCKOUT (OC1A) */
/*   pinMode (CLOCKOUT, OUTPUT);  */
/*   // set up Timer 1 */
/*   TCCR1A = bit (COM1A0);  // toggle OC1A on Compare Match */
/*   TCCR1B = bit (WGM12) | bit (CS10);   // CTC, no prescaling */
/*   OCR1A =  65000;       // output every 256th cycle */
/* } */


void setup_pins()
{
  /**
   * Configure the pins
   */
  pinMode(SHIFT_A, OUTPUT);
  pinMode(SHIFT_CLOCK, OUTPUT);
  pinMode(SHIFT_RESET, OUTPUT);
  
  digitalWrite(SHIFT_A, LOW);
  digitalWrite(SHIFT_CLOCK, LOW);
  digitalWrite(SHIFT_RESET, HIGH);  // active low

  pinMode(ROW_PIN, INPUT);
  /* pinMode(ANALOG_PIN, INPUT);  // Use external pullup resistor, > 20k (maybe 50k?) */
}


/* void reset_key_state() */
/* { */
/*   /\** */
/*    * Reset the key_state array to all zeros */
/*    *\/ */
/*   for (int row = 0; row < ROWS; row++) { */
/*     for (int col = 0; col < COLUMNS; col++) { */
/*       key_state[row][col] = 0; */
/*     } */
/*   } */
/* } */


void reset_row()
{
  /**
   * Stop the clock and reset the shift register
   */
  digitalWrite(SHIFT_CLOCK, LOW);
  digitalWrite(SHIFT_RESET, LOW);  // active low
  digitalWrite(SHIFT_RESET, HIGH);
  digitalWrite(SHIFT_A, HIGH);
}


void pulse_clock()
{
  digitalWrite(SHIFT_CLOCK, HIGH);
  digitalWrite(SHIFT_CLOCK, LOW);
}


void scan_keyboard()
{
  /**
   * Scan the keyboard
   */
  pulse_clock();
  key_state = digitalRead(ROW_PIN);
  /* cap_voltage = analogRead(ANALOG_PIN); */
  /* Serial.print("Capacitor voltage: "); */
  /* Serial.println(cap_voltage); */
  if (key_state == HIGH) {
    Serial.print(micros());
    Serial.println(" Key pressed!");
  }
  /* delayMicroseconds(10); */
}


/* void print_keyboard() */
/* { */
/*   /\** */
/*    * Print a visual representation of the keyboard state to the serial console */
/*    *\/ */
/*   for (int row = 0; row < ROWS; row++) { */
/*     for (int col = 0; col < COLUMNS; col++) { */
/*       if (key_state[row][col]) { */
/*         Serial.print("*"); */
/*       } else { */
/*         Serial.print("_"); */
/*       } */
/*     } */
/*     Serial.println(); */
/*   } */
/*   Serial.println("\n"); */
/* } */
