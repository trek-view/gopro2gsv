from types import SimpleNamespace
from xml.dom.minidom import parseString, Element, Document
from pathlib import Path
import subprocess, sys, re
from gpxpy.gpx import GPXTrack, GPX, GPXTrackSegment, GPXTrackPoint

import importlib.resources


DEFAULT_FRAME_RATE = 5

MODULE_PATH = importlib.resources.files(__package__)
ASSETS_PATH = MODULE_PATH / "assets"
SUBMODULES  = MODULE_PATH/ "third-party"

class InvalidImageException(Exception):
    pass

from datetime import timedelta, datetime


STREAM_RE = re.compile(r"Stream (#\d+:\d+)\[\w+\]\(\w+\):\s+(\w+):\s+(\w+)\s+(.*)")


def run_command_silently(cmd, raise_for_status=True, **kw):
    try:
        output = subprocess.check_output(cmd, encoding='utf-8', **kw)
        return output.strip()
    except subprocess.CalledProcessError as e:
        error_message = e.output.strip()
        if raise_for_status:
            raise RuntimeError(f"Error running command '{cmd}': {error_message}")
        return error_message


def getText(nodelist):
    if not isinstance(nodelist, list):
        nodelist = nodelist.childNodes
    rc = []
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc.append(node.data)
    return ''.join(rc)

def parse_exif_metadata(content: bytes):
    doc: Document = parseString(content)
    root: Element = doc.getElementsByTagName("rdf:Description")[0]
    child: Element = None
    metadata = {}
    for child in root.childNodes:
        if child.nodeType == child.ELEMENT_NODE:
            value = getText(child)
            if first := metadata.get(child.tagName):
                if isinstance(first, list):
                    metadata[child.tagName].append(value)
                else:
                    metadata[child.tagName] = [first, value]
            else:
                metadata[child.tagName] = value

    return metadata

def get_exif_details(path: str):
    output = run_command_silently([get_exiftool(), "-ee", "-G3", "-n", "-X", "-api", "LargeFileSupport=1", path])
    return parse_exif_metadata(output)

def test_image(path):
    MUST_HAVES = [
        "GPS:GPSLatitudeRef",
        "GPS:GPSLatitude",
        "GPS:GPSLongitudeRef",
        "GPS:GPSLongitude",
        "GPS:GPSAltitudeRef",
        "GPS:GPSAltitude",
        "GPS:GPSDateStamp",
        "GPS:GPSTimeStamp",
    ]
    exif_data = get_exif_details(path)
    if not (projection_type := exif_data.get("XMP-GPano:ProjectionType")):
        raise InvalidImageException("Image must have `XMP-GPano:ProjectionType`")
    if projection_type != "equirectangular":
        raise InvalidImageException("Image's XMP-GPano:ProjectionType must be equal to `equirectangular`")
    for key in MUST_HAVES:
        if not (value := exif_data.get(key)):
            raise InvalidImageException(f"Image's exif data missing `{key}`")
    return exif_data

def generate_gpx_from_timelapse(dir: Path, gpx_path: Path):
    if not dir.exists():
        raise RuntimeError("Attempted to generate gpx from non-existent timelapse directory")
    output = run_command_silently([get_exiftool(), "-fileOrder", "gpsdatetime", "-p", ASSETS_PATH/"gpx.fmt", dir], stderr=subprocess.DEVNULL)
    with gpx_path.open("w") as f:
        f.write(output)
    return


def generate_gpx_from_images(images: list[dict], gpx_path: Path, frame_rate=DEFAULT_FRAME_RATE):
    gpx = GPX()
    track = GPXTrack()
    seg = GPXTrackSegment()
    gpx.tracks.append(track)
    track.segments.append(seg)
    date = images[0]['date']
    delta = timedelta(seconds=1)/frame_rate
    for i, image in enumerate(images):
        longitude = float(image['GPS:GPSLongitude'])
        latitude  = float(image[ 'GPS:GPSLatitude'])
        if image['GPS:GPSLongitudeRef'] == "W":
            longitude = -longitude
        if image['GPS:GPSLatitudeRef'] == "S":
            latitude = -latitude
        point = GPXTrackPoint(latitude=latitude, longitude=longitude, elevation=image['GPS:GPSAltitude'], time=date+i*delta)
        seg.points.append(point)
    content = gpx.to_xml()
    with gpx_path.open("w") as f:
        f.write(content)
    return


def create_video_from_images(glob: Path, mp4_path: Path, start=0, num_frames=None, frame_rate=DEFAULT_FRAME_RATE):
    cmd = [get_ffmpeg(), "-r", str(frame_rate)]
    if start:
        cmd.extend(["-start_number", str(start)])
    cmd.extend(["-i", glob])
    if num_frames:
        cmd.extend(["-vframes", str(num_frames)])
    cmd.extend(["-y", mp4_path]) #always overwrite

    run_command_silently(cmd, stderr=subprocess.DEVNULL)
    return

def copy_metadata_from_file(frame: Path, video: Path):
    run_command_silently([get_exiftool(),"-TagsFromFile",frame, "-all:all>all:all", video])

def make_video_gsv_compatible(video: Path, gpx: Path, output:Path, is_gpmd: bool):
    type_flag = "-g" if is_gpmd else "-c"
    run_command_silently([sys.executable, SUBMODULES/"telemetry-injector/telemetry-injector.py", type_flag, "-v", video, "-x", gpx, "-o", output])
    return

def get_ffmpeg():
    return 'ffmpeg'

def get_exiftool():
    return 'exiftool'

def overlay_nadir(video, overlay, output, video_width, video_height, is_watermark=False):
    overlay_height = int(0.15 * video_height)
    overlay_width = video_width
    overlay_offset = f"0:{video_height-overlay_height}"
    if is_watermark:
        overlay_width = int(0.15*video_width)
        overlay_height = f"h=ih*{video_height}/{video_width}"
        overlay_offset = f"{video_width-overlay_width}:0"
    # do_overlay(video, overlay, output, overlay_width, overlay_height, overlay_offset)
    run_command_silently([get_ffmpeg(), "-i", video, "-i", overlay, "-filter_complex", f"[1:v]scale={overlay_width}:{overlay_height}[overlay]; [0:v][overlay]overlay={overlay_offset}", "-c:a", "copy", "-map", "0", "-map", "-0:v", "-copy_unknown", "-y", output], stderr=subprocess.STDOUT)
    copy_metadata_from_file(video, output)

def get_streams(video: Path):
    output  = run_command_silently([get_ffmpeg(), "-i", video], stderr=subprocess.STDOUT, raise_for_status=False)
    streams  = []
    for stream in STREAM_RE.findall(output):
        streams.append(SimpleNamespace(id=stream[0], type=stream[1].lower(), codec=stream[2], misc=stream[3]))
    return streams

def parse_stream(stream: str):
    pass
    # run_command_silently([get_ffmpeg(), "-i", video, "-i", nadir, "-filter_complex", f"[0:v][1:v] overlay={nadir_offset}", "-copy_unknown", "-map_metadata", "0", "-y", output])
# print(test_image("/home/fqrious/tmp/fus-360-pho-002s6/MULTISHOT_0035_000000-2k.jpg"))

# def do_overlay(video, overlay, output, overlay_width, overlay_height, overlay_offset):
    