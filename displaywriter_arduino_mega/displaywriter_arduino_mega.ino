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


/* In Normal mode, only communicate with the host machine when a key is pressed or released */
bool DEBUG_MODE = false;

/* In debug mode, send every voltage of each scan to host machine as 96 comma-separated integers */
/* bool DEBUG_MODE = true; */


// Input and output pins
const byte ROWS = 8;
const byte COLUMNS = 12;
const byte ROW_PIN[] = {A0, A1, A2, A3, A4, A5, A6, A7};
const byte COL_PIN[] = {22, 24, 26, 28, 30, 32, 34, 36, 38, 40, 42, 44};


// Key state
const byte nonexistent_keys[] = {  // Not all columns have 8 keys, these indices will always read high.
  2,
  12, 13, 14,
  26,
  33, 36,
  45,
  60, 61, 69,
  81
};
const int num_nonexistent_keys = sizeof(nonexistent_keys) / sizeof(nonexistent_keys[0]);
byte debounce_time = 5;  // How many consecutive redings below threshold before a key is considered released.
byte key_debounce_count[ROWS][COLUMNS];  // Stores whether each key is currently pressed
int key_voltage[ROWS][COLUMNS];  // Stores an analog scan of the keyboard
bool key_exists[ROWS][COLUMNS];  // Quickly check whether a given key index actually exists.
int OTHER_KEYS_PRESSED_THRESHOLD_INCREASE = 100;


// Key detection
const int default_voltage_threshold = 130;  // A key that measures above this voltage is considered pressed
const int special_voltage_thresholds[][2] = {
  {0,  600},  // left fn key modifier
  {3,  220},  // 1
  {29, 260},  // g
  {30, 320},  // j
  {32, 320},  // '
  {38, 500},  // left_alt
  /* {44, 320},  // right_alt */
  {58, 40},  // down
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
   * Set ADC prescale to speed up analogRead()
   *
   * The ADC prescale sets the division ratio of the system clock to the ADC.
   * Smaller values read faster but less accurately. The default (and maximum) is 128.
   *
   * We do this by setting the 3 bits of ADPS. The ADC prescale is given by 2^ADPS,
   * so ADPS = 0b101 == 5 -> 2^5 == 32
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
  /**
   * Calculate the index of a key by its row and column.
   */
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


void initialise_arrays()
{
  /**
   * Initialise all of the 96-element mapping variables (one element for each key).
   */
  for (byte row = 0; row < ROWS; row++) {
    for (byte col = 0; col < COLUMNS; col++) {
      key_voltage[row][col] = 0;
      key_debounce_count[row][col] = 0;
      key_exists[row][col] = check_key_exists(row, col);
      voltage_threshold[row][col] = voltage_threshold_for_key(row, col);
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
      if (key_exists[row][col]) {
        pulse_column(col);
        key_voltage[row][col] = analogRead(ROW_PIN[row]);
      }
    }
  }
}


bool key_pressed(byte row, byte col)
{
  /**
   * Check whether a key has just been pressed
   *
   * Only returns true if the key was unpressed last time we checked. Key threshold is increased if any other keys in the row/column are also pressed
   */
  int threshold = voltage_threshold[row][col] +
    any_keys_pressed(row, col) * OTHER_KEYS_PRESSED_THRESHOLD_INCREASE;
  return key_debounce_count[row][col] == 0 &&
    key_voltage[row][col] > threshold;
}


bool key_released(byte row, byte col)
{
  /**
   * Check whether a key has just been released
   *
   * Only returns true if the key was pressed last time we checked
   */
  return key_debounce_count[row][col] > 0 &&
    key_voltage[row][col] < voltage_threshold[row][col];
}


bool any_keys_pressed(byte row, byte col)
{
  /**
   * Check if any keys in row or col are also currently pressed.
   */
  for (byte r = 0; r < ROWS; r++) {
    if (key_debounce_count[r][col] > 0) {
      return true;
    }
  }
  for (byte c = 0; c < COLUMNS; c++) {
    if (key_debounce_count[row][c] > 0) {
      return true;
    }
  }
  return false;
}


void send_key_pressed(byte row, byte col)
{
  /**
   * Send the "key pressed" message to the host machine for a key.
   */
  Serial.print(key_index(row, col));
  Serial.println(",1");  // 1 -> pressed
}


void send_key_released(byte row, byte col)
{
  /**
   * Send the "key released" message to the host machine for a key.
   */
  Serial.print(key_index(row, col));
  Serial.println(",0");  // 0 -> unpressed
}


void send_debug_voltage(byte row, byte col)
{
  /**
   * Send the analog voltage of a key to the host machine.
   */
  Serial.print(key_voltage[row][col]);
  Serial.print(",");
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
      if (!DEBUG_MODE) {
        if (!key_exists[row][col]) {
          continue;
        }
        if (key_pressed(row, col)) {
          key_debounce_count[row][col] = debounce_time;
          send_key_pressed(row, col);
        }
        else if (key_released(row, col)) {
          key_debounce_count[row][col]--;
          if (key_debounce_count[row][col] <= 0) {
            key_debounce_count[row][col] = 0;
            send_key_released(row, col);
          }
        }
      }
      else {
        send_debug_voltage(row, col);
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
  initialise_arrays();
  Serial.begin(115200);
}


void loop()
{
  scan_keyboard();
  send_scan_to_host();
}
