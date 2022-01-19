#!/usr/bin/env python3


"""
@file

Convert raw signal from arduino into keystrokes.

@author  Hamish Morgan
@date    20/01/2021
@license BSD
"""


import sys

from typing import Iterator

import keyboard
import numpy as np
import serial


"""
Position indices of each key's character in the string received from the arduino.
"""
KEYS = {
    # Modifiers & control keys
    93: {"name": "left_alt"},
    87: {"name": "right_alt"},
    94: {"name": "space"},
    9: {"name": "left shift"},
    2: {"name": "right shift"},
    8: {"name": "ctrl"},  # ¶ (pilcrow) key
    33: {"name": "tab"},
    50: {"name": "backspace"},
    62: {"name": "return"},
    # Arrows
    73: {"name": "up"},
    13: {"name": "down"},
    85: {"name": "left"},
    1: {"name": "right"},
    # Nav cluster
    49: {"name": "delete"},  # (del)
    61: {"name": "insert"},  # (chg fmt/instr)
    37: {"name": "home"},  # (move/copy)
    25: {"name": "end"},  # (get)
    48: {"name": "page up"},  # (line adj)
    60: {"name": "page down"},  # (page end/reqd)
    # Number row
    56: {"name": "1"},
    44: {"name": "2"},
    55: {"name": "3"},
    43: {"name": "4"},
    54: {"name": "5"},
    42: {"name": "6"},
    53: {"name": "7"},
    41: {"name": "8"},
    52: {"name": "9"},
    40: {"name": "0"},
    # Alphabet
    68: {"name": "q"},
    # 32: {"name": "w"},  # a guess, not registering properly
    34: {"name": "w"},  # temp w, left of tab
    67: {"name": "e"},
    31: {"name": "r"},
    66: {"name": "t"},
    30: {"name": "y"},
    65: {"name": "u"},
    29: {"name": "i"},
    64: {"name": "o"},
    28: {"name": "p"},
    80: {"name": "a"},
    20: {"name": "s"},
    79: {"name": "d"},
    19: {"name": "f"},
    78: {"name": "g"},
    18: {"name": "h"},
    77: {"name": "j"},
    17: {"name": "k"},
    76: {"name": "l"},
    92: {"name": "z"},
    7: {"name": "x"},
    91: {"name": "c"},
    6: {"name": "v"},
    90: {"name": "b"},
    5: {"name": "n"},
    89: {"name": "m"},
    # Punctuation
    45: {"name": "`"},  # ±/° (plus minus/degrees) key
    88: {"name": "."},
    4: {"name": ","},
    3: {"name": "/"},
    # 75: {"name": "'"},  # registers when not pressed
    38: {"name": "\\"},  # (index)
    16: {"name": ";"},
    15: {"name": "'"},  # (3 2), until 75 works
    63: {"name": "["},  # (1/4 1/2)
    27: {"name": "]"},  # ([ ])
    51: {"name": "-"},
    39: {"name": "="},
}
NUM_KEYS = 96;


KeyScan = str


def read_keyscans(
    device: str = "/dev/ttyACM0",
    baudrate: int = 115200,
) -> Iterator[KeyScan]:
    """
    Read keyscans from arduino over serial.
    """
    with serial.Serial(port=device, baudrate=baudrate, timeout=1.0) as ser:
        while True:
            line = str(ser.readline().strip(), "UTF-8")
            if line:
                voltages = line.split(",")[:-1]
                if len(voltages) < NUM_KEYS:
                    continue
                # print(len(line.split(",")[:-1]), file=sys.stderr)
                yield [int(voltage) for voltage in line.split(",")[:-1]]


def calibrate_keyboard(samples: int = 100):
    """
    Read the keyboard for a while to determine expected voltages on each key.
    """
    print("Calibrating keyboard...", file=sys.stderr)
    nominal_voltages = {}
    for idx in KEYS:
        nominal_voltages[idx] = []
    for _, keyscan in zip(range(samples), read_keyscans()):
        for idx in KEYS:
            nominal_voltages[idx].append(keyscan[idx])
    for idx in KEYS:
        KEYS[idx]["nominal_voltage"] = np.mean(nominal_voltages[idx])
        KEYS[idx]["voltage_std_dev"] = np.std(nominal_voltages[idx])
    print("Calibration complete!", file=sys.stderr)


def press_keys(keyscan: KeyScan, pressed_keys: set, dry_run: bool = False) -> None:
    """
    Press/release keys as appropriate.
    """
    for idx, voltage in enumerate(keyscan):
        if idx in KEYS:
            vdiff = voltage - KEYS[idx]["nominal_voltage"]
            # if vdiff > 2 * KEYS[idx]["voltage_std_dev"]:
            if vdiff > 150:
                if dry_run:
                    print(f"Pressing: {KEYS[idx]}")
                else:
                    keyboard.press(KEYS[idx]["name"])
                    pressed_keys.add(idx)
        if idx in pressed_keys and state == 0:
            if dry_run:
                print(f"Releasing: {KEYS[idx]}")
            else:
                keyboard.release(KEYS[IDX]["name"])
                pressed_keys.remove(idx);


def check_dry_run() -> bool:
    """
    Check if --dry-run given as arg
    """
    return any(dryrun in sys.argv for dryrun in ("--dry-run", "-d"))
                

def main() -> int:
    pressed_keys = set()
    calibrate_keyboard()
    for keyscan in read_keyscans():
        press_keys(keyscan, pressed_keys, check_dry_run())
    return 0


if __name__ == "__main__":
    sys.exit(main())
