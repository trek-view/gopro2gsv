import argparse
import functools
import os
import pathlib
from math import ceil
from pathlib import Path
import typing

from .imagetool import get_valid_images, write_images_to_dir
from .shell_helper import (copy_metadata_from_file, create_video_from_images,
                           generate_gpx_from_images, get_exif_details,
                           make_video_gsv_compatible, overlay_nadir,
                           get_streams)
from .gsv import GSV
from .sql_helper import DB
from .errors import FatalException
from dotenv import load_dotenv

import logging

def newLogger(name: str) -> logging.Logger:
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,  # Set the desired logging level
        format=f"%(asctime)s [{name}] [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(),  # Log to stdout and stderr
        ],
        datefmt='%d-%b-%y %H:%M:%S'
    )

    return logging.getLogger(__name__)

def setLogFile(logger, file: Path):
    logger.info(f"Saving log to `{file.absolute()}`")
    handler = logging.FileHandler(file)
    handler.formatter = logging.Formatter(fmt='%(levelname)s %(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S')
    logger.addHandler(handler)
    logger.info("=====================GoPro2GSV======================")



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
    parser.add_argument("--force_relogin", action="store_true", help="Don't use saved authentication")

    args = parser.parse_args()
    is_photo_mode = False

    if args.input_directory:
        is_photo_mode = True
        if not args.video_telemetry_format:
            parser.error("--video_telemetry_format is required in photo mode")
    

    return args, is_photo_mode

def get_metadata_item(metadata: list|str, key):
    value = metadata[key]
    if isinstance(value, list):
        return value[0]
    return value


def main(args, is_photo_mode):
    videos: list[tuple[Path, int, int, dict|list[dict]]] = []
    log_filepath: Path = None
    streetview_id = None
    #init gsv if 
    database = DB()
    logger = newLogger("GoPro2GSV")
    logger.info("====================================================")
    logger.info("=====================GoPro2GSV======================")
    logger.info("====================================================")
    if args.upload_to_streetview:
        secret = os.getenv("GOOGLE_CLIENT_SECRET")
        client_id = os.getenv("GOOGLE_APP_ID")
        key = os.getenv("GOOGLE_CLIENT_KEY")
        if not client_id or not secret:
            raise FatalException("--upload_to_streetview passed but `GOOGLE_APP_ID` or `GOOGLE_CLIENT_SECRET` not found in env")
        creds = database.get_gsv_auth()
        if args.force_relogin:
            creds = None
        gsv = GSV(client_id, secret, creds)
        database.save_gsv_auth(gsv.credentials.to_json())
        
    if is_photo_mode:
        input_dir : pathlib.Path = args.input_directory
        if not args.output_filepath:
            args.output_filepath = input_dir/"gopro2gsv_output"
        output_filepath = Path(args.output_filepath)
        output_filepath.mkdir(parents=True, exist_ok=True)
        output_filename = output_filepath.name
        log_filepath    = output_filepath.with_name(output_filename+".log")
        setLogFile(logger, log_filepath)
        images = get_valid_images(input_dir)
        processed_dir = output_filepath
        # gpx_file = input_dir/"processed.gpx"
        logger.info(f"Copying {len(images)} images to new directory: {processed_dir.absolute()}")
        write_images_to_dir(images, processed_dir)
        number_of_images = len(images)
        images_per_video = 300
        images_per_video = min(images_per_video, number_of_images//ceil(number_of_images/images_per_video)) #make it such that there's the same or close to the same number of images per video
        parts = ceil(number_of_images/images_per_video)
        for i in range(1, parts+1):
            logger.info(f"Processing video #{i} of {parts}")
            start = (i-1) * images_per_video
            end   = start + images_per_video
            gpx_file = output_filepath.with_name(f"{output_filename}-{i}.gpx")
            mp4_file = output_filepath.with_name(f"{output_filename}-{i}_DIRTY.mp4")
            final_mp4_file = output_filepath.with_name(f"{output_filename}-{i}.mp4")
            first_image = images[start]
            logger.info(f"generating gpx file for video #{i} at {gpx_file}")
            generate_gpx_from_images(images[start:end], gpx_file)
            logger.info(f"generating video #{i} at {mp4_file}")
            create_video_from_images(processed_dir/f"%05d.jpg", mp4_file, start, images_per_video, frame_rate=5)
            logger.info(f"adding {args.video_telemetry_format} data stream to video #{i} at {final_mp4_file}")
            make_video_gsv_compatible(mp4_file, gpx_file, final_mp4_file, is_gpmd=args.video_telemetry_format == "GPMD")
            logger.info(f"copying metadata from first image into {final_mp4_file}")
            copy_metadata_from_file(first_image['newpath'], final_mp4_file)
            videos.append((final_mp4_file, int(get_metadata_item(first_image, "File:ImageWidth")), int(get_metadata_item(first_image, "File:ImageHeight")), images[start:end]))
    else:
        input_vid : Path = args.input_video
        if not args.output_filepath:
            name, _ = os.path.splitext(input_vid.name)
            args.output_filepath = input_vid.with_name(f"{name}-gopro2gsv_output")
        output_filename, _ = os.path.splitext(args.output_filepath.name)
        log_filepath    = args.output_filepath.with_name(output_filename+".log")
        streams = get_streams(input_vid)
        if len(list(filter(lambda x: x.type == "video", streams))) > 1:
            raise FatalException("More than one video stream in input_video")
        metadata = get_exif_details(input_vid)
        valid_frames = 0
        for k, v in metadata.items():
            if k.endswith(":GPSDateTime") and k.startswith("Track"):
                valid_frames += len(v)
        if valid_frames < 10:
            raise FatalException(f"Less than 10 valid frames in video: {len(v)} found")
        width, height = int(get_metadata_item(metadata, 'Track1:ImageWidth')), int(get_metadata_item(metadata, 'Track1:ImageHeight'))
        logger.info(f"Found {width}x{height} video with {valid_frames} valid frames at {input_vid}")
        videos.append((input_vid, width, height, metadata))
    
    for i, (video, width, height, more) in enumerate(videos):
        name, _ = os.path.splitext(video.name)
        newpath = video
        logger.info(f"Post-processing video #{i+1} of {len(videos)}")
        if args.path_to_nadir:
            logger.info("Adding nadir to video")
            newpath = video.with_name(f"{name}_with-nadir.mp4")
            overlay_nadir(video, args.path_to_nadir, newpath, width, height)
        elif args.watermark:
            logger.info("Adding watermark to video")
            newpath = video.with_name(f"{name}_watermarked.mp4")
            overlay_nadir(video, args.watermark, newpath, width, height, True)
        if args.upload_to_streetview:
            logger.info(f"Uploading `{newpath}` to GSV")
            resp, streetview_id = gsv.upload_video(newpath)
            logger.info(f"[SUCCESS] Sequence uploaded for {newpath}! Sequence id: {streetview_id}")

        if is_photo_mode:
            database.insert_output(args.input_directory.absolute(), newpath, log_filepath, streetview_info=streetview_id, is_photo_mode=True, images=more)
        else:
            database.insert_output(args.input_video.absolute(), newpath, log_filepath, streetview_info=streetview_id, is_photo_mode=False)

if __name__ == "__main__":
    load_dotenv()
    args, is_photo_mode = parse_args()
    main(args, is_photo_mode)
