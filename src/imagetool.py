import os
import pathlib, shutil
from pathlib import Path
import re

from .utils import calculateVelocities

from .shell_helper import copy_metadata_from_file, create_video_from_images, delete_files, generate_gpx_from_images, make_video_gsv_compatible, set_date_metadata, test_image, InvalidImageException, get_exif_details_for_dir
from .errors import FatalException, GSVException
from datetime import datetime, timedelta
from dateutil.parser import parse as parse_date
from math import ceil
from .utils import metadata_dict
from .constants import *

from logging import getLogger
logger = getLogger("gopro2gsv.image_tool")

MAX_RE = re.compile(r"(\w{4}).*.jpg")
FUSION_RE = re.compile(r"multishot_(\d{4})_.*.jpg")



CAMERAS_RE = {
    "fusion": re.compile(r"(\w{4}).*.jpg"),
    "max": re.compile(r"multishot_(\d{4})_.*.jpg"),
}



def get_camera_attr_from_name(name) -> tuple[str, str]:
    for camera, re_exp in CAMERAS_RE.items():
        match = re_exp.match(name)
        if match:
            return camera, match.group(1)
    raise InvalidImageException(f"UnsupportedCamera: unidentified filename pattern: `{name}`")

def parse_date_and_width_from_exif(exif_data: dict[str, str]) -> tuple[int, datetime]:
    raw__date = f'{exif_data["GPS:GPSDateStamp"].replace(":", "-")} {exif_data["GPS:GPSTimeStamp"]}'
    raw_width = int(exif_data["File:ImageWidth"])
    raw_height = int(exif_data["File:ImageHeight"])
    exif_data["height"] = raw_height
    exif_data["width"] = raw_width
    return raw_width, parse_date(raw__date)

def get_files_from_dir(input_dir: Path) -> tuple[list[dict], list[dict]]:
    global_camera: bool = None
    global_prefix: str = None
    global_width: str = None
    prev_date: datetime = None

    invalid_files = []
    valid_images = []

    for f, metadata in get_exif_details_for_dir(input_dir).items():
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
            test_image(metadata)
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

    return valid_images, invalid_files

def fix_outlier(valid_images, max_acceptable_velocity):
    prev_date = valid_images and valid_images[0]["date"]
    prev_image = valid_images and valid_images[0]
    for i, image in enumerate(valid_images):
        error = None
        date = image["date"]
        path: pathlib.Path = image["path"]
        name = path.name
        time_diff = date - prev_date
        start_loc = prev_image["GPS:GPSLatitude"], prev_image["GPS:GPSLongitude"], prev_image["GPS:GPSAltitude"]
        end_loc   = image["GPS:GPSLatitude"], image["GPS:GPSLongitude"], image["GPS:GPSAltitude"]
        if time_diff > timedelta(seconds=MAX_TIME_DIFFERENCE):
            error = GSVException(f"More than {MAX_TIME_DIFFERENCE} seconds between two succeeding frames: [{name}|{time_diff.total_seconds()} seconds]")
        v, v_vector = calculateVelocities(start_loc, end_loc, time_diff.total_seconds())
        if v > max_acceptable_velocity:
            error = GSVException(f"Velocity {v} [{v_vector}] is greater than {max_acceptable_velocity}")
        if error:
            image["error"] = str(error)
            logger.warn(f"{error} for {image['path']}")
            continue
        prev_date = date
        prev_image = image
        
    return valid_images

def process_into_videos(images, framerate, max_length, output_filepath, global_meta_path=None):
    frame_glob = output_filepath/"_processed/%05d.jpg"
    valid_images = write_images_to_dir(images, frame_glob.parent)

    if len(valid_images) < MIN_FRAMES_PER_VIDEO:
            raise FatalException(f"At least {MIN_FRAMES_PER_VIDEO} valid frames required, found {len(valid_images) or None}")    
    videos = []
    output_filename, _ = os.path.splitext(output_filepath.name)
    frames_per_video = int(max_length*framerate)
    number_of_images = len(valid_images)
    parts = ceil(number_of_images/frames_per_video)
    frame_cursor = 0

    for i in range(1, parts+1):
        logger.info(f"Processing video #{i} of {parts}")
        end   = frame_cursor + frames_per_video
        if i == parts-1:
            remaining_frames = number_of_images-end
            if remaining_frames < MIN_FRAMES_PER_VIDEO:
                end = number_of_images - MIN_FRAMES_PER_VIDEO
        end = min(end, len(valid_images))
        
        gpx_file = output_filepath.with_name(f"{output_filename}-{i}.gpx")
        mp4_file = output_filepath.with_name(f"{output_filename}-{i}_DIRTY.mp4")
        final_mp4_file = output_filepath.with_name(f"{output_filename}-{i}.mp4")
        first_image = valid_images[frame_cursor]
        logger.info(f"Using frame #{frame_cursor} to #{end}")
        logger.info(f"generating gpx file for video #{i} at {gpx_file}")
        start_date = valid_images[0]["date"] + frame_cursor*timedelta(seconds=1)/framerate
        generate_gpx_from_images(valid_images[frame_cursor:end], gpx_file, start_date=start_date, frame_rate=framerate)
        logger.info(f"generating video #{i} at {mp4_file}")
        create_video_from_images(frame_glob, mp4_file, frame_cursor, end-frame_cursor, frame_rate=framerate, date=first_image['date'])
        logger.info(f"adding gpmd data stream to video #{i} at {final_mp4_file}")
        make_video_gsv_compatible(mp4_file, gpx_file, final_mp4_file, framerate, is_gpmd=True)
        logger.info(f"copying metadata from first image into {final_mp4_file}")
        copy_metadata_from_file(global_meta_path or first_image['newpath'], final_mp4_file)
    
        delete_files(mp4_file)
        set_date_metadata(final_mp4_file, first_image['date'])
        videos.append((final_mp4_file, int(first_image["width"]), int(first_image["height"]), dict(images=valid_images[frame_cursor:end], gpx_file=str(gpx_file)), final_mp4_file))

        frame_cursor = end
    delete_files(frame_glob.parent)
    return videos

def write_images_to_dir(images: list[dict], dir: Path)->list[dict]:
    dir.mkdir(exist_ok=True)
    written_images = []
    for image in images:
        if image.get("error"):
            continue
        path: Path = image['path']
        newpath = dir/f"{len(written_images):05d}.jpg"
        shutil.copyfile(path, newpath)
        image["newpath"] = newpath
        written_images.append(image)
    return written_images
