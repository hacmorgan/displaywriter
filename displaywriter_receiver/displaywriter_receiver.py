#!/usr/bin/env python3


"""
@file

Read messages from Arduino and generate keypresses or debug information.

The Arduino can either send full analog scans of the keyboard (when it is in debug mode),
or just which key has been pressed or released (when it is in normal mode).

Some debugging operations (e.g. --raw, --detect) require the Arduino to be in debug mode,
but normal operation expects it to be in normal mode. This is set in the Arudino code, so
it needs to be reprogrammed before any debugging operations (and vice-versa).

Originally the arduino only operated in debug mode, so this program would detect which
key is pressed by analysing the analog scans of the keyboard, but that requires constant
serial communincation with the Arduino, which requires about 5% of one CPU's time at all
times for smooth operation.

@author  Hamish Morgan
@date    20/01/2021
@license BSD
"""


import argparse
import json
import os
import sys
import time

from typing import Iterator, Optional, TextIO

import keyboard
import matplotlib.pyplot as plt
import numpy as np
import serial


KEYS = {}  # filled in from calibration file
FUNCTION_MODIFIER_KEYS = {}  # copied from KEYS
NUM_KEYS = 96  # number of values sent by arduino

# Aliases for decoding messages from Arduino
KEY_PRESSED_STATE = 1
KEY_RELEASED_STATE = 0


"""
Type Aliases
"""
KeyScan = np.ndarray
PlotData = list[float]


def is_function_key_modifier(idx) -> bool:
    """
    Check whether a key is the function key modifier.
    """
    return "type" in KEYS[idx] and KEYS[idx]["type"] == "function_key_modifier"


def load_key_calibration(cal_fd: TextIO) -> None:
    """
    Load key calibration from file.

    @param[in] cal_fd File descriptor of open calibration file.
    """
    for field, cfg in json.load(cal_fd).items():
        idx = int(field)
        KEYS[idx] = cfg
        if is_function_key_modifier(idx):
            FUNCTION_MODIFIER_KEYS[idx] = cfg
            FUNCTION_MODIFIER_KEYS[idx]["pressed"] = False


def set_niceness(niceness: int = -10) -> bool:
    """
    Try to set the niceness of the receiver lower.

    We want to increase the priority of the receiever for the OS, to maximise
    responsiveness when the PC is under load.

    This will only work on *nix, and requires the receiver to be run by root to allow
    the niceness to be reduced (priority increased).

    @param[in] niceness New niceness value (should be -ve for higher priority)
    @return True if niceness set successfully, False otherwise.
    """
    if os.name == "posix":
        try:
            os.nice(niceness)
            return True
        except OSError:
            pass
    return False


def read_keyscans(
    device: str,
    baudrate: int,
) -> Iterator[KeyScan]:
    """
    Read keyscans (voltage of each key) from arduino over serial.

    The Arduino must be in debug mode.

    @param[in] device Serial device of Arduino (e.g. /dev/ttyACM0 - Linux, COM3 - windows)
    @param[in] baudrate Baudrate for serial communication
    @return Generator of keyscans.
    """
    with serial.Serial(port=device, baudrate=baudrate, timeout=1.0) as ser:
        while True:
            voltage_bytestrings = ser.readline().strip().split(b",")[:-1]
            if len(voltage_bytestrings) != NUM_KEYS:
                continue
            try:
                scan = np.array([int(voltage) for voltage in voltage_bytestrings])
                yield scan
            except ValueError:
                continue


def print_raw_scan(scan: KeyScan) -> None:
    """
    Print raw voltages of scan.

    Values are printed with 4 digits to ensure consisent width.

    @param[in] scan Keyboard scan.
    """
    for row in scan.reshape(8, 12).astype(int):
        print(",".join(f"{num:4d}" for num in row))
    print()


def measure_voltages(
    device: str, baudrate: int, samples: int = 25
) -> Iterator[tuple[np.ndarray, np.ndarray]]:
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
    for keyscan in read_keyscans(device=device, baudrate=baudrate):
        voltages[idx, :] = keyscan
        idx += 1
        if idx == samples:
            yield np.mean(voltages, axis=0), np.std(voltages, axis=0)
            idx = 0


def detect_likely_keys(device: str, baudrate: int) -> None:
    """
    Detect keys that might be pressed.

    This is achieved by measuring baseline (unpressed) key voltages, then using those
    expected values to find keys with the biggest deviation from their expected voltage.

    Requires Arduino to be in debug mode.
    """
    print("Measuring baseline voltages...")
    mean_voltages, stddev_voltages = next(measure_voltages(device, baudrate))
    print("Done!")
    for new_mean_voltages, new_stddev_voltages in measure_voltages(device, baudrate):
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


def key_idx_from_name(key_name: str) -> int:
    """
    Find key index of key with given name
    """
    for idx in KEYS:
        if KEYS[idx]["name"] == key_name:
            return idx
    raise KeyError(f"{key_name} key not found")


def timestamp_generator(end_time: float) -> Iterator[float]:
    """
    Infinitely generate timestamps (handy for zipping)
    """
    while timestamp := time.time() < end_time:
        yield timestamp


def pyplot_args(timestamps: PlotData, voltages: dict[int, PlotData]) -> list[PlotData]:
    """
    Return a flattened list of [timestamps, key_a, timestamps, key_b, ...] for unpacking
    as arguments to plt.plot()
    """
    args = []
    for key in voltages:
        args.append(timestamps)
        args.append(voltages[key])
    return args


def plot_key_voltages(
    keys: list[str], device: str, baudrate: int, measurement_period: float = 3.0
) -> None:
    """
    Plot voltages on specified keys over a given period of time.

    @param[in] keys List of keys to plot
    @param[in] measurement_period How long to collect measurements for before plotting
               (seconds).
    """
    keys = [key_idx_from_name(key_name) for key_name in keys]
    timestamps = []
    voltages = {key: [] for key in keys}
    for scan, timestamp in zip(
        read_keyscans(device=device, baudrate=baudrate),
        timestamp_generator(end_time=time.time() + measurement_period),
    ):
        timestamps.append(timestamp)
        for key in keys:
            voltages[key].append(scan[key])
    plt.plot(*pyplot_args(timestamps, voltages))
    plt.show()


def shadows_function_key(idx: int) -> bool:
    """
    Check whether a key shadows a function key (e.g. 2 -> F2)
    """
    return "shadow_function_key" in KEYS[idx]


def should_use_function_key(idx: int) -> bool:
    """
    Check whether key should be treated as a function key
    """
    return shadows_function_key(idx) and any(
        FUNCTION_MODIFIER_KEYS[idx]["pressed"] for idx in FUNCTION_MODIFIER_KEYS
    )


def get_key(idx: int) -> str:
    """
    Get scancode or name of key from its index.

    If key shadows a function key and function modifier key is down, return function key.
    """
    if should_use_function_key(idx):
        return KEYS[idx]["shadow_function_key"]
    if "scancode" in KEYS[idx]:
        return KEYS[idx]["scancode"]
    return KEYS[idx]["name"]


def should_press_and_release(idx: int) -> bool:
    """
    Check whether a key should be pressed and released instead of just pressed.
    """
    return "press_and_release" in KEYS[idx] and KEYS[idx]["press_and_release"]


def press_key(idx: int, dry_run: bool) -> None:
    """
    Press key with given index, or just pretend to.

    @param[in] idx Index of key.
    @param[in] dry_run Print a message to stdout instead of actually pressing key if True
    """
    if idx not in KEYS:
        return

    if dry_run:
        print(f"Pressing: {KEYS[idx]}")
        return

    if is_function_key_modifier(idx):
        FUNCTION_MODIFIER_KEYS[idx]["pressed"] = True
        return

    key = get_key(idx)

    if should_press_and_release(idx):
        keyboard.press_and_release(key)
        return

    keyboard.press(key)


def release_key(idx: int, dry_run: bool) -> None:
    """
    Release key with given index, or just pretend to.

    @param[in] idx Index of key.
    @param[in] dry_run Print a message to stdout instead of actually pressing key if True
    """
    if idx not in KEYS:
        return

    if dry_run:
        print(f"Releasing: {KEYS[idx]}")
        return

    if is_function_key_modifier(idx):
        FUNCTION_MODIFIER_KEYS[idx]["pressed"] = False
        return

    key = get_key(idx)

    if should_press_and_release(idx):
        keyboard.press_and_release(key)
        return

    keyboard.release(key)


def read_messages(
    device: str,
    baudrate: int,
    dry_run: bool,
) -> Iterator[KeyScan]:
    """
    Read key state messages from Arduino.

    The Arduino must NOT be in debug mode.

    @param[in] device Serial device of Arduino (e.g. /dev/ttyACM0 - *nix, COM3 - windows)
    @param[in] baudrate Baudrate for serial communication
    @return Generator of keyscans.
    """
    with serial.Serial(port=device, baudrate=baudrate, timeout=1.0) as ser:
        while True:
            try:
                key, pressed = map(int, ser.readline().strip().split(b","))
                if pressed:
                    press_key(key, dry_run)
                else:
                    release_key(key, dry_run)
            except ValueError:
                continue


def get_args() -> argparse.Namespace:
    """
    Define and parse args
    """
    parser = argparse.ArgumentParser(prog="DisplayWriter Receiver")
    parser.add_argument(
        "--baudrate",
        "--baud",
        "-b",
        type=int,
        default=115200,
        help="Baudrate for serial communication with Arduino",
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
        "--niceness",
        "-n",
        type=int,
        default=-10,
        help="Receiver niceness (priority for OS). Only works on *nix",
    )
    parser.add_argument(
        "--plot-keys",
        "-p",
        type=str,
        help="Plot voltages over 3 seconds for each key (as comma-separated string)",
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

    set_niceness(niceness=args.niceness)

    if args.raw:
        for scan in read_keyscans(device=args.device, baudrate=args.baudrate):
            print_raw_scan(scan)

    elif args.detect:
        print(detect_likely_keys(device=args.device, baudrate=args.baudrate))

    elif args.plot_keys is not None:
        while True:
            plot_key_voltages(
                keys=args.plot_keys.strip().split(","),
                device=args.device,
                baudrate=args.baudrate,
            )

    else:
        read_messages(device=args.device, baudrate=args.baudrate, dry_run=args.dry_run)

    return 0


if __name__ == "__main__":
    sys.exit(main(get_args()))
