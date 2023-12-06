# telemetry-injector

## Introduction

This script;

1. takes a series of geotagged images/video with GPX file
2. parses out the telemetry into a gpx file
3. creates a camm / gpmd binary file from gpx
4. creates a video file from photos
5. injects the camm binary stream into the video

CAMM outputs are still WIP.

## Usage

```shell
python3 telemetry-injector.py -c -i INPUT_IMAGE_DIRECTORY/ -o OUTPUT_VIDEO_FILE.mp4
```

* `-g`: Flag to use gpmf metadata injection.
* `-c`: Flag to use camm metadata injection.
* `-i`: Input image directory.
* `-v`: Input mp4 files, should be mp4 video.
* `-x`: Input gpx files, should be mp4 video.
* `-o`: Output video file conataining metadata.

### Image Input

For `camm` images metadata injection
	
```shell
python3 telemetry-injector.py -c -i input_image_directory -o OUTPUT_VIDEO_FILE.mp4
```

For `gpmf` images metadata injection

```shell
python3 telemetry-injector.py -g -i input_image_directory -o OUTPUT_VIDEO_FILE.mp4
```

### Video Input

For `camm` video metadata injection
	
```shell
python3 telemetry-injector.py -c -v input_mp4_video_file -x input_gpx_file -o output_mp4_video_file
```

For `gpmf` video metadata injection

```shell
python telemetry-injector.py -g -v input_mp4_video_file -x input_gpx_file -o output_mp4_video_file
```