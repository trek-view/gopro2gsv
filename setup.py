#!/usr/bin/env python

import os, sys
import platform
import shutil
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py

# BIN_DEST = Path(os.path.abspath("build/bin"))
BIN_DEST = Path(os.path.abspath("src/bin"))

class BuildCommand(build_py):
    def run(self):
        binary_files: list[Path] = [Path("third-party/max2sphere/max2sphere"), Path("third-party/fusion2sphere/fusion2sphere")]
        if platform.system() == "Windows":
            binary_files.clear()
            os.system("cd .\\third-party\\fusion2sphere && make clean && make")
            os.system("cd .\\third-party\\max2sphere && make clean && make")
            binary_files.append(Path("third-party/max2sphere/max2sphere.exe"))
            binary_files.append(Path("third-party/fusion2sphere/fusion2sphere.exe"))
        elif sys.platform.lower() == "darwin":
            if platform.processor() == "arm": 
                #it's Apple Silicon Mac (M1,, M2, ...)
                os.system("cd ./third-party/fusion2sphere && make clean && make -f Makefile-MacM1")
                os.system("cd ./third-party/max2sphere && make clean && make -f Makefile-MacM1")
            else:
                # regular intel mac 
                os.system("cd ./third-party/fusion2sphere && make clean && make")
                os.system("cd ./third-party/max2sphere && make clean && make")
        else:
            # linux
            os.system("cd ./third-party/fusion2sphere && make clean && make")
            os.system("cd ./third-party/max2sphere && make clean && make -f Makefile-Linux")
        BIN_DEST.mkdir(exist_ok=True)
        for bin in binary_files:
            shutil.move(bin, BIN_DEST/bin.name)
        build_py.run(self)

setup(
    name='gopro2gsv',
    version='0.0.1-1',
    description='Does stuff with gopro files',
    cmdclass={
        'build_py': BuildCommand,
    },
    package_data=dict(mybin=[str(BIN_DEST)]),
    include_package_data=True
)
