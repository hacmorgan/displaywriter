
DisplayWriter
=============

Arduino-based control system for an IBM DisplayWriter word processor system's keyboard.

This project is intended to be as electronically simple as possible, and is generally oversimplified. A much better technical reference is Tom Wong-Cornall (xwhatsit)'s DisplayWriter keyboard controller documentation. It was indispensable for the development of this project, with the most useful parts being:
- [Installation instructions](https://static.wongcornall.com/ibm-capsense-usb/installation_displaywriter.pdf?utm_source=pocket_mylist)
- [Circuit diagram](https://static.wongcornall.com/ibm-capsense-usb-web/img/beamspring-usb_rev4_schem.png)
- [Project write-up](https://static.wongcornall.com/ibm-capsense-usb-web/ibm-capsense-usb.html)


# Overview
This system replaces the original IBM controller. It utilises:
- An Arduino Mega for 12 of its output pins (to pulse the keyboard's columns) and its 8 analog input pins (to read the keyboard's rows)
- Two LM339N comparators, each handling 4 of the keyboard's 8 rows.
- Some resistors, a potentiometer, and some capacitors.
- Python code running on the host machine to read messages from the arduino over serial and generate keypresses.

It seems that other beamspring keyboards and maybe even other displaywriter keyboards have only 4 rows, which may make it feasible to use e.g. an Arduino Leonardo to present to the OS as a USB keyboard and do away with the Python receiver code entirely.

I considered using a separate Arduino Leonardo, or the [HoodLoader2](https://github.com/NicoHood/HoodLoader2) bootloader to do this, but found the receiver code is reliable and seamless when hooked into my init system, and I would prefer to keep the project simple. With this said, it does help to have a spare keyboard to get into the motherboard's UEFI setup or select a different boot device!


# Circuitry
TODO


# Software
TODO
