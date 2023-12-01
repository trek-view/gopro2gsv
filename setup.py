#!/usr/bin/env python

import os
import platform
import shutil
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py

# BIN_DEST = Path(os.path.abspath("build/bin"))
BIN_DEST = Path(os.path.abspath("src/bin"))

class BuildCommand(build_py):
    def run(self):
        binary_files: list[Path] = []
        if platform.system() == "Windows":
            os.system("cd .\\third-party\\fusion2sphere && make")
            os.system("cd .\\third-party\\max2sphere && make")
            binary_files.append(Path("third-party/max2sphere/max2sphere.exe"))
            binary_files.append(Path("third-party/fusion2sphere/fusion2sphere.exe"))
        else:
            os.system("cd ./third-party/fusion2sphere && make clean && make")
            os.system("cd ./third-party/max2sphere && make clean && make")
            binary_files.append(Path("third-party/max2sphere/max2sphere"))
            binary_files.append(Path("third-party/fusion2sphere/fusion2sphere"))
        BIN_DEST.mkdir(exist_ok=True)
        for bin in binary_files:
            shutil.move(bin, BIN_DEST/bin.name)
        build_py.run(self)

setup(
    name='gopro2gsv',
    version='0.0.1',
    description='Does stuff with gopro files',
    cmdclass={
        'build_py': BuildCommand,
    },
    package_data=dict(mybin=[str(BIN_DEST)]),
    include_package_data=True
)
