import argparse
import functools
import logging
import os
import pathlib
from pathlib import Path
import shutil

from dotenv import load_dotenv

from .errors import FatalException
from .gsv import GSV
from .imagetool import (fix_outlier, get_files_from_dir, process_into_videos,
                        write_images_to_dir)
from .shell_helper import (delete_files, get_exif_details, get_streams,
                           overlay_nadir)
from .sql_helper import DB
from .videotool import MINIMUM_GPS_POINTS, tag_all_images, video_to_images

FRAMES_PER_VIDEO = 300
TIMELAPSE_FRAME_RATE = 5
VALID_EXTRACT_FPS = [5, 2, 1, 0.5, 0.2]


def newLogger(name: str) -> logging.Logger:
    # Configure logging
    stream_handler = logging.StreamHandler()  # Log to stdout and stderr
    stream_handler.setLevel(logging.INFO)
    logging.basicConfig(
        level=logging.DEBUG,  # Set the desired logging level
        format=f"%(asctime)s [{name}] [%(levelname)s] %(message)s",
        handlers=[stream_handler],
        datefmt='%d-%b-%y %H:%M:%S'
    )

    return logging.getLogger("gopro2gsv")

def setLogFile(logger, file: Path):
    logger.info(f"Saving log to `{file.absolute()}`")
    handler = logging.FileHandler(file, "w")
    handler.formatter = logging.Formatter(fmt='%(levelname)s %(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S')
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    logger.info("=====================GoPro2GSV======================")



def parse_path(parser, path, is_file=True):
    p = pathlib.Path(path)
    if not p.exists():
        raise argparse.ArgumentTypeError(f"{p.absolute()}: no such file or directory")
    if is_file and p.is_dir():
        raise argparse.ArgumentTypeError(f"{p.absolute()}: expected file, got directory")
    elif p.is_file() and not is_file:
        raise argparse.ArgumentTypeError(f"{p.absolute()}: expected directory, got file")
    return p

def valid_nadir_range(value):
    ivalue = int(value)
    if 5 <= ivalue <= 30:
        return ivalue
    raise argparse.ArgumentTypeError(f"must be between 5 and 30 (inclusive), but got {ivalue}")

def parse_args():
    parser = argparse.ArgumentParser(description="GoPro to Google Street View converter")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--input_video", help="for timelapse video mode, the path to the .mp4 video", type=functools.partial(parse_path, parser, is_file=True))
    group.add_argument("--input_directory", help="Path to the directory of .jpg images", type=functools.partial(parse_path, parser, is_file=False))
    group.add_argument("--refresh_upload_status", action="store_true", help="rechecks all GSV uploaded sequences not in PROCESSED or FAILED states")

    parser.add_argument("--path_to_nadir", help="Path to the nadir image", type=functools.partial(parse_path, parser, is_file=True))
    parser.add_argument("--size_of_nadir", type=valid_nadir_range, help="Percentage of video the nadir will cover", default=150)

    parser.add_argument("--output_filepath", help="Output filepath for video")
    parser.add_argument("--upload_to_streetview", action="store_true", help="Upload image to StreetView")
    parser.add_argument("--force_relogin", action="store_true", help="Don't use saved authentication")
    parser.add_argument("--outlier_speed_meters_sec", "--outlier_speed", default=40, type=int, help="When a destination photo has a speed greater than the specified outlier speed it will be removed")
    parser.add_argument("--extract_fps", default=None, help="", type=float, choices=VALID_EXTRACT_FPS)
    parser.add_argument("--max_output_video_secs", default=60, help="Maximum length of video in seconds")
    parser.add_argument("--keep_extracted_frames", action="store_true", help="store a copy of the extracted images used to create final video (with geotags). ")

    args = parser.parse_args()
    is_photo_mode = False

    if args.input_directory:
        is_photo_mode = True
    

    return args, is_photo_mode


def gopro2gsv(args, is_photo_mode, logger: logging.Logger):
    videos: list[tuple[Path, int, int, dict|list[dict]]] = []
    log_filepath: Path = None
    streetview_id = None
    #init gsv if 
    database = DB()
    logger.info("====================================================")
    logger.info("=====================GoPro2GSV======================")
    logger.info("====================================================")
    if args.upload_to_streetview or args.refresh_upload_status:
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        key = os.getenv("GOOGLE_CLIENT_KEY")
        if not client_id or not client_secret:
            raise FatalException("--upload_to_streetview/--refresh_upload_status passed but `GOOGLE_CLIENT_ID` or `GOOGLE_CLIENT_SECRET` not found in env")
        creds = database.get_gsv_auth()
        if args.force_relogin:
            creds = None
        gsv = GSV(client_id, client_secret, creds)
        database.save_gsv_auth(gsv.credentials.to_json())

    if args.refresh_upload_status:
        statuses: list[tuple[str, str|None, str|None]] = []
        for id, _, _ in database.get_unfinished_gsv_uploads():
            logger.info(f"Updating status for {id}")
            statuses.append(gsv.get_status(id))
        database.update_gsv_statuses(statuses)
        return
    elif is_photo_mode:
        input_dir : pathlib.Path = args.input_directory
        if not args.output_filepath:
            args.output_filepath = input_dir/"gopro2gsv_output"
        output_filepath = Path(args.output_filepath)
        output_filepath.mkdir(parents=True, exist_ok=True)
        output_filename, _ = os.path.splitext(output_filepath.name)
        log_filepath    = output_filepath.with_name(output_filename+".log")
        setLogFile(logger, log_filepath)
        valid_images, invalid_files = get_files_from_dir(input_dir)
        valid_images = fix_outlier(valid_images, args.outlier_speed_meters_sec, invalid_files)

        processed_dir = output_filepath
        # gpx_file = input_dir/"processed.gpx"
        database.record_timelapse(invalid_files)
        logger.info(f"Copying {len(valid_images)} images to new directory: {processed_dir.absolute()}")
        write_images_to_dir(valid_images, processed_dir)

        videos = process_into_videos(valid_images, TIMELAPSE_FRAME_RATE, args.max_output_video_secs, processed_dir)
        delete_files(processed_dir)
    else:
        input_vid : Path = args.input_video
        if not args.output_filepath:
            name, _ = os.path.splitext(input_vid.name)
            output_filepath = input_vid.with_name(f"{name}-gopro2gsv_output")
        else:
            output_filepath = Path(args.output_filepath)
        log_filepath = output_filepath.with_name(os.path.splitext(output_filepath.name)[0] + ".log")
        setLogFile(logger, log_filepath)
        
        if not args.extract_fps:
            streams = get_streams(input_vid)
            if len(list(filter(lambda x: x.type == "video", streams))) > 1:
                raise FatalException("More than one video stream in input_video, consider passing `--extract_fps`")
            metadata = get_exif_details(input_vid)
            valid_frames = 0
            for k, v in metadata.items():
                if k.endswith(":GPSDateTime") and k.startswith("Track"):
                    valid_frames += len(v)
            if valid_frames < MINIMUM_GPS_POINTS:
                raise FatalException(f"Less than 10 valid frames in video: {len(v)} found")
            width, height = int(metadata['Track1:ImageWidth']), int(metadata['Track1:ImageHeight'])
            logger.info(f"Found {width}x{height} video with {valid_frames} valid frames at {input_vid}")
            videos.append((input_vid, width, height, metadata, output_filepath))
        else:
            invalid_files = []
            valid_images, video_fps, frame_glob = video_to_images(input_vid, output_filepath, framerate=args.extract_fps)
            if args.keep_extracted_frames:
                logger.info(f"Tagging {len(valid_images)} images")
                tag_all_images(valid_images)
            valid_images = fix_outlier(valid_images, args.outlier_speed_meters_sec, invalid_files)
            
            database.record_timelapse(invalid_files)
            videos = process_into_videos(valid_images, TIMELAPSE_FRAME_RATE, args.max_output_video_secs, output_filepath, frame_glob=frame_glob)

            if args.keep_extracted_frames:
                output_filename, _ = os.path.splitext(output_filepath.name)
                frames_dir = output_filepath.with_name(f"{output_filename}-images")
                delete_files(frames_dir)
                logger.info(f"--keep_extracted_frames passed, moving processed frames into `{frames_dir}`")
                shutil.move(frame_glob.parent, frames_dir)
            delete_files(frame_glob.parent.parent)
    
    for i, (video, width, height, more, output_path) in enumerate(videos):
        name, _ = os.path.splitext(output_path.name)
        newpath: Path = video
        logger.info(f"Post-processing video #{i+1} of {len(videos)}")
        if args.path_to_nadir:
            logger.info("Adding nadir to video")
            newpath = output_path.with_name(f"{name}_with-nadir.mp4")
            newpath.parent.mkdir(exist_ok=True, parents=True)
            overlay_nadir(video, args.path_to_nadir, newpath, width, height, height_ratio=args.size_of_nadir/100)
        
        # delete input video file if it's created by us
        if more.get('gpx_file') and video != newpath:
            delete_files(video)

        if args.upload_to_streetview:
            logger.info(f"Uploading `{newpath}` to GSV")
            resp, streetview_id = gsv.upload_video(newpath)
            logger.info(f"[SUCCESS] Sequence uploaded for {newpath}! Sequence id: {streetview_id}")

        if is_photo_mode:
            database.insert_output(args.input_directory.absolute(), newpath, log_filepath, streetview_id=streetview_id, is_photo_mode=True, video_info=more)
        else:
            database.insert_output(args.input_video.absolute(), newpath, log_filepath, streetview_id=streetview_id, is_photo_mode=False)

        logger.info(f"Video #{i+1} saved at `{newpath}`")

def main(args, is_photo_mode):
    logger = newLogger("GoPro2GSV")
    try:
        gopro2gsv(args, is_photo_mode, logger)
    except FatalException as e:
        logger.error(e)
    

if __name__ == "__main__":
    load_dotenv()
    args, is_photo_mode = parse_args()
    main(args, is_photo_mode)
