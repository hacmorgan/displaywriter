
DisplayWriter
=============

Arduino-based control system for an IBM DisplayWriter word processor system's keyboard.

This project is intended to be as electronically simple as possible, and is generally oversimplified. A much better technical reference is Tom Wong-Cornall (xwhatsit)'s DisplayWriter keyboard controller documentation. It was indispensable for the development of this project, with the most useful parts being:
- [Installation instructions](https://static.wongcornall.com/ibm-capsense-usb/installation_displaywriter.pdf?utm_source=pocket_mylist)
- [Circuit diagram](https://static.wongcornall.com/ibm-capsense-usb-web/img/beamspring-usb_rev4_schem.png)
- [Project write-up](https://static.wongcornall.com/ibm-capsense-usb-web/ibm-capsense-usb.html)


# Overview
This system replaces the original IBM controller. It utilises an Arduino Mega's 8 analog input pins (rows) and 12 of its output pins (columns), along with some LM339N comparators and a relatively small amount of circuitry, to scan the keyboard. It seems that other beamspring keyboards and even other displaywriter keyboards have only 4 rows, which may make it feasible to use a smaller Arduino for such keyboards, but I can't confirm that.


# Arduino Configuration
This project makes use of Nico Hood's [HoodLoader2 bootloader](https://github.com/NicoHood/HoodLoader2) and [HID API](https://github.com/NicoHood/HID), which allows various Arduinos (including the Mega) to present as a USB keyboard, among many other things. Both projects have their own wikis with installation instructions, but the steps to setup the arduino for this project are outlined below.

## Installing the Hoodloader2 bootloader



# Circuitry
TODO


# Software
TODO
