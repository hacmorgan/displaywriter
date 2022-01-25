#!/usr/bin/env python3


"""
@file

Convert raw signal from arduino into keystrokes.

@author  Hamish Morgan
@date    20/01/2021
@license BSD
"""


"""
TODO
- Use argparse
- Make --raw stay in the loop (rather than creating a new serial connection every time)
- Make 
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
KEYS = {}  # filled in from calibration file
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


def measure_voltages(samples: int = 25) -> Iterator[tuple[np.ndarray, np.ndarray]]:
    """
    Measure the voltages of each key over a period of time.

    Yields continuously (returns a generator) to avoid breaking the serial connection
    when continuous measurements are required.

    @param[in] samples How many times to sample the keyboard
    @retval Mean voltage for each key
    @retval Stddev voltage for each key
    """
    voltages = np.zeros((samples, NUM_KEYS), dtype=int)
    idx = 0
    for keyscan in read_keyscans():
        voltages[idx, :] = keyscan
        idx += 1
        if idx == samples:
            yield np.mean(voltages, axis=0), np.std(voltages, axis=0)
            idx = 0


def detect_likely_keys() -> None:
    """
    
    """
    print("Measuring baseline voltages in 3s... don't press any keys!")
    time.sleep(3)
    print("Measuring baseline voltages...")
    mean_voltages, stddev_voltages = next(measure_voltages())
    print("Done!")
    for new_mean_voltages, new_stddev_voltages in measure_voltages():
        mean_voltage_diffs = new_mean_voltages - mean_voltages
        for order, idx in zip(range(10), reversed(np.argsort(mean_voltage_diffs))):
            print(f"{order}th biggest vdiff: {mean_voltage_diffs[idx]:.2f} (key index: {idx}, mean voltage: {new_mean_voltages[idx]})")
        print("\n")
    

            
def calibrate_keyboard(calibration_file = "calibration.json", samples: int = 50):
    """
    Read the keyboard for a while to determine expected voltages on each key.
    """
    print("Calibrating keyboard...", file=sys.stderr)

    print("Measuring key voltages unpressed...", file=sys.stderr)
    mean_voltages, stddev_voltages = next(measure_voltages())
    for idx in KEYS:
        KEYS[idx]["nominal_unpressed_voltage"] = mean_voltages[idx]
        KEYS[idx]["nominal_unpressed_voltage_stddev"] = stddev_voltages[idx]

    print("Measuring key voltages when pressed...", file=sys.stderr)
    for idx, (mean_voltages, stddev_voltages) in zip(KEYS, measure_voltages()):
        print(f"Measuring {KEYS[idx]['name']} in 3s...")
        time.sleep(3.0)
        print("Measuring now...")
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
                    key = KEYS[idx]["scancode"] if "scancode" in KEYS[idx] else KEYS[idx]["name"]
                    if "press_and_release" in KEYS[idx] and KEYS[idx]["press_and_release"]:
                        keyboard.press_and_release(key)                    
                    keyboard.press(key)
                pressed_keys.add(idx)
            elif idx in pressed_keys and not key_pressed(voltage, idx):
                if dry_run:
                    print(f"Releasing: {KEYS[idx]}")
                else:
                    key = KEYS[idx]["scancode"] if "scancode" in KEYS[idx] else KEYS[idx]["name"]
                    keyboard.release(key)
                pressed_keys.remove(idx);


def check_dry_run() -> bool:
    """
    Check if --dry-run given as arg
    """
    return any(dryrun in sys.argv for dryrun in ("--dry-run", "-d"))
                

def main() -> int:
    
    pressed_keys = set()
    
    if "--raw" in sys.argv:
        for voltage in measure_voltages(samples=1):
            print(voltage)
        return 0
    
    if "--detect" in sys.argv:
        print(detect_likely_keys())
        return 0
    
    with open("/home/hamish/src/displaywriter/calibration.json", "r") as cal_file:
        for str_idx, cfg in json.load(cal_file).items():
            KEYS[int(str_idx)] = cfg

    if "--calibrate" in sys.argv:
        calibrate_keyboard()
        with open("/home/hamish/src/displaywriter/calibration.json", "w") as cal_file:
            json.dump(KEYS, cal_file)

    for keyscan in read_keyscans():
        press_keys(keyscan, pressed_keys, check_dry_run())

    return 0


if __name__ == "__main__":
    sys.exit(main())
