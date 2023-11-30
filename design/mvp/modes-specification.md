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

## Mode specifications

### Mode 1: equirectangular mp4 video -> final video

Processed GoPro MAX and Fusion videos can be directly uploaded to StreetView.

However, there are many cases where user will want to add a nadir.

As such, user can enter GoPro videos to GoPro2GSV. They will be outputted with a nadir now added to the video track, however, all other tracks will remain the same.

Overview:

* 1a: user input
* 1b: validation
* 1c: add a nadir
* 1d: output

#### 1a: User options on input

* custom nadir file
* custom nadir size

#### 1b: Validation

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

#### 1c: Adding a nadir

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

#### 1d: Output

* `<DIRECTORY NAME ENTERED IN INPUT>/`
	* `<VIDEO NAME ENTERED IN INPUT>.gpx`: the GPX file created from the final video
	* `<VIDEO NAME ENTERED IN INPUT>.mp4`: the final video file
	* `<VIDEO NAME ENTERED IN INPUT>.log`: a log detailing a breakdown of script run


##### 1d: GPX

The GPX file is generated for the video in the following structure;

```xml
<?xml version="1.0" encoding="UTF-8"?>
<gpx xmlns="http://www.topografix.com/GPX/1/1" xmlns:gopro2gsv="https://github.com/trek-view/gopro2gsv" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd" version="1.1" creator="gpx.py -- https://github.com/tkrajina/gpxpy">
  <trk>
    <trkseg>
      <trkpt lat="LAT" lon="LON">
        <ele>ELE</ele>
        <time>TIME</time>
      </trkpt>
```

Most of this (apart from headers) can be generated by exiftool as follows;

```shell
exiftool -ee -p gpx.fmt VIDEO.mp4
```

### Mode 2: equirectangular timelapse frames -> final video

`.jpg` timelapse images from the GoPro MAX or Fusion cameras can be converted into a video.

Overview:

* 2a: user input
* 2b: validation
* 2c: smooth GPS
* 2d: turn frames into video
* 2e: add nadir (same a 1c)
* 2f: output

#### 2a: User options on input

* custom nadir file
* custom nadir size
* smooth GPS
* maximum output video length

#### 2b: Validation

GoPro2GSV validates image inputs before processing.

**Note:** this does not apply to images entering the pipeline via other modes (e.g. equirectangular mp4 video -> timelapse frames -> final video)

It does this by checking the image metadata of all images entered as follows;

1. GoPro2GSV checks the directory for `.jpg` files (case insensitive). It ignores any other files that might be present.
2. Checks there are >=20 frames in the input
3. GoPro2GSV checks the filename prefixes all match to a single timelapse recorded on the camera.
	* for the MAX the first 4 letter must always be the same, e.g. `GSAA0001.JPG`, `GSAA0002.JPG`
	* for the FUSION the 4 numbers after `MULTISHOT_` must always be the same, e.g. `MULTISHOT_0001_000001.jpg`, `MULTISHOT_0001_000002.jpg`
4. GoPro2GSV checks the metadata of all valid images from previous step using `exiftool`, and images that are not valid are discarded;
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
5. GoPro2GSV checks all valid images from previous step have the same dimensions by ensuring all images have the same values for `File:ImageWidth` and `File:ImageHeight` properties

```shell
exiftool -ee -G3 -api LargeFileSupport=1 -ProjectionType -GPSLatitudeRef -GPSLatitude -GPSLongitudeRef -GPSLongitude -GPSAltitudeRef -GPSAltitude -GPSTimeStamp -GPSDateStamp -ImageWidth -ImageHeight  <IMAGE>.jpg
```

6. GoPro2GSV sorts all valid images from previous step by time (`GPS:GPSDateStamp+GPS:GPSDateStamp`), earliest to latest.
7. GoPro2GSV checks that time between consecutive images (`GPS:GPSDateStamp+GPS:GPSDateStamp`) is not >20 seconds. If true then the whole directory is not considered and an `ERROR` log is reported
8. GoPro2GSV checks that a directory with all valid images from previous step has >=20 valid images after the previous step. If <20 valid images then the whole directory is not considered and an `ERROR` log is reported
8. GoPro2GSV renames the images files in format `NNNNN.jpg`, starting from `00001.jpg` and ascends, e.g. `00001.jpg`, `00002.jpg`...
9. GoPro2GSV tracks the data of each timelapse image, including those that failed validation, in the local database. The original and new filename is included so that it is clear what files were not considered in the final video (and why)

#### 2c: Smoothing GPS

In some cases, GPS data is erroneous. e.g. the distance or speed between two consecutive points by time is clearly to fast (e.g. 1000 km/h speed)

There are many ways to get rid of outlying points like this, here are a few examples; https://gis.stackexchange.com/questions/19683/what-algorithm-should-i-use-to-remove-outliers-in-trace-data

As we don't need all photos in an input we solve it simply by checking speed between photos.

(Distance B to A in meters)/(GPS Time B to GPS Time A) = speed in m/s.

`B to A` is used to account for first and last photos.

User can set an outlier "speed" at input that the speed calculated must not exceed.

Default if not passed is 40 meters / second (144 km/h).

Note, first the script determines the speed between each photo pair. And the photo identified as erronous removed.

Let's walk though two examples to demonstrate;

`B to A`: 100 m/s -- A much be incorrect, because `C to B` has "normal speed", so A is removed
`C to B`: 5 m/s
`D to C`: 6 m/s
`E to D`: 100 m/s
`F to E`: 100 m/s -- E much be incorrect, because `D to C` and `F to G` has "normal speed", so A is removed
`G to F`: 5 m/s



`B to A`: 4 m/s
`C to B`: 100 m/s
`D to C`: 100 m/s
`E to D`: 2 m/s
`F to E`: 2 m/s
`G to F`: 100 m/s


`B to A`: 4 m/s
`C to B`: 100 m/s
`D to C`: 100 m/s
`E to D`: 100 m/s
`F to E`: 2 m/s
`G to F`: 



When user passes this flag, they can enter any whole number.

For the images that remain after initial validation, when a destination photo has a speed greater than the specified outlier speed it will be removed (and logged) from the input photos considered to produce a video (similar to validation logic to when photos in input have no GPS).

Like before, GoPro2GSV tracks the data of each timelapse image, including those that failed GPS smoothing, with information about why they failed.

#### 2d: Processing frames

All valid images in each timelapse (directory) are now ready to be processed. 

A final check is done to ensure that there are enough photos to meet the 20 frame (4 second) requirement.

If this test is passed, a GPX file is created from the valid images as follows;

```shell
exiftool -fileOrder gpsdatetime -p gpx.fmt <DIRECTORY NAME> <DIRECTORY NAME>.gpx
```

Note, the about command assumes that only the valid images are in the directory (thus this directory should only contain the validated videos).

The GPX file is generated as follows;

```xml
<?xml version="1.0" encoding="UTF-8"?>
<gpx xmlns="http://www.topografix.com/GPX/1/1" xmlns:gopro2gsv="https://github.com/trek-view/gopro2gsv" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd" version="1.1" creator="gpx.py -- https://github.com/tkrajina/gpxpy">
  <trk>
    <trkseg>
      <trkpt lat="LAT" lon="LON">
        <ele>ELE</ele>
        <time>TIME</time>
        <extensions>
          <gopro2gsv:InputPhoto>PATH TO PHOTO</gopro2gsv:InputPhoto>
          <gopro2gsv:SpeedMStoNext>SPEED TO NEXT PHOTO</gopro2gsv:SpeedMStoNext>
          <gopro2gsv:DistanceMtoNext>SPEED TO NEXT PHOTO</gopro2gsv:DistanceMtoNext>
          <gopro2gsv:TimeSecstoNext>SPEED TO NEXT PHOTO</gopro2gsv:TimeSecstoNext>
        </extensions>
      </trkpt>
```

There are three distinct parts of the video created from the validated images;

* video track: the video made from the images
* telemetry track: the telemetry track created from the GPS data
* video file metadata: the video file metadata (e.g. the equirectangular definition)

##### 2d: Processing frames - video track

Helpful supporting information for this section:

* Publishing a video to StreetView API: https://www.trekview.org/blog/2022/create-google-street-view-video-publish-api/
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

The resulting video is of almost the same quality as the input.

[According to many ad-hoc observations in various Google StreetView groups](https://www.facebook.com/groups/366117726774216), StreetView servers also appear to prefer shorter segments, often rejecting longer videos. Again, this is undocumented but I will play it safe and pack videos with a length not exceeding 60 seconds. 

This means at a frame rate of 5 FPS (0.2 seconds per frame), each video will contain a maximum of 300 frames (60 * 5).

As such, a sequence with 720 images will create three videos; two with 300 frames (1 min each) and one with 120 frames (24 seconds long). Each video name is appended with a number based on order, e.g. `timelapse_0001.mp4`, `timelapse_0002.mp4`.

##### 2d: Processing frames - telemetry track

Helpful supporting information for this section:

* Overview to GPMF: https://www.trekview.org/blog/metadata-exif-xmp-360-video-files-gopro-gpmd/
* Overview to CAMM https://www.trekview.org/blog/metadata-exif-xmp-360-video-files-camm-camera-motion-metadata-spec/
* Injecting Telemetry into Video Files (Part 1): An Introduction: https://www.trekview.org/blog/injecting-camm-gpmd-telemetry-videos-part-1-introduction/
* Injecting Telemetry into Video Files (Part 2): A high-level introduction to the mp4 specification: https://www.trekview.org/blog/injecting-camm-gpmd-telemetry-videos-part-2-mp4-overview/
* Injecting Telemetry into Video Files (Part 3): Structuring telemetry trak's in mp4 videos: https://www.trekview.org/blog/injecting-camm-gpmd-telemetry-videos-part-3-mp4-structure-telemetry-trak/
* Injecting Telemetry into Video Files (Part 4): CAMM: https://www.trekview.org/blog/injecting-camm-gpmd-telemetry-videos-part-4-camm/
* Injecting Telemetry into Video Files (Part 5): GPMF: https://www.trekview.org/blog/injecting-camm-gpmd-telemetry-videos-part-5-gpmf/
* Setting times between images https://www.trekview.org/blog/turn-gopro-timewarp-video-into-timelapse-images/
* Proof of concept implementation: https://github.com/trek-view/telemetry-injector/tree/dep

GPMF is a video telemetry standard embedded as a track to MP4 videos.

Before the telemetry track is created, the image times need to be adjusted to match final video framerate (5 FPS).

By setting the framerate at a fixed 5 FPS (in the video track step) we totally ignore the actual time spacing between photos, but that does not matter for our purposes. That is because the real time spacing between photos does not always matter when it comes to StreetView (e.g. Google does not really care if photo was taken at the time reported). There are exceptions (e.g. where times between photos are very long), but due to validation in GoPro2GSV this does not impact us.

However, it is extremely important the time spacing between GPS points matches the time spacing between the frames in the video (so that the correct GPS position matches the correct frame, else the frame will be aligned to the wrong position on the map).

To do this, GoPro2GSV first modified the `GPS:GPSTimeStamp` and `GPS:GPSDateStamp` values in the images.

The first image (by time) in the timelapse remains the same. From there, each subsequent image time is increased by +0.2 seconds.

For example,

* Image 1, original `GPS:GPSTimeStamp` = `2023-08-01T09:00:00.000` , modified `GPS:GPSTimeStamp` = `2023-08-01T09:00:00.000`
* Image 2, original `GPS:GPSTimeStamp` = `2023-08-01T09:00:10.000` , modified `GPS:GPSTimeStamp` = `2023-08-01T09:00:00.200`
* Image 3, original `GPS:GPSTimeStamp` = `2023-08-01T09:00:13.000` , modified `GPS:GPSTimeStamp` = `2023-08-01T09:00:00.400`
* Image 4, original `GPS:GPSTimeStamp` = `2023-08-01T09:00:17.380` , modified `GPS:GPSTimeStamp` = `2023-08-01T09:00:00.600`

Now that the times are corrected, the GPMF track can be created for the video.

TODO: FIX BROKEN LINKS TO TELEMETRY INJECTOR

##### 2d: Processing frames - video file metadata

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

#### 2e: Adding a nadir

Same as for mode 1c.

#### 2f: Output

* `<DIRECTORY NAME ENTERED IN INPUT>/`
	* `<VIDEO NAME ENTERED IN INPUT>-<N>.gpx`: the GPX file created to make the video
	* `<VIDEO NAME ENTERED IN INPUT>-<N>.mp4`: the final video file
	* `<VIDEO NAME ENTERED IN INPUT>-<N>.log`: a log detailing a breakdown of script run

Note, in the case of image inputs where more than one video is created (as video exceed max length set), there will be multiple `.gpx`, `.mp4`, and `.log` files. `-<N>` is the count of these files, starting at `1`, e.g. `my_directory_name-1.gpx`, `my_directory_name-1.mp4`, `my_directory_name-1.log`, `my_directory_name-2.gpx`, etc.

##### 2f: Output - A note on max video length and frames

An output video should always have 20 frames (is 4 seconds long). The reason for this is Street View will reject videos with <=10 GPS points.

This is simple if the output video length is shorter than the maximum video length defined by the user (or the default which is 300 frames / 1 minute length).

To ensure second, third etc., videos outputted always have 20 or more frames, and thus 20 or more GPS points, if a  second, third etc. is needed, gopro2gsv packs videos to to 20 frames shorter than the maximum video length.

**Example 1:**

Lets say 302 frames are used in the input (and all pass validation). The user sets a maximum output video length of 20 seconds (100 frames).

302 / 5 = 60.4 seconds. Therefore 4 videos will result.

However, the fourth video is less than 20 frames (0.4 seconds = 2 frames).

Thus the first and second video will pack to 100 frames (20 seconds). The third will pack to 80 frames (16 seconds). The fourth video will pack to 22 frames (4.4 seconds)

**Example 2:**

Lets say 290 frames are used in the input (and all pass validation). The user sets a maximum output video length of 20 seconds (100 frames).

290 / 5 = 58 seconds. Therefore 3 videos will result. As no videos less than 20 frames, no need to account for videos that don't meet 20 frame requirements.

### Mode 3: equirectangular mp4 video -> timelapse frames -> final video

Overview:

* 3a: user input
* 3b: validation
* 3c: extract and geotag frames
* 3d: start mode 2 pipeline at 2c: smooth GPS

#### 3a: User options on input

* custom nadir file
* custom nadir size
* extraction frame rate
* keep extracted frames
* smooth GPS
* maximum output video length

#### 3b: Validation

Same as mode 1

#### 3c: Processing

On input a user defines an extraction frame rate.

There are three distinct parts of the video extraction;

* extract GPS: the GPS data in the video
* extract frames: the frames in the video
* geotag the extracted frames

##### 3c: Processing - extract GPS

Useful supporting reading for this section:

* Extract GPS from video: https://www.trekview.org/blog/extracting-gps-track-from-360-timelapse-video/
* Lessons learned geotagging photos: https://www.trekview.org/blog/lessons-learned-when-geotagging-photos/

A GPX file can be created as follows

```shell
exiftool -ee -p gpx.fmt INPUT.mp4 > INPUT.gpx
```

Note, for larger files you might encounter the error:

```shell
Warning: End of processing at large atom (LargeFileSupport not enabled)
```

I got this error when processing this 4GB video.

In which case you need to enable large file support (largefilesupport) using an exiftool `.config` file. [Read this topic on the exiftool forum for more information](https://exiftool.org/forum/index.php?topic=3916.0).

##### 3c: Processing - extract frames

The frames can be extracted from the video as follows

```shell
ffmpeg -i INPUT.mp4 -r USER RATE img%d.jpg 
```

##### 3c: Processing - geotag the extracted frames

Firstly, each frame has the following data added to it/

The following fields are always fixed 

* `XMP-GPano:StitchingSoftware` = gopro2gsv
* `XMP-GPano:SourcePhotosCount` = 2 b/c GoPro 360 cameras only have 2 lenses), so values are static.
* `XMP-GPano:UsePanoramaViewer` = TRUE
* `XMP-GPano:ProjectionType`= equirectangular
* `XMP-GPano:CroppedAreaLeftPixels` = 0
* `XMP-GPano:CroppedAreaTopPixels` = 0

The following fields vary depending on input

* `XMP-GPano:CroppedAreaImageHeightPixels` = Is same as ImageHeight value
* `XMP-GPano:CroppedAreaImageWidthPixels` = Is same as ImageWidth value
* `XMP-GPano:FullPanoHeightPixels` = Is same as ImageHeight value
* `XMP-GPano:FullPanoWidthPixels` = Is same as ImageWidth value

To assign the photo times, we use the first GPS time value reported in the GPS extracted earlier and assign it to photo time fields as follows:

<table class="tableizer-table">
<thead><tr class="tableizer-firstrow"><th>Video metadata field extracted</th><th>Example extracted</th><th>Image metadata field injected</th><th>Example injected</th></tr></thead><tbody>
 <tr><td>TrackN:GPSDateTime</td><td>2020:04:13 15:37:22.444</td><td>DateTimeOriginal</td><td>2020:04:13 15:37:22Z</td></tr>
 <tr><td>TrackN:GPSDateTime</td><td>2020:04:13 15:37:22.444</td><td>SubSecTimeOriginal</td><td>444</td></tr>
 <tr><td>TrackN:GPSDateTime</td><td>2020:04:13 15:37:22.444</td><td>SubSecDateTimeOriginal</td><td>2020:04:13 15:37:22.444Z</td></tr>
</tbody></table>

Example exiftool command to write these values:

```shell
exiftool DateTimeOriginal:"2020:04:13 15:37:22Z" SubSecTimeOriginal:"444" SubSecDateTimeOriginal: "2020:04:13 15:37:22.444Z"
```

Now we need to assign time to other photos. To do this we simply order the photos in ascending numerical order (as we number them sequentially when extracting frames).

We always extract videos at a fixed frame rate based on user input. Therefore, we really only need to know the video start time in addition to framerate, to determine time of subsequent photos.

To do this, we can incrementally add time based on extraction rate (e.g. photo 2 is 0.2 seconds later than photo one where framerate is set at extraction as 5 FPS).

Now the photos are timed, we can use the photo time and GPS positions / times to geotag the photos:

[We can use Exiftool's geotag function to add GPS data (latitude, longitude, altitude)](https://exiftool.org/geotag.html).

```shell
exiftool -Geotag file.xml "-Geotime<SubSecDateTimeOriginal" DIRECTORY_OF_IMAGES
```

This will write the following fields into the photos;

* `GPS:GPSDateStamp`
* `GPS:GPSTimeStamp`
* `GPS:GPSLatitude`
* `GPS:GPSLatitudeRef`
* `GPS:GPSLongitude`
* `GPS:GPSLongitudeRef`
* `GPS:GPSAltitudeRef`
* `GPS:GPSAltitude`

#### 3d: start mode 2 pipeline at 2c: smooth GPS

3d: start mode 2 pipeline at 2c: smooth GPS

### Mode 4: .360 mode -> max2sphere -> timelapse frames -> final video (for MAX cameras)

MAX Cameras produce a .360 format that is in EAC format. These need to be converted into equirectangular format for use with most major viewing software (e.g. GSV).

Overview:

* 4a: user input
* 4b: validation
* 4c: extract frames and GPS, convert frames to equirectangular
* 4d: start mode 3 at 3c Processing - geotag the extracted frames

#### 4a: User options on input

* custom nadir file
* custom nadir size
* extraction frame rate
* keep extracted frames
* smooth GPS
* maximum output video length

#### 4b: Validation

GoPro2GSV validates `.360` inputs before processing as follows;

* file extension must be `.360`
* filenames must start with `GS`
* `GoPro:Model` is GoPro Max
* `trackN:MetaFormat` is gpmd
* `trackN:GPSDateTime` has more than 10 entries

Where `trackN` is the track that contains the gpmd telemetry.

#### 4c: Processing

Useful supporting information for this section;

* Reverse Engineering GoPro's 360 Video File Format (Part 1)
https://www.trekview.org/blog/reverse-engineering-gopro-360-file-format-part-1/
* Part 2
https://www.trekview.org/blog/reverse-engineering-gopro-360-file-format-part-2/
* Part 3
https://www.trekview.org/blog/reverse-engineering-gopro-360-file-format-part-3/
* Part 4
https://www.trekview.org/blog/reverse-engineering-gopro-360-file-format-part-3/

Processing is broken up into four key parts;

1. extract GPS from video
2. extracting frames from .360 input
3. turning extracted frames into equirectangular projections using max2sphere
4. geotag extracted frames

##### 4c Processing - extract GPS from video

Same as 3c: Processing - extract GPS

##### 4c Processing - extracting frames from .360 input

The following command can be used to extract frames from the video;

```
ffmpeg -i INPUT.360 -map 0:0 -r XXX trackN/img%d.jpg -map 0:5 -r XXX trackN/img%d.jpg
```

Where `XXX` = framerate user passes in CLI.

Note: if timewarp mode is used, the track numbers are different:

Regular video = `-map 0:0` and `-map 0:5`
Timewarp video = `-map 0:0` and `-map 0:4` (not currently supported)

##### 4c Processing - turning extracted frames into equirectangular projections using max2sphere

Using max2sphere each frame can be turned into equirectangular frames;

```shell
@SYSTEM_PATH/max2sphere -w XXXX -n 1 -m YYYY track%d/frame%4d.jpg
```

Note, `-w` flag variable (`XXXX`), is the same as `ImageWidth` of extracted frame:

For `-m` flag variable `YYYY` is equal to number of frames extracted from the video.

##### 4c Processing - geotag extracted frames

Same as 3c: Processing - geotag the extracted frames.

Script now continues rest 2c processing (GPS smoothing)