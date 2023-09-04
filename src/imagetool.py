import pathlib, shutil
from pathlib import Path
import re

from .shell_helper import test_image, InvalidImageException
from datetime import datetime, timedelta
from dateutil.parser import parse as parse_date
from math import ceil
from collections import UserDict

from logging import getLogger
logger = getLogger("gopro2gsv.image_tool")

MAX_RE = re.compile(r"(\w{4}).*.jpg")
FUSION_RE = re.compile(r"multishot_(\d{4})_.*.jpg")

CAMERAS_RE = {
    "fusion": re.compile(r"(\w{4}).*.jpg"),
    "max": re.compile(r"multishot_(\d{4})_.*.jpg"),
}


class metadata_dict(UserDict):
    def __getitem__(self, key) -> str:
        value = super().__getitem__(key)
        if isinstance(value, list):
            return value[0]
        return value
    
    def list(self, key):
        return super().__getitem__(key)

def get_camera_attr_from_name(name) -> tuple[str, str]:
    for camera, re_exp in CAMERAS_RE.items():
        match = re_exp.match(name)
        if match:
            return camera, match.group(1)
    raise InvalidImageException(f"UnsupportedCamera: unidentified filename pattern: `{name}`")

def parse_date_and_width_from_exif(exif_data: dict[str, str]) -> tuple[int, datetime]:
    raw__date = f'{exif_data["GPS:GPSDateStamp"].replace(":", "-")} {exif_data["GPS:GPSTimeStamp"]}'
    raw_width = int(exif_data["File:ImageWidth"])
    return raw_width, parse_date(raw__date)

def get_files_from_dir(input_dir: Path) -> tuple[list[dict], list[dict]]:
    files: list[pathlib.Path] = tuple(input_dir.iterdir())
    global_camera: bool = None
    global_prefix: str = None
    global_width: str = None
    prev_date: datetime = None

    invalid_files = []
    valid_images = []

    for f in files:
        metadata = metadata_dict()
        try:
            name = f.name.lower()
            if name.startswith("."):
                continue
            if f.is_dir():
                raise InvalidImageException(f"unidentiified file: `{f.name}` file is a directory")
            if not name.endswith(".jpg"):
                raise InvalidImageException(f"unidentiified file: `{f.name}` is not an image file")

            camera, prefix = get_camera_attr_from_name(name)
            if global_camera == None: # first image
                global_camera, global_prefix = camera, prefix

            if camera != global_camera or prefix != global_prefix:
                raise InvalidImageException(f"filename `{f.name}` does not match pattern")

            metadata = metadata_dict(test_image(str(f)))
            width, date = parse_date_and_width_from_exif(metadata)

            if not global_width: # first iteration
                global_width = width
            if width != global_width:
                raise InvalidImageException(f"Image width does not match for {name}: {width} != {global_width}")

            metadata["date"] = date
            valid_images.append(metadata)
        except InvalidImageException as e:
            metadata["error"] = str(e)
            invalid_files.append(metadata)
            logger.warn(e)

        # set path for file
        metadata["path"] = f 
        

    valid_images.sort(key=lambda v: (v["date"], v["path"]))

    prev_date = valid_images[0]["date"]
    workdir = input_dir/"processed"
    workdir.mkdir(exist_ok=True) # don't throw if folder already exist
    for i, image in enumerate(valid_images):
        date = image["date"]
        path: pathlib.Path = image["path"]
        name = path.name
        if (delta := date - prev_date) > timedelta(seconds=60):
            valid_images.pop(i)
            logger.warn(f"More than 60 seconds between two succeeding frames: [{name}|{delta.seconds} seconds]... removed")
        prev_date = date
    return valid_images, invalid_files

def write_images_to_dir(images: list[dict], dir: Path, images_per_video=300):
    dir.mkdir(exist_ok=True)
    for i, image in enumerate(images):
        path: Path = image['path']
        newpath = dir/f"{i:05d}.jpg"
        shutil.copyfile(path, newpath)
        image["newpath"] = newpath
    return
