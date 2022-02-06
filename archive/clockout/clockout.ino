#ifdef __AVR_ATmega2560__
  const byte CLOCKOUT = 11;  // Mega 2560
#else
  const byte CLOCKOUT = 9;   // Uno, Duemilanove, etc.
#endif

const byte ROW_PIN[] = {4, 5, 6, 7, 10, 11, 12, 13};

void setup ()
{
  // set up 8 MHz timer on CLOCKOUT (OC1A)
  pinMode (CLOCKOUT, OUTPUT); 
  // set up Timer 1
  TCCR1A = bit (COM1A0);  // toggle OC1A on Compare Match
  TCCR1B = bit (WGM12) | bit (CS10);   // CTC, no prescaling
  OCR1A = 1024;       // output every 8th cycle

  for (int i = 0; i < 8; i++) {
    pinMode(ROW_PIN[i], INPUT_PULLUP);  // External 330k pullup resistors used
  }
}  // end of setup

void loop ()
{
  // whatever 
}  // end of loop
