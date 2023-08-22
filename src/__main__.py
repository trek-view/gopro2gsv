import argparse, pathlib, shutil
from math import ceil
from pathlib import Path
import functools
import re

from .shell_helper import test_image, InvalidImageException, generate_gpx_from_timelapse, generate_gpx_from_images, create_video_from_images, make_video_gsv_compatible, copy_metadata_from_file, get_exif_details, overlay_nadir
from types import SimpleNamespace
from datetime import datetime, timedelta
from dateutil.parser import parse as parse_date

from .imagetool import get_valid_images, write_images_to_dir


import os

def strip_extension(filename):
    return os.path.splitext(filename)[0]

class FatalException(Exception):
    pass

def parse_path(parser, path, is_file=True):
    p = pathlib.Path(path)
    if not p.exists():
        parser.error(f"{p.absolute()}: no such file or directory")
    if is_file and p.is_dir():
        parser.error(f"{p.absolute()}: expected file, got directory")
    elif p.is_file() and not is_file:
        parser.error(f"{p.absolute()}: expected directory, got file")
    return p

def parse_args():
    parser = argparse.ArgumentParser(description="GoPro to Google Street View converter")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--input_video", help="for timelapse video mode, the path to the .mp4 video", type=functools.partial(parse_path, parser, is_file=True))
    group.add_argument("--input_directory", help="Path to the directory of .jpg images", type=functools.partial(parse_path, parser, is_file=False))

    parser.add_argument("--video_telemetry_format", choices=["CAMM", "GPMD", "camm", "gpmd"], help="Video telemetry format (CAMM or GPMD)", type=str.upper)

    group = parser.add_mutually_exclusive_group(required=False)

    group.add_argument("--path_to_nadir", help="Path to the nadir image", type=functools.partial(parse_path, parser, is_file=True))
    group.add_argument("--watermark", help="Path to watermark", type=functools.partial(parse_path, parser, is_file=True))

    parser.add_argument("--output_filepath", help="Output filepath for video")
    parser.add_argument("--upload_to_streetview", action="store_true", help="Upload image to StreetView")

    args = parser.parse_args()
    is_photo_mode = False

    if args.input_directory:
        is_photo_mode = True
        if not args.video_telemetry_format:
            parser.error("--video_telemetry_format is required in photo mode")
    

    return args, is_photo_mode



def main(args, is_photo_mode):
    videos: list[tuple[Path, int, int]] = []
    if is_photo_mode:
        input_dir : pathlib.Path = args.input_directory
        if not args.output_filepath:
            args.output_filepath = input_dir/"gopro2gsv_output"
        output_filepath = Path(args.output_filepath)
        output_filepath.mkdir(parents=True, exist_ok=True)
        output_filename = output_filepath.name
        images = get_valid_images(input_dir)
        processed_dir = output_filepath
        # gpx_file = input_dir/"processed.gpx"
        write_images_to_dir(images, processed_dir)
        number_of_images = len(images)
        images_per_video = 300
        images_per_video = min(images_per_video, number_of_images//ceil(number_of_images/images_per_video)) #make it such that there's the same or close to the same number of images per video
        for i in range(ceil(number_of_images/images_per_video)):
            start = i * images_per_video
            end   = start + images_per_video
            gpx_file = output_filepath.with_name(f"{output_filename}-{i}.gpx")
            mp4_file = output_filepath.with_name(f"{output_filename}-{i}_DIRTY.mp4")
            final_mp4_file = output_filepath.with_name(f"{output_filename}-{i}.mp4")
            first_image = images[start]
            generate_gpx_from_images(images[start:end], gpx_file)
            create_video_from_images(processed_dir/f"%05d.jpg", mp4_file, start, images_per_video, frame_rate=5)
            make_video_gsv_compatible(mp4_file, gpx_file, final_mp4_file, is_gpmd=args.video_telemetry_format == "GPMD")
            copy_metadata_from_file(first_image['newpath'], final_mp4_file)
            videos.append((final_mp4_file, int(first_image["File:ImageWidth"]), int(first_image["File:ImageHeight"])))
    else:
        input_vid : Path = args.input_video
        if not args.output_filepath:
            name = strip_extension(input_vid.name)
            args.output_filepath = input_vid.with_name(f"{name}-gopro2gsv_output")
        metadata = get_exif_details(input_vid)
        valid_frames = 0
        for k, v in metadata.items():
            if k.endswith(":GPSDateTime") and k.startswith("Track"):
                valid_frames += len(v)
        if valid_frames < 10:
            raise FatalException(f"Less than 10 valid frames in video: {len(v)} found")
        videos.append((input_vid, int(metadata['Track1:ImageWidth'][0]), int(metadata['Track1:ImageHeight'][0])))
    for video, width, height in videos:
        name = strip_extension(video.name)
        newpath = video
        if args.path_to_nadir:
            newpath = video.with_name(f"{name}_with-nadir.mp4")
            overlay_nadir(video, args.path_to_nadir, newpath, width, height)
        elif args.watermark:
            newpath = video.with_name(f"{name}_watermarked.mp4")
            overlay_nadir(video, args.watermark, newpath, width, height, True)
if __name__ == "__main__":
    args, is_photo_mode = parse_args()
    main(args, is_photo_mode)