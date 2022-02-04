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
bool analog_read = true;

// Size of data to be sent
int message_size = 129;  // according to python

// defines for setting and clearing register bits
#ifndef cbi
#define cbi(sfr, bit) (_SFR_BYTE(sfr) &= ~_BV(bit))
#endif
#ifndef sbi
#define sbi(sfr, bit) (_SFR_BYTE(sfr) |= _BV(bit))
#endif


void set_analog_read_speed()
{
  /**
   * Set ADC prescale to 32 -> speeds up analogRead
   *
   * The ADC prescale sets the division ratio of the system clock to the ADC.
   * Smaller values read faster but less accurately. The default is 128
   *
   * We do this by setting the 3 bits of ADPS. The ADC prescale is given by 2**ADPS,
   * so ADPS = 0b101 -> 2**5 == 32
   */
  sbi(ADCSRA, ADPS2);
  cbi(ADCSRA, ADPS1);
  sbi(ADCSRA, ADPS0);
}


void setup_pins()
{
  /**
   * Configure the pins
   */
  set_analog_read_speed();
  
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
      digitalWrite(COL_PIN[col], HIGH);
      digitalWrite(COL_PIN[col], LOW);
      /* pulse_pin(COL_PIN[col]); */
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
        Serial.print(",");
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
  scan_keyboard(analog_read=analog_read);
  send_scan_to_pc(analog_read=analog_read);
}
