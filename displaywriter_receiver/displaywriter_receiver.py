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
? Checksum for messages
? Make a feedforward network to watch voltages after initial press to avoid multiple presses
"""


import argparse
import json
import sys
import time

from typing import Iterator, Optional, TextIO

import keyboard
import numpy as np
import serial


GLOBAL_CONFIG = {}
KEYS = {}  # filled in from calibration file
NUM_KEYS = 96  # number of values sent by arduino


"""
Type Aliases
"""
KeyScan = str


def read_keyscans(
    device: str = "/dev/ttyACM0",
    baudrate: int = 115200,
) -> Iterator[KeyScan]:
    """
    Read keyscans from arduino over serial.
    """
    ewme_scan = np.zeros(NUM_KEYS, dtype=float)
    ewme_ratios = np.ones(NUM_KEYS, dtype=float) * GLOBAL_CONFIG["ewme_ratio"]
    for idx in KEYS:
        if "ewme_ratio" in KEYS[idx]:
            ewme_ratios[idx] = KEYS[idx]["ewme_ratio"]
    with serial.Serial(port=device, baudrate=baudrate, timeout=1.0) as ser:
        while True:
            voltage_bytestrings = ser.readline().strip().split(b",")[:-1]
            if len(voltage_bytestrings) != NUM_KEYS:
                continue
            try:
                scan = np.array([int(voltage) for voltage in voltage_bytestrings])
                # ewme_scan = (1 - ewme_ratios) * ewme_scan + ewme_ratios * scan
                yield scan
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
    """ """
    print("Measuring baseline voltages...")
    mean_voltages, stddev_voltages = next(measure_voltages())
    print("Done!")
    for new_mean_voltages, new_stddev_voltages in measure_voltages():
        mean_voltage_diffs = new_mean_voltages - mean_voltages
        mean_voltage_diffs_percent = (
            (new_mean_voltages - mean_voltages) / (mean_voltages + 0.1) * 100
        )
        for metric, symbol in (
            (mean_voltage_diffs, "/1023*5V"),
            (mean_voltage_diffs_percent, "%"),
        ):
            for order, idx in zip(range(10), reversed(np.argsort(metric))):
                print(
                    f"{order}th biggest vdiff ({symbol}): {metric[idx]:.2f}({symbol}) (key index: {idx}, mean voltage: {new_mean_voltages[idx]})"
                )
            print()
        print("\n")


def calibrate_keyboard(calibration_file="calibration.json", samples: int = 50):
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
    return abs(voltage - KEYS[idx]["nominal_unpressed_voltage"]) > abs(
        voltage - KEYS[idx]["nominal_pressed_voltage"]
    )


def increment_confidence(idx: int, max_confidence: int) -> None:
    """ """
    if "confidence" not in KEYS[idx]:
        KEYS[idx]["confidence"] = 0
    KEYS[idx]["confidence"] = min(max_confidence, KEYS[idx]["confidence"] + 1)


def decrement_confidence(idx: int) -> None:
    """ """
    KEYS[idx]["confidence"] = max(KEYS[idx]["confidence"] - 1, 0)


def press_key(idx: int, voltage: int, dry_run: bool) -> None:
    """ """
    if dry_run:
        print(f"Pressing: {KEYS[idx]} (measured voltage: {voltage})")
    else:
        key = KEYS[idx]["scancode"] if "scancode" in KEYS[idx] else KEYS[idx]["name"]
        if "press_and_release" in KEYS[idx] and KEYS[idx]["press_and_release"]:
            keyboard.press_and_release(key)
        keyboard.press(key)


def release_key(idx: int, dry_run: bool) -> None:
    """ """
    if dry_run:
        print(f"Releasing: {KEYS[idx]}")
    else:
        key = KEYS[idx]["scancode"] if "scancode" in KEYS[idx] else KEYS[idx]["name"]
        keyboard.release(key)


def press_keys(
    keyscan: KeyScan, pressed_keys: set, dry_run: bool = False, max_confidence: int = 2
) -> None:
    """
    Press/release keys as appropriate.
    """
    for idx, voltage in enumerate(keyscan):
        if idx in KEYS:
            if idx in pressed_keys:
                if key_pressed(voltage, idx):
                    increment_confidence(idx, max_confidence)
                else:
                    decrement_confidence(idx)
                    if KEYS[idx]["confidence"] == 0:
                        release_key(idx, dry_run)
                        pressed_keys.remove(idx)
            else:
                if key_pressed(voltage, idx):
                    press_key(idx, voltage, dry_run)
                    pressed_keys.add(idx)
                    KEYS[idx]["confidence"] = (
                        KEYS[idx]["max_confidence"]
                        if "max_confidence" in KEYS[idx]
                        else max_confidence
                    )


def print_raw_scan(scan: KeyScan) -> None:
    """
    Print raw voltages of scan.

    Values are printed with 4 digits to ensure consisent width.

    @param[in] scan Keyboard scan.
    """
    for row in scan.reshape(8, 12).astype(int):
        print(",".join(f"{num:4d}" for num in row))
    print()


def plot_key_voltages(keys: list[str], measurement_period: float = 3.0) -> None:
    """
    Plot voltages on specified keys over a given period of time.

    @param[in] keys List of keys to plot
    @param[in] measurement_period How long to collect measurements for before plotting (seconds).
    """


def load_key_calibration(cal_fd: TextIO) -> None:
    """
    Load key calibration from file.

    @param[in] cal_fd File descriptor of open calibration file.
    """
    for field, cfg in json.load(cal_fd).items():
        if field == "global":
            GLOBAL_CONFIG.update(cfg)
        else:
            KEYS[int(field)] = cfg


def get_args() -> argparse.Namespace:
    """
    Define and parse args
    """
    parser = argparse.ArgumentParser(prog="DisplayWriter Receiver")
    parser.add_argument(
        "--calibrate",
        action="store_true",
        help="Auto-calibrate the keyboard (TODO)",
    )
    parser.add_argument(
        "--calibration",
        "-c",
        type=str,
        help="Keyboard calibration file.",
        default="/home/hamish/src/displaywriter/calibration.json",
    )
    parser.add_argument(
        "--detect",
        "-e",
        action="store_true",
        help="Measure baseline voltages (with keys unpressed). Then report 10 keys with "
        "highest voltage diff relative to baselines.",
    )
    parser.add_argument(
        "--device",
        "-v",
        type=str,
        default="/dev/ttyACM0",
        help="Serial device of arduino.",
    )
    parser.add_argument(
        "--dry-run",
        "-d",
        action="store_true",
        help="Print registered keypresses rather than sending them to the OS.",
    )
    parser.add_argument(
        "--raw",
        "-r",
        action="store_true",
        help="Print raw key voltages from arduino. Exponential weighted moving average "
        "is applied before printing.",
    )
    return parser.parse_args()


def main(args: argparse.Namespace) -> int:

    with open(args.calibration, "r") as cal_fd:
        load_key_calibration(cal_fd)

    if args.raw:
        for scan in read_keyscans(device=args.device):
            print_raw_scan(scan)
        return 0

    if args.detect:
        print(detect_likely_keys())
        return 0

    if args.calibrate:
        calibrate_keyboard()
        with open(args.calibration, "w") as cal_file:
            json.dump(KEYS, cal_file)

    pressed_keys = set()
    for keyscan in read_keyscans(device=args.device):
        press_keys(keyscan, pressed_keys, args.dry_run)

    return 0


if __name__ == "__main__":
    sys.exit(main(get_args()))
