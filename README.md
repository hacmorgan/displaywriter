
DisplayWriter
=============

Arduino-based control system for an IBM DisplayWriter word processor system's keyboard.

This project is intended to be as electronically simple as possible, and is generally oversimplified. A much better technical reference is Tom Wong-Cornall (xwhatsit)'s DisplayWriter keyboard controller:
- [Installation instructions](https://static.wongcornall.com/ibm-capsense-usb/installation_displaywriter.pdf?utm_source=pocket_mylist)
- [Circuit diagram](https://static.wongcornall.com/ibm-capsense-usb-web/img/beamspring-usb_rev4_schem.png)
- [Project write-up](https://static.wongcornall.com/ibm-capsense-usb-web/ibm-capsense-usb.html)


# Overview
This system replaces the original IBM controller. It utilises an Arduino Mega's 8 analog input pins (rows) and 12 of its output pins (columns), along with some LM339N comparators and a relatively small amount of circuitry, to scan the keyboard. It seems that other beamspring keyboards and even other displaywriter keyboards have only 4 rows, which may make it feasible to use a smaller Arduino for such keyboards, but I can't confirm that.

After the keyboard has been scanned, the Arduino sends an analog voltage reading (as an integer in the range [0, 1023]) for each key to the host machine. It is up to the receiver software running on the host machine to analyse those readings and send keypresses accordingly. As such, this system is only usable on a machine with another keyboard attached. With that said, by hooking the receiver into the init system (in my case `systemd`) to run automatically on startup, I am able to log into my machine and use it without a second keyboard attached.


# Circuitry
TODO


# Software
TODO
