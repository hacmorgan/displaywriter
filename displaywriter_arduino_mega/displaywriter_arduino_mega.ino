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


/* In debug mode, send raw key voltages to host machine rather than pressed/released key
   index. This is required for some debugging modes of the receiver. */
/* bool DEBUG_MODE = true; */
bool DEBUG_MODE = false;


// Input and output pins
const byte ROWS = 8;
const byte COLUMNS = 12;
const byte ROW_PIN[] = {A0, A1, A2, A3, A4, A5, A6, A7};
const byte COL_PIN[] = {22, 24, 26, 28, 30, 32, 34, 36, 38, 40, 42, 44};


// Key state
const byte nonexistent_keys[] = {  // Not all columns have 8 keys, these indices will always read high.
  2,
  12, 13, 14,
  26, 33,
  36, 45,
  60, 61, 69,
  81
};
const int num_nonexistent_keys = sizeof(nonexistent_keys) / sizeof(nonexistent_keys[0]);
byte debounce_time = 5;  // How many consecutive redings below threshold before a key is considered released.
byte key_state[ROWS][COLUMNS];  // Stores whether each key is currently pressed
int key_voltage[ROWS][COLUMNS];  // Stores an analog scan of the keyboard
bool key_exists[ROWS][COLUMNS];  // Quickly check whether a given key index actually exists.


// Key detection
const int default_voltage_threshold = 20;  // A key that measures above this voltage is considered pressed
const int special_voltage_thresholds[][2] = {
  { 0, 600},
  {50, 120},
};
const int num_special_voltage_thresholds = sizeof(special_voltage_thresholds) / (sizeof(special_voltage_thresholds[0][0]) * 2);
int voltage_threshold[ROWS][COLUMNS];  // Allows for custom voltage thresholds


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
   *
   * Experimentally, the best value for this application is 16 or 32.
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


byte key_index(byte row, byte col)
{
  return row * COLUMNS + col;
}


bool check_key_exists(byte row, byte col)
{
  /**
   * Check if a key exists at a given position in the keyboard matrix.
   */
  byte key_idx = key_index(row, col);
  for (byte i = 0; i < num_nonexistent_keys; i++) {
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


int voltage_threshold_for_key(byte row, byte col)
{
  /**
   * Find the voltage threshold for key
   */
  byte key_idx = key_index(row, col);
  for (int i = 0; i < num_special_voltage_thresholds; i++) {
    if (special_voltage_thresholds[i][0] == key_idx) {
      return special_voltage_thresholds[i][1];
    }
  }
  return default_voltage_threshold;
}


void fill_voltage_thresholds()
{
  /**
   * Fill out the voltage threshold map.
   */
  for (byte row = 0; row < ROWS; row++) {
    for (byte col = 0; col < COLUMNS; col++) {
      voltage_threshold[row][col] = voltage_threshold_for_key(row, col);
    }
  }
}


void clear_key_state()
{
  /**
   * Clear the key state array, to make sure all keys are assumed unpressed.
   */
  for (byte row = 0; row < ROWS; row++) {
    for (byte col = 0; col < COLUMNS; col++) {
      key_state[row][col] = 0;
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
   * Sending data to the host machine is done after a scan is completed, as the measured
   * voltages are noisier if we try to send serial data during the scan.
   */
  for (int row = 0; row < ROWS; row++)
  {
    for (int col = 0; col < COLUMNS; col++)
    {
      pulse_column(col);
      key_voltage[row][col] = analogRead(ROW_PIN[row]);
    }
  }
}


void send_scan_to_host()
{
  /**
   * Send scan data to the host machine.
   *
   * In debug mode: send measured voltage of each key.
   * In normal operation: only send messages when a key is pressed or released.
   */
  for (int row = 0; row < ROWS; row++) {
    for (int col = 0; col < COLUMNS; col++) {
      if (DEBUG_MODE) {
        Serial.print(key_voltage[row][col]);
        Serial.print(",");
      } else {
        if (!key_exists[row][col]) {
          continue;
        }
        if (key_state[row][col] == 0 && key_voltage[row][col] > voltage_threshold[row][col]) {
          key_state[row][col] = debounce_time;
          Serial.print(row * COLUMNS + col);  // key index
          Serial.println(",1");  // 1 -> pressed
        } else if (key_state[row][col] > 0 && key_voltage[row][col] < voltage_threshold[row][col]) {
          key_state[row][col]--;
          if (key_state[row][col] <= 0) {
            key_state[row][col] = 0;
            Serial.print(row * COLUMNS + col);  // key index
            Serial.println(",0");  // 0 -> unpressed
          }
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
  fill_voltage_thresholds();
  Serial.begin(115200);
}


void loop()
{
  scan_keyboard();
  send_scan_to_host();
}
