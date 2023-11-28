# Modes

## Overview of modes

gopro2gsv supports a variety of modes depending on the input media you have, and the output you want;

1. equirectangular mp4 video -> final video
	* this mode is designed for when you just want to add a nadir to the video. This mode has the fewest options, but is useful is all you want to do is brand the video before storage/upload to GSV. This mode allows you to:
		* add a custom nadir to the video
2. equirectangular timelapse frames -> final video
	* this mode will take a series of equirectangular timelapse frames and create an equirectangular video from them. This mode allows you to:
		* control the length of the video output: useful for when GSV rejects unmodified longer videos (e.g when the start is recorded indoors)
		* to remove erroneous GPS points / frames: useful for when GPS is erratic and GSV rejects unmodified input video for this reason
3. equirectangular mp4 video -> timelapse frames -> final video
	* this mode will break the input video down into geotagged timelapse frames at an extraction frame rate a user enters. Erroneous GPS/frames are then removed and the extracted frames are then rebuilt into an equirectangular video, or set of equirectangular videos (in the same way as equirectangular timelapse frames -> final video mode), and optionally a set of frames. This mode allows you to:
		* control the length of the video output: useful for when GSV rejects unmodified longer videos (e.g when the start is recorded indoors)
		* to remove erroneous GPS points / frames: useful for when GPS is erratic and GSV rejects unmodified input video for this reason
		* keep a copy of extracted frames: useful if you want to share geotagged frames in addition to the video (e.g. on Facebook, etc.)
4. .360 mode -> max2sphere -> timelapse frames -> final video (for MAX cameras)
	* this mode is similar to equirectangular mp4 video -> timelapse frames -> final video mode, however accepts GoPro's .360 video format (EAC projection). .360 inputs are broken into geotagged timelapse frames at a user set frame rate, erroneous GPS points/frames removed, and these frames are then converted to equirectangular images using max2sphere, and finally rebuilt into an equirectangular video, or set of equirectangular videos (and optionally a set of frames). The user options are the same as equirectangular mp4 video -> timelapse frames -> final video mode
5. dual fisheye timelapse frames -> fusion2sphere -> timelapse frames -> final video (for Fusion cameras)
	* this mode take two fisheye timelapse frames, stitches them together into equirectangular frames using fusion2sphere, removes erroneous GPS points/frames, and the extracted frames are then rebuilt into an equirectangular video, or set of equirectangular videos. The user options are the same as equirectangular timelapse frames -> final video
6. dual fisheye mp4 video -> timelapse frames -> final video (for Fusion cameras)
	* this mode takes two fisheye mp4 videos, breaks each video into frames at a user defined frame rate, stitches them together into equirectangular frames using fusion2sphere, removes erroneous GPS points/frames, and the extracted frames are then rebuilt into an equirectangular video, or set of equirectangular videos. The user options are the same as equirectangular mp4 video -> timelapse frames -> final video mode

## Mode specifications

### Mode 1: equirectangular mp4 video -> final video

Processed GoPro MAX and Fusion videos can be directly uploaded to StreetView.

However, there are many cases where user will want to add a nadir.

As such, user can enter GoPro videos to GoPro2GSV. They will be outputted with a nadir now added to the video track, however, all other tracks will remain the same.

#### User options on input

* custom nadir file
* custom nadir size

#### Validation

GoPro2GSV validates the video input before processing.

It does this by checking each images metadata as follows;

* filetype = .mp4
* `Main:ProjectionType` is `equirectangular`
* `Main:MetaFormat` is `gpmd`
* `Main:GPSDateTime` has more than 10 results

This can be done using exiftool as follows;

```shell
exiftool -ee -G3 -api LargeFileSupport=1 -ProjectionType -MetaFormat -GPSDateTime <DIRECTORY NAME>.mp4
```

#### Adding a nadir

Helpful supporting information for this section:

* How to overlay a nadir on a video: https://www.trekview.org/blog/2022/overlay-nadir-watermark-video-using-ffmpeg/
* How to create a nadir with ImageMagick: https://www.trekview.org/blog/2021/adding-a-custom-nadir-to-360-video-photo/
* Proof of concept of implementation: https://github.com/trek-view/nadir-patcher/

A user can add a nadir to the resulting video file.

A square nadir can be provided by the user on input with a minimum dimension of 500x500px and must be a `.png` image.

To determine how the nadir needs to be resized, the video resolution is checked as follows;

```shell
ffmpeg exiftool -ee -G3 -api LargeFileSupport=1 -ImageWidth -ImageHeight <DIRECTORY NAME>.mp4
```

The adjusted nadir height is always 25% of the `ImageHeight` value, and the nadir width the same as the `ImageWidth` value.

A simple walk-through of the process is described here: https://www.trekview.org/blog/2022/overlay-nadir-watermark-video-using-ffmpeg/

The output video matches the input video for quality and for contained tracks (e.g. video, audio, telemetry, etc.).

### Mode 2: equirectangular timelapse frames -> final video

.jpg timelapse images from the GoPro MAX or Fusion cameras can be converted into a video.

#### User options on input

* custom nadir file
* custom nadir size
* smooth GPS

#### Validation

GoPro2GSV validates image inputs before processing.

It does this by checking each images metadata as follows;

1. GoPro2GSV checks the directory only contains `.jpg` files (case insensitive). It ignores any hidden dot files that might be present, however, will fail if any other type of file or directory is detected.
2. GoPro2GSV checks the filename prefixes all match to a single timelapse recorded on the camera.
	* for the MAX the first 4 letter must always be the same, e.g. `GSAA0001.JPG`, `GSAA0002.JPG`
	* for the FUSION the 4 numbers after `MULTISHOT_` must always be the same, e.g. `MULTISHOT_0001_000001.jpg`, `MULTISHOT_0001_000002.jpg`
3. GoPro2GSV check the metadata of all valid images from previous step using `exiftool`, and images that are not valid are discarded;
	* file extension must be `.jpg` (case insensitive)
	* `XMP-GPano:ProjectionType` must be equal to `equirectangular`
	* `GPS:GPSLatitudeRef` must be present
	* `GPS:GPSLatitude` must be present
	* `GPS:GPSLongitudeRef` must be present
	* `GPS:GPSLongitude` must be present
	* `GPS:GPSAltitudeRef` must be present
	* `GPS:GPSAltitude` must be present
	* `GPS:GPSTimeStamp` must be present
	* `GPS:GPSDateStamp` must be present
4. GoPro2GSV checks all valid images from previous step have the same dimensions by ensuring all images have the same values for `File:ImageWidth` and `File:ImageWidth` properties
5. GoPro2GSV sorts all valid images from previous step by time (`GPS:GPSDateStamp+GPS:GPSDateStamp`), earliest to latest.
6. GoPro2GSV checks that time between consecutive images (`GPS:GPSDateStamp+GPS:GPSDateStamp`) is not >20 seconds. If true then the whole directory is not considered and an `ERROR` log is reported
7. GoPro2GSV checks that a directory with all valid images from previous step has >=10 valid images after the previous step. If <10 valid images then the whole directory is not considered and an `ERROR` log is reported
8. GoPro2GSV renames the images files in format `NNNNN.jpg`, starting from `00001.jpg` and ascends, e.g. `00001.jpg`, `00002.jpg`...
9. GoPro2GSV tracks the data of each timelapse image, including those that failed validation, in the local database. The original and new filename is included so that it is clear what files were not considered in the final video (and why)
10. All valid images in each timelapse (directory) are now ready to be proccessed. A GPX file is created from the valid images as follows;

```shell
exiftool -fileOrder gpsdatetime -p gpx.fmt <DIRECTORY NAME> <DIRECTORY NAME>.gpx
```

Note, the about command assumes that only the valid images are in the directory.

#### Smoothing GPS

 In some cases, GPS data is erroneous. e.g. the distance or speed between two consecutive points by time is clearly to fast (e.g. 1000 km/h speed)

There are many ways to get rid of outlying points like this, here are a few examples; https://gis.stackexchange.com/questions/19683/what-algorithm-should-i-use-to-remove-outliers-in-trace-data

User can set an outlier "speed" at input.

Default if not passed is 40 meters / second (144 km/h).

When user passes this flag, they can enter any whole number

When a destination photo has a speed greater than the specified outlier speed it will be removed (and logged) from the input photos considered to produce a video (similar to validation logic to when photos in input have no GPS)                              

#### Processing frames

There are three distinct parts of the video created from the validated images;

* video track: the video made from the images
* telemetry track: the telemetry track created from the image metadata (currently only GPMF)
* video file metadata: the file metadata


Helpful supporting information for this section:

* Publising a video to StreetView API: https://www.trekview.org/blog/2022/create-google-street-view-video-publish-api/
* H265 encoding in ffmpeg: https://trac.ffmpeg.org/wiki/Encode/H.265

Video processing can be done by ffmpeg as follows

```shell
ffmpeg -r 5 -i %05d.jpg -c:v libx265 -crf 28 -preset medium <DIRECTORY NAME>_NNNN.mp4
```

Let's break that down:

* `-r 5`: the output framerate per second (always 5, explained below)
* `-i %05d.jpg`: the filenames to match on. `%05d` means capture 5 digits.
* `-c:v libx264` is an abbreviated version of codec:v. Encodes the video using the libx264 codec (H264).
* `<DIRECTORY NAME>` is the directory name of the timelapse images

Note, this is purely for example purposes. The resulting video should be of the same quality as the input (so might need some more ffmpeg flags to be included).

[According to many ad-hoc observations in various Google StreetView groups](https://www.facebook.com/groups/366117726774216), StreetView servers also appear to prefer shorter segments, often rejecting longer videos. Again, this is undocumented but I will play it safe and pack videos with a length not exceeding 60 seconds. 

This means at a frame rate of 5 FPS (0.2 seconds per frame), each video will contain a maximum of 300 frames (60 * 5).

As such, a sequence with 720 images will create three videos; two with 300 frames (1 min each) and one with 120 frames (24 seconds long). Each video name is appended with a number based on order, e.g. `timelapse_0001.mp4`, `timelapse_0002.mp4`.

###### GPMF/CAMM track

Helpful supporting information for this section:

* Overview to GPMF: https://www.trekview.org/blog/2020/metadata-exif-xmp-360-video-files-gopro-gpmd/
* Overview to CAMM https://www.trekview.org/blog/2021/metadata-exif-xmp-360-video-files-camm-camera-motion-metadata-spec/
* Adding a CAMM track to video: https://www.trekview.org/blog/2022/injecting-camm-gpmd-telemetry-videos-part-4-camm/
* Adding a GPMF track to video:  https://www.trekview.org/blog/2022/injecting-camm-gpmf-telemetry-videos-part-5-gpmf/
* Understanding MP4s: https://github.com/trek-view/tools/tree/main/understanding_mp4
* Understanding GPS: https://github.com/trek-view/tools/tree/main/understanding_gps
* Understanding GMPF telemetry: https://github.com/trek-view/tools/blob/main/understanding_gpmf_telemetry.md
* Understanding CAMM telemetry: https://github.com/trek-view/tools/tree/main/understanding_camm
* Setting times between images https://www.trekview.org/blog/2022/turn-gopro-timewarp-video-into-timelapse-images/
* Proof of concept implementation: https://github.com/trek-view/telemetry-injector/tree/dep

GPMF/CAMM is a video telemetry standard embedded as a track to MP4 videos.

Before the telemetry needs to be adjuste to match framerate.

By setting the framerate at a fixed 5 FPS (in the video track step) we totally ignore the actual time spacing between photos, but that doesn’t matter.

The real time spacing between photos does not matter when it comes to StreetView (e.g. Google does not really care if photo was taken at the time reported).

However, it does matter the time spacing between GPS points matches the time spacing between the frames in the video (so that the correct GPS position matches the correct frame).

To do this, GoPro2GSV first modified the `GPS:GPSTimeStamp` and `GPS:GPSDateStamp` values in the images.

The first image (by time) in the timelapse remains the same. From there, each subsequent image time is increased by +0.2 seconds.

For example,

* Image 1, original time = `2023-08-01T09:00:00.000` , modified time = `2023-08-01T09:00:00.000`
* Image 2, original time = `2023-08-01T09:00:10.000` , modified time = `2023-08-01T09:00:00.200`
* Image 3, original time = `2023-08-01T09:00:13.000` , modified time = `2023-08-01T09:00:00.400`
* Image 4, original time = `2023-08-01T09:00:17.380` , modified time = `2023-08-01T09:00:00.600`

Now that the times are corrected, the GPMF or GPMD track can be created for the video.

###### Video file metadata

Helpful supporting information for this section:

* Copying global metadata: https://www.trekview.org/blog/2022/create-google-street-view-video-publish-api/
* Google Spatial Media usage: https://www.trekview.org/blog/2021/introduction-to-xmp-namespaces/

Finally, the script adds some global metadata to the video(s) to make them easier to work with in the future.

This can be done by copying the metadata from the first frame, into the video file like so:

```shell
exiftool -TagsFromFile FIRSTFRAME.jpg "-all:all>all:all" OUTPUT.mp4
```

Note, when the timelapse creates multiple video outputs, the FIRSTFRAME.jpg considers the first frame used for that video.

Finally the Google Spatial Media tool can be used to inject equirectangular info to ensure video projection is read correctly;

```shell
git clone https://github.com/google/spatial-media.git
cd spatialmedia
python spatialmedia -i demo-video-no-meta.mp4 demo-video-with-meta.mp4
```



