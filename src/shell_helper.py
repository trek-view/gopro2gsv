from types import SimpleNamespace
from xml.dom.minidom import parseString, Element, Document
from pathlib import Path
import subprocess, sys, re, os, shutil
from gpxpy.gpx import GPXTrack, GPX, GPXTrackSegment, GPXTrackPoint
from xml.etree import ElementTree
import tempfile
import importlib.resources

from .utils import metadata_dict
from .errors import FatalException

from logging import getLogger
logger = getLogger("gopro2gsv.shell_helper")

DEFAULT_FRAME_RATE = 5

MODULE_PATH = importlib.resources.files(__package__)
ASSETS_PATH = MODULE_PATH / "assets"
SUBMODULES  = MODULE_PATH/ "third-party"

class InvalidImageException(Exception):
    pass

from datetime import timedelta, datetime


STREAM_RE = re.compile(r"Stream (#\d+:\d+)\[\w+\]\(\w+\):\s+(\w+):\s+(\w+)\s+(.*)")


def run_command_silently(cmd, decode_output=True, raise_for_status=True, **kw):
    cmd = list(map(str, cmd))
    cmd_str = " ".join(map(repr, cmd))
    try:

        logger.debug(f"Running Command:\t{cmd_str}")
        if not decode_output:
            return subprocess.check_output(cmd, universal_newlines=True, **kw)
        output = subprocess.check_output(cmd, encoding='utf-8', **kw)
        return output.strip()
    except subprocess.CalledProcessError as e:
        error_message = e.output.strip()
        if raise_for_status:
            raise RuntimeError(f"Error running command `{cmd_str}`: {error_message}")
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
    root: Element = None
    out_vals: dict[Path, dict] = {}
    for root in doc.getElementsByTagName("rdf:Description"):
        file = Path(root.getAttribute("rdf:about"))
        child: Element = None
        metadata = metadata_dict(path=file)
        metadata["namespaces"] = [attr[6:] for attr in root.attributes.keys() if attr.startswith('xmlns:')]
        for child in root.childNodes:
            if child.nodeType == child.ELEMENT_NODE:
                value = getText(child)
                metadata[child.tagName] = value
        out_vals[file] = metadata
    return out_vals

def get_exif_details(path: str):
    try:
        output = run_command_silently([get_exiftool(), "-ee", "-G3", "-n", "-X", "-api", "LargeFileSupport=1", path])
        return next(iter(parse_exif_metadata(output).values()))
    except BaseException as e:
        raise InvalidImageException(f"Could not get exif metadata from `{path}`") from e

def get_exif_details_for_dir(path: Path):
    try:
        output = run_command_silently([get_exiftool(), "-ee", "-G3", "-n", "-X", "-api", "LargeFileSupport=1", path], raise_for_status=False)
        return parse_exif_metadata(output)
    except BaseException as e:
        raise InvalidImageException(f"Could not get exif metadata from `{path}`") from e

def test_image(exif_data):
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
    if not (projection_type := exif_data.get("XMP-GPano:ProjectionType")):
        raise InvalidImageException("Image must have `XMP-GPano:ProjectionType`")
    if projection_type != "equirectangular":
        raise InvalidImageException("Image's XMP-GPano:ProjectionType must be equal to `equirectangular`")
    for key in MUST_HAVES:
        if not (value := exif_data.get(key)):
            raise InvalidImageException(f"Image's exif data missing `{key}`")
    return True

def generate_gpx_from(dir: Path):
    if not dir.exists():
        raise FatalException("Attempted to generate gpx from non-existent timelapse directory")
    output = run_command_silently([get_exiftool(), "-fileOrder", "gpsdatetime", "-p", ASSETS_PATH/"gpx.fmt", dir], stderr=subprocess.DEVNULL)
    return output


def generate_gpx_from_images(images: list[dict], gpx_path: Path, frame_rate=DEFAULT_FRAME_RATE, start_date=None):
    gpx = GPX()
    gpx.nsmap["gopro2gsv"] = "https://github.com/trek-view/gopro2gsv"
    track = GPXTrack()
    seg = GPXTrackSegment()
    gpx.tracks.append(track)
    track.segments.append(seg)
    date = start_date or images[0]['date']
    delta = timedelta(seconds=1)/frame_rate
    for i, image in enumerate(images):
        longitude = float(image['GPS:GPSLongitude'])
        latitude  = float(image[ 'GPS:GPSLatitude'])
        if image.get('GPS:GPSLongitudeRef', None) == "W":
            longitude = -longitude
        if image.get('GPS:GPSLatitudeRef', None) == "S":
            latitude = -latitude
        point = GPXTrackPoint(latitude=latitude, longitude=longitude, elevation=image['GPS:GPSAltitude'], time=date+i*delta)
        ext1 = ElementTree.Element("gopro2gsv:InputPhoto")
        ext1.text = str(image['path'])
        point.extensions.append(ext1)
        seg.points.append(point)
    content = gpx.to_xml(version='1.1')
    with gpx_path.open("w") as f:
        f.write(content)
    return


def create_video_from_images(glob: Path, mp4_path: Path, start=0, num_frames=None, frame_rate=DEFAULT_FRAME_RATE, date=datetime.today()):
    cmd = [get_ffmpeg(), "-r", str(frame_rate)]
    if start:
        cmd.extend(["-start_number", str(start)])
    cmd.extend(["-i", glob])
    if num_frames:
        cmd.extend(["-vframes", str(num_frames)])
    cmd.extend(["-y", mp4_path]) #always overwrite

    run_command_silently(cmd, stderr=subprocess.DEVNULL)
    return

# returns number of frames
def splitvideo(video:Path, out:Path, framerate=None) -> int:
    start_time = datetime.now()
    if os.listdir(out.parent):
        raise FatalException(f"Cannot split into `{str(out.parent)}`, directory not empty")
    cmd = [get_ffmpeg(), "-i", video]
    if framerate:
        cmd.extend(["-r", str(framerate)])
    _, ext = os.path.splitext(video)
    if ext == '.360':
        # cmd.extend(["-filter_complex", '[0:v:0][0:v:1]vstack=inputs=2,v360=eac:equirect,scale=2*trunc(iw/2):2*trunc(ih/2)[out]', '-map', '[out]'])
        cmd.extend(["-filter_complex", '[0:v:0][0:v:1]vstack=inputs=2,v360=eac:equirect,crop=iw:ih:mod(iw\,2):mod(ih\,2)[out]', '-map', '[out]'])
    cmd.extend(["-y", out]) #always overwrite

    run_command_silently(cmd, stderr=subprocess.DEVNULL)
    num_frames = len(os.listdir(out.parent))
    logger.info(f"video `{video}` split into {num_frames} frames, took {(datetime.now() - start_time).total_seconds()} seconds")
    return num_frames
    

def copy_metadata_from_file(from_: Path, to_: Path):
    run_command_silently([get_exiftool(),"-TagsFromFile",from_, "-all:all>all:all", to_])
    delete_files(to_.with_name(to_.name+"_original"))

def set_exif_metadata(video:Path, *key_values: tuple[str,str]):
    args = []
    for k, v in key_values:
        args.append(f"-{k}={v}")
    run_command_silently([get_exiftool(), *args, video])
    delete_files(video.with_name(video.name+"_original"))

def set_date_metadata(video: Path, date: datetime):
    dfm = date.isoformat().replace("-", ":")
    set_exif_metadata(video, ("Media*Date", dfm), ("Track*Date", dfm), ("AllDates",dfm))

def make_video_gsv_compatible(video: Path, gpx: Path, output:Path, framerate, is_gpmd: bool):
    type_flag = "-g" if is_gpmd else "-c"
    run_command_silently([sys.executable, MODULE_PATH/"telemetry_injector/telemetry-injector.py", type_flag, "-v", video, "-x", gpx, "-o", output, "-r", framerate])
    return

def get_ffmpeg():
    return os.environ.get("FFMPEG_PATH") or 'ffmpeg'

def get_exiftool():
    return os.environ.get("EXIFTOOL_PATH") or 'exiftool'

def get_magick():
    return os.environ.get("MAGICK_PATH") or 'magick'

def overlay_nadir(video, overlay, output, video_width, video_height, height_ratio=0.25):
    overlay_height = int(height_ratio * video_height)
    overlay_width = video_width
    overlay_offset = f"0:{video_height-overlay_height}"
    with tempfile.NamedTemporaryFile() as f:
        logger.debug(f"Pre-processing nadir at {f.name}")
        run_command_silently([get_magick(), "convert", overlay, "-rotate", 180, "-distort", "depolar", 0, "-flip", "-flop", f.name])

        run_command_silently([get_ffmpeg(), "-i", video, "-i", f.name, "-filter_complex", f'[1:v]scale={overlay_width}:{overlay_height}[overlay]; [0:v][overlay]overlay={overlay_offset}', "-c:a", "copy", "-map", "0", "-map", "-0:v", "-copy_unknown", "-y", output], stderr=subprocess.STDOUT)
        copy_metadata_from_file(video, output)

def get_streams(video: Path):
    output  = run_command_silently([get_ffmpeg(), "-i", video], stderr=subprocess.STDOUT, raise_for_status=False)
    streams  = []
    for stream in STREAM_RE.findall(output):
        streams.append(SimpleNamespace(id=stream[0], type=stream[1].lower(), codec=stream[2], misc=stream[3]))
    return streams

def delete_files(*files: Path):
    for file in files:
        try:
            if file.is_dir():
                shutil.rmtree(file)
            else:
                os.remove(file)
        except Exception as e:
            pass


def parse_stream(stream: str):
    pass
    # run_command_silently([get_ffmpeg(), "-i", video, "-i", nadir, "-filter_complex", f"[0:v][1:v] overlay={nadir_offset}", "-copy_unknown", "-map_metadata", "0", "-y", output])
# print(test_image("/home/fqrious/tmp/fus-360-pho-002s6/MULTISHOT_0035_000000-2k.jpg"))

# def do_overlay(video, overlay, output, overlay_width, overlay_height, overlay_offset):
    
if __name__ == "__main__":
    out = run_command_silently(["magick", "convert", "./stock_nadirs/trek-view-circle-nadir.png", "-rotate", 180, "-distort", "depolar", 0, "-flip", "-flop", "-"], decode_output=False)
    print(type(out), len(out))