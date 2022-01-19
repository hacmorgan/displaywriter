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
const byte ROW_PIN[] = {4, 5, 6, 7, 10, 11, 12, 13};

// Key states
const byte ROWS = 8;
const byte COLUMNS = 12;
byte key_state[ROWS][COLUMNS];


void setup()
{
  /* setup_clockout(); */
  setup_pins();
  Serial.begin(38400);
}


void loop()
{
  reset_key_state();
  scan_keyboard();
  /* print_keyboard(); */
  /* delay(5); */
}


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

  for (int i = 0; i < 8; i++) {
    pinMode(ROW_PIN[i], INPUT_PULLUP);  // External 330k pullup resistors used
  }
}


void reset_key_state()
{
  /**
   * Reset the key_state array to all zeros
   */
  for (int row = 0; row < ROWS; row++) {
    for (int col = 0; col < COLUMNS; col++) {
      key_state[row][col] = 0;
    }
  }
}


void reset_column()
{
  /**
   * Stop the clock and reset the shift register
   */
  digitalWrite(SHIFT_CLOCK, LOW);
  digitalWrite(SHIFT_RESET, LOW);  // active low
  digitalWrite(SHIFT_RESET, HIGH);
  digitalWrite(SHIFT_A, HIGH);
  pulse_clock();
  digitalWrite(SHIFT_A, LOW);
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
  for (int row = 0; row < ROWS; row++) {
    reset_column();
    for (int col = 0; col < COLUMNS; col++) {
      digitalWrite(SHIFT_CLOCK, HIGH);
      key_state[row][col] = digitalRead(ROW_PIN[row]);
      digitalWrite(SHIFT_CLOCK, LOW);
    }
  }
}


void print_keyboard()
{
  /**
   * Print a visual representation of the keyboard state to the serial console
   */
  for (int row = 0; row < ROWS; row++) {
    for (int col = 0; col < COLUMNS; col++) {
      if (key_state[row][col]) {
        Serial.print("*");
      } else {
        Serial.print("_");
      }
    }
    Serial.println();
  }
  Serial.println("\n");
}
