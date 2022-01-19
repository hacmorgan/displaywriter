/**
 * Scan the keyboard pin by pin.
 *
 * @author  Hamish Morgan
 * @date    16/01/2021
 * @license BSD
 */

// Input and output pins
const byte ROWS = 8;
const byte COLUMNS = 12;
const byte ROW_PIN[] = {A0, A1, A2, A3, A4, A5, A6, A7};
const byte COL_PIN[] = {22, 24, 26, 28, 30, 32, 34, 36, 38, 40, 42, 44};

// Key states
int key_state[ROWS][COLUMNS];
float voltage;
bool analog_read = false;

// Size of data to be sent
int message_size = 129;  // according to python 


void setup_pins()
{
  /**
   * Configure the pins
   */
  for (int i = 0; i < COLUMNS; i++) {
    pinMode(COL_PIN[i], OUTPUT);
    digitalWrite(COL_PIN[i], LOW);  // todo: change to high
  }
  
  for (int i = 0; i < ROWS; i++) {
    pinMode(ROW_PIN[i], INPUT);
  }
}


void pulse_pin(byte pin)
{
  digitalWrite(pin, HIGH);
  digitalWrite(pin, LOW);
}


void scan_keyboard(bool analog_read = false)
{
  for (int row = 0; row < ROWS; row++) {
    for (int col = 0; col < COLUMNS; col++) {
      pulse_pin(COL_PIN[col]);
      if (analog_read) {
          key_state[row][col] = analogRead(ROW_PIN[row]);
      } else {
          key_state[row][col] = digitalRead(ROW_PIN[row]);
      }
    }
  }
}


void print_keyboard(bool analog_read = false)
{
  /**
   * Print a visual representation of the keyboard state to the serial console
   */
  for (int row = 0; row < ROWS; row++) {
    for (int col = 0; col < COLUMNS; col++) {
      if (analog_read) {
        voltage = key_state[row][col] / 1023.0 * 5.0;
        Serial.print(voltage, 2);
        Serial.print(" ");
      } else {
        if (key_state[row][col]) {
            Serial.print("*");
        } else {
            Serial.print("_");
        }
      }
    }
    Serial.println();
  }
  Serial.println("\n");
}


void send_scan_to_pc(bool analog_read=true)
{
  for (int row = 0; row < ROWS; row++) {
    for (int col = 0; col < COLUMNS; col++) {
        Serial.print(key_state[row][col]);
        if (analog_read) {
          Serial.print(",");
        }
    }
  }
  Serial.println();
}


void setup()
{
  setup_pins();
  Serial.begin(115200);
}


void loop()
{
  /* while (Serial.availableForWrite() < message_size) { ; } */
  scan_keyboard(analog_read=true);
  send_scan_to_pc(analog_read=true);
}
