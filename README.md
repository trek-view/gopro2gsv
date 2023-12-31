# GoPro2GSV

Processes .jpg images and .mp4/.360 videos shot on GoPro MAX or Fusion cameras and uploads to Google Street View.

## Overview

Here are Trek View we use GoPro Fusion and MAX cameras to record 360 images and videos.

The results of this work is published to either Google StreetView or Mapillary. In many cases we apply a nadir to these images to brand the video with our logo before uploading them.

Both these tools accept video uploads containing GPMF telemetry tracks.

To suport this workflow GoPro2GSV supports 6 modes;

1. equirectangular mp4 video -> final video
2. equirectangular timelapse frames -> final video
3. equirectangular mp4 video -> timelapse frames -> final video
4. .360 mode -> max2sphere -> timelapse frames -> final video (for MAX cameras)

Each mode offer different settings, but ultimately the aim of GoPro2GSV is for a user to take any 360 image or video generated by a GoPro 

**IMPORTANT:** GoPro2GSV does not support videos shot in timelapse or timewarp mode. This is because the logic described in the following posts is not implemented;

* Timelapse: https://www.trekview.org/blog/turn-gopro-timelapse-video-into-timelapse-images/
* Timewarp: https://www.trekview.org/blog/turn-gopro-timewarp-video-into-timelapse-images/ 

## Usage

### Setup

Install the required dependencies using:

```shell
# clone the latest code
git clone https://github.com/trek-view/gopro2gsv
cd gopro2gsv
# create a venv
python3 -m venv gopro2gsv-venv
source gopro2gsv-venv/bin/activate
# install requirements
pip3 install -r requirements.txt
git submodule update --init
python3 setup.py build
```

You will also need: 

* [Imagemagick](https://imagemagick.org/script/download.php)
* [ffmpeg](https://www.ffmpeg.org/download.html)
* [exiftool](https://exiftool.org/install.html)

These must be installed in the path. You can check this by running `magick`, `ffmpeg` , `exiftool` from the CLI. If it returns information about the tools, they are correctly installed.

On a Mac, you can install these quickly using brew as follows;

```shell
brew install ffmpeg exiftool imagemagick
```

If these are installed in the default paths no more action is needed (generally the case if installed using defaults). However, if the paths are custom, you will need to set these in the `.env` file under:

```txt
MAGICK_PATH=
FFMPEG_PATH=
EXIFTOOL_PATH=
```

### If you intent to upload to Street View

You need to set your Google keys if you intend to upload to GSV. First copy the `.env` file

```shell
cp .env.example .env
```

And then add your keys. The process to generated keys is described in `design/mvp/gsv-specification.md`

### Run

The base script can be run as follows;

```shell
python3 gopro2gsv.py
```

The options available to run differ by mode as follows;

#### Mode 1: equirectangular mp4 video -> final video

* `--input_video` (required): for timelapse video mode, the path to the `.mp4` video
	* e.g. `/path/to/my/file-in.mp4`
* `--path_to_nadir` (optional): a square nadir to be added to the images.
	* e.g. `/path/to/nadir.png`
* `--size_of_nadir` (optional, must use with `--path_to_nadir`): percentage height of output video nadir should cover. Default is 25% if not passed.
	* e.g. `25` (%)
* `--output_filepath` (required): name of video and directory for output. All log and GPX files will be named / placed using this information.
	* e.g. `/path/to/my/file-out`
* `--upload_to_streetview` (optional): if passed will upload the image to StreetView (will require user to authenticate)

#### Mode 2: equirectangular timelapse frames -> final video

* `--input_directory` (required): for timelapse photo mode, the path to the directory of `.jpg` images
	* e.g. `/path/to/my/directory`
* `--path_to_nadir` (optional): a square nadir to be added to the images.
	* e.g. `/path/to/nadir.png`
* `--size_of_nadir` (optional, must use with `--path_to_nadir`): percentage height of output video nadir should cover. Default is 25% if not passed.
	* e.g. `25` (%)
* `--max_output_video_secs` (optional) The maximum length of any video in the output in seconds. May result in multiple video files per output if input cannot be packed into maximum video length specified. Default is `60` seconds (300 frames)
	* e.g. `30` seconds
* `--output_filepath` (required): name of video and directory for output. All log and GPX files will be named / placed using this information.
	* e.g. `/path/to/my/file-out`
* `--upload_to_streetview` (optional): if passed will upload the image to StreetView (will require user to authenticate)

#### Mode 3: equirectangular mp4 video -> timelapse frames -> final video

* `--input_video` (required): for timelapse video mode, the path to the `.mp4` video
	* e.g. `/path/to/my/file-in.mp4`
	* e.g. `/path/to/my/directory`
* `--extract_fps` (required): the frame rate for extraction. Can select either `5` frames per second, `5`, `4`, `2`, `1`, `0.5`, `0.2`
	* e.g `5`
* `--keep_extracted_frames` (optional): if passed, a copy of the extracted frames will be kept
* `--path_to_nadir` (optional): a square nadir to be added to the images.
	* e.g. `/path/to/nadir.png`
* `--size_of_nadir` (optional, must use with `--path_to_nadir`): percentage height of output video nadir should cover. Default is 25% if not passed.
	* e.g. `25` (%)
* `--max_output_video_secs` (optional) The maximum length of any video in the output in seconds. May result in multiple video files per output if input cannot be packed into maximum video length specified. Default is `60` seconds (300 frames)
	* e.g. `30` seconds
* `--output_filepath` (required): name of video and directory for output. All log and GPX files will be named / placed using this information.
	* e.g. `/path/to/my/file-out`
* `--upload_to_streetview` (optional): if passed will upload the image to StreetView (will require user to authenticate)

#### Mode 4: .360 mode -> max2sphere -> timelapse frames -> final video (for MAX cameras)

* `--input_video` (required): for timelapse video mode, the path to the `.360` video
	* e.g. `/path/to/my/file-in.360`
* `--extract_fps` (required): the frame rate for extraction. Can select either `5` frames per second, `5`, `4`, `2`, `1`, `0.5`, `0.2`
	* e.g `5`
* `--keep_extracted_frames` (optional): if passed, a copy of the extracted frames (after stitched by max2sphere) will be kept
* `--path_to_nadir` (optional): a square nadir to be added to the images.
	* e.g. `/path/to/nadir.png`
* `--size_of_nadir` (optional, must use with `--path_to_nadir`): percentage height of output video nadir should cover. Default is 25% if not passed.
	* e.g. `25` (%)
* `--max_output_video_secs` (optional) The maximum length of any video in the output in seconds. May result in multiple video files per output if input cannot be packed into maximum video length specified. Default is `60` seconds (300 frames)
	* e.g. `30` seconds
* `--output_filepath` (required): name of video and directory for output. All log and GPX files will be named / placed using this information.
	* e.g. `/path/to/my/file-out`
* `--upload_to_streetview` (optional): if passed will upload the image to StreetView (will require user to authenticate)

#### All modes: Check for Street View Status updates

If `--upload_to_streetview` has been used in any mode, you can check the status of the upload.

The following flag can be run in isolation to simply run update checks on all uploads that are not in `PROCESSED` or `FAILED`

* `--refresh_upload_status`: rechecks all GSV uploaded sequences not in `PROCESSED` or `FAILED` states. [More on Google Street View States here](https://developers.google.com/streetview/publish/reference/rest/v1/photoSequence/create#PhotoSequence).

## Support

[Limited support available on Slack via the #oss-gopro2gsv channel](https://join.slack.com/t/trekview/shared_invite/zt-1gb4upchi-52pmWhPiwhFaAQqm0vWmJg).

## License

[Apache 2.0](/LICENSE).