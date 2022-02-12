
DisplayWriter
=============

Arduino-based control system for an IBM DisplayWriter word processor system's keyboard.

This project is intended to be as electronically simple as possible, and is generally oversimplified. A much better technical reference is Tom Wong-Cornall (xwhatsit)'s DisplayWriter keyboard controller documentation. It was indispensable for the development of this project, with the most useful parts being:
- [Installation instructions](https://static.wongcornall.com/ibm-capsense-usb/installation_displaywriter.pdf?utm_source=pocket_mylist)
- [Circuit diagram](https://static.wongcornall.com/ibm-capsense-usb-web/img/beamspring-usb_rev4_schem.png)
- [Project write-up](https://static.wongcornall.com/ibm-capsense-usb-web/ibm-capsense-usb.html)


# Overview
This system replaces the original IBM controller. It utilises:
- An Arduino Mega
  - 12 digital output pins (to pulse the keyboard's columns)
  - 8 analog input pins (to read the keyboard's rows)
- Two LM339N quad-comparator chips, each handling 4 of the keyboard's 8 rows.
- Some resistors, a potentiometer, and some capacitors.
- Python code running on the host machine to read messages from the arduino over serial and generate keypresses.

It seems that other beamspring keyboards and maybe even other displaywriter keyboards have only 4 rows, which may make it feasible to use e.g. an Arduino Leonardo to present to the OS as a USB keyboard and do away with the Python receiver code entirely.

I considered using a separate Arduino Leonardo, or the [HoodLoader2](https://github.com/NicoHood/HoodLoader2) bootloader to do this, but found the receiver code is reliable and seamless when hooked into my init system, and I would prefer to keep the project simple. With this said, it does help to have a spare keyboard to get into the motherboard's UEFI setup or select a different boot device.


# Circuitry
TODO


# Software
The Arduino can operate in two modes.

### Normal mode
In normal mode, the arduino scans all 96 combinations of its 12 column outputs and 8 row inputs, assigning an integer index for each key in the order they were scanned. The Displaywriter actually only has 84 keys, so the 12 nonexistent keys are hardcoded to 0.



# Calibrating the keyboard
This system requires some careful calibration to work correctly, primarily concerning:
- the voltage threshold for keys to be considered pressed (in software)
- the reference voltage for the comparators (by adjusting potentiometer)

Once calibrated, the keyboard is responsive and reliable, and should not need further calibration.

## Setting the reference voltage
The voltage reference is set by a voltage divider with a 10K potentiometer in series with the resistor to GND. This could also be done with a DAC, but a POT is simpler and easier to experiment with.

- Ensure the Arduino is in debug mode by setting `DEBUG_MODE = true` at the top of `displaywriter_arduino_mega.ino`.
  - Don't forget to reprogram the Arduino to incorporate this change!
- Run the receiver in raw mode: `sudo displaywriter_receiver.py --raw`

You will see a voltage between 0 and 1023 for each key in the keyboard. Ideally, these values should all be 0 unless the key is pressed. There will be some values that do not go to 0, but this is to be expected. Not every column has 8 keys, so sometimes the arduino will pulse a column and read a row that is not capacitively coupled to that column, producing these high values. For me, a pressed key will have a value around 400 (between 200 and 600 for almost all keys).

## Setting the voltage threshold
With an idea of the voltages we can expect to see when a key is pressed from using the receiver in raw mode, we can now:
- Put the Arduino back in normal mode by setting `DEBUG_MODE = false` in `displaywriter_arduino_mega.ino`.
  - Don't forget to reprogram the Arduino to incorporate this change.
- Run the receiver in dry run mode: `sudo displaywriter_receiver.py --dry-run`

This will print to stdout whenever a key would be pressed, to allow us to find false detections or keys that don't register reliably when pressed. The reference voltage must be set on the arduino, so this may take a few cycles of
- Reprogram Arduino
- Run receiver in dry run mode
- Test the keyboard, observe unresponsive keys and/or keys that trigger when not pressed
- Kill receiver
- Change threshold
- Repeat
