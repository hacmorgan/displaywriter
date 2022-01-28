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
? Checksum for messages
? Make a feedforward network to watch voltages after initial press to avoid multiple presses
"""


import json
import sys
import time

from typing import Iterator, Optional

import keyboard
import numpy as np
import serial


"""
Position indices of each key's character in the string received from the arduino.
"""
GLOBAL_CONFIG = {}
KEYS = {}  # filled in from calibration file
NUM_KEYS = 96;  # number of values sent by arduino


KeyScan = str


def read_keyscans(
    device: str = "/dev/ttyACM0",
    baudrate: int = 115200,
) -> Iterator[KeyScan]:
    """
    Read keyscans from arduino over serial.
    """
    ewme_scan = np.zeros(NUM_KEYS, dtype=float)
    ewme_ratios = np.zeros(NUM_KEYS, dtype=float)
    for idx in KEYS:
        if "ewme_ratio" in KEYS[idx]:
            ewme_ratios[idx] = KEYS[idx]["ewme_ratio"]
        else:
            ewme_ratios[idx] = GLOBAL_CONFIG["ewme_ratio"]
    with serial.Serial(port=device, baudrate=baudrate, timeout=1.0) as ser:
        while True:
            voltage_bytestrings = ser.readline().strip().split(b",")[:-1]
            if len(voltage_bytestrings) != NUM_KEYS:
                continue
            try:
                scan = np.array([float(voltage) for voltage in voltage_bytestrings])
                ewme_scan = (1 - ewme_ratios) * ewme_scan + ewme_ratios * scan
                yield ewme_scan
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
    print("Measuring baseline voltages...")
    mean_voltages, stddev_voltages = next(measure_voltages())
    print("Done!")
    for new_mean_voltages, new_stddev_voltages in measure_voltages():
        mean_voltage_diffs = new_mean_voltages - mean_voltages
        mean_voltage_diffs_percent = (new_mean_voltages - mean_voltages) / (mean_voltages + 0.1) * 100
        for metric, symbol in ((mean_voltage_diffs, "/1023*5V"), (mean_voltage_diffs_percent, "%")):
            for order, idx in zip(range(10), reversed(np.argsort(metric))):
                print(f"{order}th biggest vdiff ({symbol}): {metric[idx]:.2f}({symbol}) (key index: {idx}, mean voltage: {new_mean_voltages[idx]})")
            print()
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
    voltage_reader = measure_voltages()
    for idx in KEYS:
        print(f"Measuring {KEYS[idx]['name']} in 4s...")
        time.sleep(4.0)
        print("Measuring now...")
        mean_voltages, stddev_voltages = next(voltage_reader)
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


def increment_confidence(idx: int) -> None:
    """
    """
    if "confidence" not in KEYS[idx]:
        KEYS[idx]["confidence"] = 0
    KEYS[idx]["confidence"] += 1


def decrement_confidence(idx: int) -> None:
    """
    """
    KEYS[idx]["confidence"] -= 1
    

def press_key(idx: int, voltage: int, dry_run: bool) -> None:
    """
    """
    if dry_run:
        print(f"Pressing: {KEYS[idx]} (measured voltage: {voltage})")
    else:
        key = KEYS[idx]["scancode"] if "scancode" in KEYS[idx] else KEYS[idx]["name"]
        if "press_and_release" in KEYS[idx] and KEYS[idx]["press_and_release"]:
            keyboard.press_and_release(key)                    
        keyboard.press(key)
    

def release_key(idx: int, dry_run: bool) -> None:
    """
    """
    if dry_run:
        print(f"Releasing: {KEYS[idx]}")
    else:
        key = KEYS[idx]["scancode"] if "scancode" in KEYS[idx] else KEYS[idx]["name"]
        keyboard.release(key)


def press_keys(keyscan: KeyScan, pressed_keys: set, dry_run: bool = False, confidence: int = 1) -> None:
    """
    Press/release keys as appropriate.
    """
    for idx, voltage in enumerate(keyscan):
        if idx in KEYS:
            if idx not in pressed_keys and key_pressed(voltage, idx):
                increment_confidence(idx)
                if KEYS[idx]["confidence"] >= confidence:
                    press_key(idx, voltage, dry_run)
                    pressed_keys.add(idx)
            elif idx in pressed_keys and not key_pressed(voltage, idx):
                decrement_confidence(idx)
                if KEYS[idx]["confidence"] == 0:
                    release_key(idx, dry_run)
                    pressed_keys.remove(idx)


def check_dry_run() -> bool:
    """
    Check if --dry-run given as arg
    """
    return any(dryrun in sys.argv for dryrun in ("--dry-run", "-d"))
                

def main() -> int:
    
    pressed_keys = set()
    
    with open("/home/hamish/src/displaywriter/calibration.json", "r") as cal_file:
        for field, cfg in json.load(cal_file).items():
            if field == "global":
                GLOBAL_CONFIG.update(cfg)
            else:
                KEYS[int(field)] = cfg

    if "--raw" in sys.argv:
        for scan in read_keyscans():
            # print(",".join(f"{val:.1f}" for val in scan))
            print(scan.reshape(8, 12).astype(int))
        return 0
    
    if "--detect" in sys.argv:
        print(detect_likely_keys())
        return 0
    
    if "--calibrate" in sys.argv:
        calibrate_keyboard()
        with open("/home/hamish/src/displaywriter/calibration.json", "w") as cal_file:
            json.dump(KEYS, cal_file)

    for keyscan in read_keyscans():
        press_keys(keyscan, pressed_keys, check_dry_run())

    return 0


if __name__ == "__main__":
    sys.exit(main())
