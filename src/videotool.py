from concurrent.futures import ThreadPoolExecutor
import math
import os
import pathlib, shutil
from pathlib import Path
import re

from src.utils import metadata_dict

from .shell_helper import copy_metadata_from_file, delete_files, set_exif_metadata, splitvideo, test_image, InvalidImageException, get_exif_details_for_dir, get_exif_details
from .errors import FatalException
from datetime import datetime, timedelta
from dateutil.parser import parse as parse_date
from math import ceil
from collections import UserDict

MINIMUM_GPS_POINTS = 10

def get_gps_data(metadata, video_fps=None):
    groups = []
    gpsData = None
    group = None
    num_frames = 0
    for k, v in metadata.key_values:
        splits = k.split(":")
        if len(splits) != 2:
            continue
        key = splits[1]
        if key == "VideoFrameRate" and not video_fps:
            video_fps = float(v)
        if key == "GPSDateTime":
            v = parse_date(v.replace(":", "-", 2))
            gpsData = {}
            group = {}
            group["date"] = v
            group["data"] = []
            groups.append(group)
        if key in ["GPSLatitude", "GPSLongitude", "GPSAltitude"]:
            gpsData[f"GPS:{key}"] = float(v)
            if len(gpsData) == 3:
                num_frames += 1
                group["data"].append(gpsData)
                gpsData = {}
    media_start_time = groups[0]["date"]
    media_duration   = float(metadata["QuickTime:Duration"])
    groups.append({"date": media_start_time + timedelta(seconds=media_duration)})
    points = []
    for i, group in enumerate(groups[:-1]):
        start_time, end_time = group["date"], groups[i+1]["date"]
        duration = (end_time - start_time)
        timediff = duration/len(group['data'])
        for i, point in enumerate(group["data"]):
            point["date"] = start_time + timediff*i
            point["media_time"] = (point["date"] - media_start_time).total_seconds()
            points.append(point)
    if not video_fps:
        raise FatalException("Unable to parse input video frame rate, cannot continue...")
    num_frames = math.ceil(video_fps * media_duration)
    gps_cursor = 0
    frames = []
    for f in range(num_frames):
        frame_time = f/video_fps
        if not (gps_cursor+1 == len(points) or frame_time < points[gps_cursor+1]["media_time"]):
            gps_cursor += 1
        point = points[gps_cursor]
        frame = point.copy()
        frame['frame_time'] = frame_time
        frames.append(frame)
    return (video_fps, points, frames)

def validate_input_video(name, metadata):
    _, mode = os.path.splitext(name)
    if mode == ".360":
        if not name.startswith("GS"):
            raise FatalException("Filename must start with GS")
        model = metadata.get("GoPro:Model", None)
        if model != "GoPro Max":
            raise FatalException(f"Unknown GoPro:Model: `{model}`")

    elif mode == ".mp4":
        if not (name.startswith("GS") or name.startswith("VIDEO")):
            raise FatalException("Filename must start with GS or VIDEO")
        ptype = metadata.get("XMP-GSpherical:ProjectionType", None)
        if ptype != "equirectangular":
            raise FatalException(f"Projection Type must be equirectangular, got {ptype}")
    else:
        raise FatalException(f"Unknown video mode `{mode}`")

    metatrack = None
    for ns in metadata["namespaces"]:
        if not ns.startswith("Track"):
            continue
        if metadata.get(f"{ns}:MetaFormat") == "gpmd":
            metatrack = ns
    
    if not metatrack:
        raise FatalException("Could not find gpmd metadata track")
    num_gps_points = len(metadata.list(metatrack+":GPSDateTime"))
    if num_gps_points < MINIMUM_GPS_POINTS:
        raise FatalException(f"At least {MINIMUM_GPS_POINTS} GPS points required, got {num_gps_points}")

def video_to_images(video: Path, out: Path, framerate:int=None):
    metadata = get_exif_details(video)
    validate_input_video(video.name, metadata)

    fps, gps_points, frames = get_gps_data(metadata, framerate)
    frames_dir = out/"_preprocessing"
    frames_dir.mkdir(exist_ok=True, parents=True)
    numframes = splitvideo(video, frames_dir/"FRAME-%05d.jpg", framerate)
    assert abs(numframes-len(frames))<3, "extracted frames less than anticipated frames"
    first_frame_path = frames_dir/("FRAME-%05d.jpg"%1)
    copy_metadata_from_file(video, first_frame_path)
    for i in range(min(numframes, len(frames))):
        frames[i]["path"] = frames_dir/("FRAME-%05d.jpg"%(i+1))
        frames[i]["newpath"] = frames[i]["path"]
        frames[i]["File:ImageWidth"] = 1
        frames[i]["File:ImageHeight"] = 1
    tag_image(frames[0])
    return frames, fps, frames_dir/"FRAME-%05d.jpg"

def tag_image(image):
    path = image['path']
    d: datetime = image["date"]
    dfm = d.isoformat().replace("-", ":")
    set_exif_metadata(path, 
                ("gpsposition", "{},{}".format(image["GPS:GPSLatitude"], image["GPS:GPSLongitude"])), 
                ("GPSAltitude", image["GPS:GPSAltitude"]),
                ("GPSAltitudeRef", image["GPS:GPSAltitude"]),
                ("xmp:ProjectionType", "equirectangular"),
                ("Media*Date", dfm), ("Track*Date", dfm),
                ("AllDates",dfm), ("GPSDateStamp", dfm),
                ("GPSTimeStamp", dfm.split("T")[1]),
                ("XMPToolkit", "gopro2gsv")
    )

def tag_all_images(images: list[metadata_dict]):
    executor = ThreadPoolExecutor(max_workers=20)
    executor.map(tag_image, images)