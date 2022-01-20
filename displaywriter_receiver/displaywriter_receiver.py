#!/usr/bin/env python3


"""
@file

Convert raw signal from arduino into keystrokes.

@author  Hamish Morgan
@date    20/01/2021
@license BSD
"""


import json
import sys
import time

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
    21: {"name": "caps lock"},
    8: {"name": "ctrl"},  # ¶ (pilcrow) key
    33: {"name": "tab"},
    50: {"name": "backspace"},
    62: {"name": "return"},
    47: {"name": "escape"},
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
    32: {"name": "w"},  # a guess, not registering properly
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
    15: {"name": "\\"},  # (3 2), until 75 works
    3: {"name": "/"},
    75: {"name": "'"},  # registers when not pressed
    # 38: {"name": "\\"},  # (index)
    16: {"name": ";"},
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
            voltage_bytestrings = ser.readline().strip().split(b",")[:-1]
            if len(voltage_bytestrings) != NUM_KEYS:
                continue
            try:
                yield [int(voltage) for voltage in voltage_bytestrings]
            except ValueError:
                continue


def measure_voltages(samples: int = 25) -> tuple[list[int], list[int]]:
    """
    Measure the voltages of each key over a period of time

    @param[in] samples How many times to sample the keyboard
    @retval Mean voltage for each key
    @retval Stddev voltage for each key
    """
    voltages = np.zeros((samples, NUM_KEYS), dtype=int)
    for idx, keyscan in zip(range(samples), read_keyscans()):
        voltages[idx, :] = keyscan
    return np.mean(voltages, axis=0), np.std(voltages, axis=0)


def detect_likely_keys() -> None:
    print("Measuring baseline voltages in 3s... don't press any keys!")
    time.sleep(3)
    print("Measuring baseline voltages...")
    mean_voltages, stddev_voltages = measure_voltages()
    print("Done!")
    while True:
        new_mean_voltages, new_stddev_voltages = measure_voltages()
        mean_voltage_diffs = new_mean_voltages - mean_voltages
        for order, idx in zip(range(10), reversed(np.argsort(mean_voltage_diffs))):
            print(f"{order}th biggest vdiff: {mean_voltage_diffs[idx]} (key index: {idx})")
        print("\n")
    

            
def calibrate_keyboard(calibration_file = "calibration.json", samples: int = 50):
    """
    Read the keyboard for a while to determine expected voltages on each key.
    """
    print("Calibrating keyboard...", file=sys.stderr)

    print("Measuring key voltages unpressed...", file=sys.stderr)
    mean_voltages, stddev_voltages = measure_voltages()
    for idx in KEYS:
        KEYS[idx]["nominal_unpressed_voltage"] = mean_voltages[idx]
        KEYS[idx]["nominal_unpressed_voltage_stddev"] = stddev_voltages[idx]

    print("Measuring key voltages when pressed...", file=sys.stderr)
    for idx in KEYS:
        print(f"Measuring {KEYS[idx]['name']} in 3s...")
        time.sleep(3.0)
        print("Measuring now...")
        mean_voltages, stddev_voltages = measure_voltages()
        KEYS[idx]["nominal_pressed_voltage"] = mean_voltages[idx]
        KEYS[idx]["nominal_pressed_voltage_stddev"] = stddev_voltages[idx]
        print(f"Finished measuring {KEYS[idx]['name']} now...")

    print(f"Calibration complete! Writing to file: {calibration_file}", file=sys.stderr)
    with open(calibration_file, "w") as cal_file:
        json.dump(KEYS, cal_file)


def key_pressed(voltage: int, idx: int) -> bool:
    """
    Return True if key is pressed, False otherwise
    """
    if "voltage_threshold" in KEYS[idx]:
        return voltage > KEYS[idx]["voltage_threshold"]
    return abs(voltage - KEYS[idx]["nominal_unpressed_voltage"]) > abs(voltage - KEYS[idx]["nominal_pressed_voltage"])
        

def press_keys(keyscan: KeyScan, pressed_keys: set, dry_run: bool = False) -> None:
    """
    Press/release keys as appropriate.
    """
    for idx, voltage in enumerate(keyscan):
        if idx in KEYS:
            if idx not in pressed_keys and key_pressed(voltage, idx):
                if dry_run:
                    print(f"Pressing: {KEYS[idx]} (measured voltage: {voltage})")
                else:
                    if "press_and_release" in KEYS[idx] and KEYS[idx]["press_and_release"]:
                        keyboard.press_and_release(KEYS[idx]["name"])
                    keyboard.press(KEYS[idx]["name"])
                pressed_keys.add(idx)
            elif idx in pressed_keys and not key_pressed(voltage, idx):
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
    if "--raw" in sys.argv:
        print(measure_voltages())
        return 0
    if "--detect" in sys.argv:
        print(detect_likely_keys())
        return 0
    if "--calibrate" in sys.argv:
        calibrate_keyboard()
    else:
        with open("calibration.json", "r") as cal_file:
            for idx, cfg in json.load(cal_file).items():
                KEYS[int(idx)].update(cfg)
    for keyscan in read_keyscans():
        press_keys(keyscan, pressed_keys, check_dry_run())
    return 0


if __name__ == "__main__":
    sys.exit(main())
