#!/usr/bin/env python3
from setuptools import setup

setup(
    name="displaywriter_receiver",
    version="1.0",
    description="Convert raw signal from arduino into keystrokes",
    author="Hamish Morgan",
    author_email="ham430@gmail.com",
    url="http://github.com/hacmorgan/displaywriter",
    packages=[
        "displaywriter_receiver",
    ],
    install_requires=[
        "keyboard",
        "matplotlib",
        "numpy",
        "pyserial",
    ],
    scripts=[
        "displaywriter_receiver/displaywriter_receiver.py",
    ],
)
