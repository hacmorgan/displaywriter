/**
 * Scan the keyboard pin by pin.
 *
 * Uses a digital output pin for each column of the keyboard matrix, and an analog
 * input pin for each row. For each key, the arduino pulses the column and reads the
 * analog voltage on the row.
 *
 * This means that, at least for the 8-row displaywriter keyboard, an Arduino Mega is required.
 *
 * @author  Hamish Morgan
 * @date    16/01/2021
 * @license BSD
 */


// Debug mode: send raw key voltages to host machine rather than pressed/released key index.
bool DEBUG_MODE = true;


// Input and output pins
const byte ROWS = 8;
const byte COLUMNS = 12;
const byte ROW_PIN[] = {A0, A1, A2, A3, A4, A5, A6, A7};
const byte COL_PIN[] = {22, 24, 26, 28, 30, 32, 34, 36, 38, 40, 42, 44};


// Key state and detection
int voltage_threshold = 200;  // A key that measures above this voltage is considered pressed
bool key_state[ROWS][COLUMNS];
int key_voltage;
const byte nonexistent_keys[] = {  // Not all columns have 8 keys, these indices will always read high.
  2,
  12, 13, 14,
  26, 33,
  36, 45,
  60, 61, 69,
  81
};
bool key_exists[ROWS][COLUMNS];  // Quickly check whether a given key index actually exists.


// Macros for setting and clearing register bits
#ifndef cbi
#define cbi(sfr, bit) (_SFR_BYTE(sfr) &= ~_BV(bit))
#endif
#ifndef sbi
#define sbi(sfr, bit) (_SFR_BYTE(sfr) |= _BV(bit))
#endif


void set_analog_read_speed()
{
  /**
   * Set ADC prescale to speeds up analogRead
   *
   * The ADC prescale sets the division ratio of the system clock to the ADC.
   * Smaller values read faster but less accurately. The default (and maximum) is 128.
   *
   * We do this by setting the 3 bits of ADPS. The ADC prescale is given by 2^ADPS,
   * so ADPS = 0b101 -> 2^5 == 32
   */
  sbi(ADCSRA, ADPS2);
  cbi(ADCSRA, ADPS1);
  sbi(ADCSRA, ADPS0);
}


void setup_pins()
{
  /**
   * Configure the pins.
   *
   * We will pulse the columns and measure the response in the rows, so the column pins
   * must be output pins, and the row pins must be input pins.
   */
  set_analog_read_speed();

  for (int i = 0; i < COLUMNS; i++) {
    pinMode(COL_PIN[i], OUTPUT);
    digitalWrite(COL_PIN[i], LOW);
  }
  
  for (int i = 0; i < ROWS; i++) {
    pinMode(ROW_PIN[i], INPUT);
  }
}


bool check_key_exists(byte row, byte col)
{
  /**
   * Check if a key exists at a given position in the keyboard matrix.
   */
  byte key_idx = row * COLUMNS + col;
  for (byte i = 0; i < sizeof(nonexistent_keys); i++) {
    if (key_idx == nonexistent_keys[i]) {
      return false;
    }
  }
  return true;
}


void fill_nonexistent_key_map()
{
  /**
   * Fill out nonexistent key map.
   *
   * This provides a quick way to check if a given row/column combination actually has a
   * key, as not all columns have 8 rows attached.
   */
  for (int row = 0; row < ROWS; row++) {
    for (int col = 0; col < COLUMNS; col++) {
      key_exists[row][col] = check_key_exists(row, col);
    }
  }
}


void clear_key_state()
{
  /**
   * Clear the key state array, to make sure all keys are assumed unpressed.
   */
  for (int row = 0; row < ROWS; row++) {
    for (int col = 0; col < COLUMNS; col++) {
      key_state[row][col] = false;
    }
  }
}


void pulse_column(int col)
{
  /**
   * Pulse a column of the keyboard matrix by its index
   */
  digitalWrite(COL_PIN[col], HIGH);
  digitalWrite(COL_PIN[col], LOW);
}


void scan_keyboard()
{
  /**
   * Scan the keyboard and communicate with the host machine.
   *
   * In debug mode: send measured voltage of each key.
   * In normal operation: only send messages when a key is pressed or released.
   */
  for (int row = 0; row < ROWS; row++)
  {
    for (int col = 0; col < COLUMNS; col++)
    {
      pulse_column(col);
      /* digitalWrite(COL_PIN[col], HIGH); */
      /* digitalWrite(COL_PIN[col], LOW); */
      key_voltage = analogRead(ROW_PIN[row]);

      if (DEBUG_MODE)
      {
        Serial.print(key_voltage);
        Serial.print(",");
      }
      else
      {
        if (!key_exists[row][col])
        {
          continue;
        }
      
        if (! key_state[row][col] && key_voltage > voltage_threshold)
        {
          key_state[row][col] = true;
          Serial.print(row * COLUMNS + col);  // key index
          Serial.println(",1");  // 1 -> pressed
        }
        else if (key_state[row][col] && key_voltage < voltage_threshold)
        {
          key_state[row][col] = false;
          Serial.print(row * COLUMNS + col);  // key index
          Serial.println(",0");  // 0 -> unpressed
        }
      }
    }
  }
  if (DEBUG_MODE) {
    Serial.println();
  }
}


void setup()
{
  setup_pins();
  clear_key_state();
  fill_nonexistent_key_map();
  Serial.begin(115200);
}


void loop()
{
  scan_keyboard();
}
