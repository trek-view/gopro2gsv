# GoPro2GSV

Here are Trek View we use GoPro Fusion and MAX cameras to record 360 images and videos.

The results of this work is published to either Google StreetView or Mapillary. In many cases we apply a nadir to these images to brand the video with our logo before uploading them.

Both these tools accept video uploads containing either CAMM or GPMF telemetry tracks.

To suport this workflow GoPro2GSV;

* takes timelapse images and converts them into a video (with GPMF telemetry)
* adds a nadir to all inputted or converted videos

The output will provide a video that can be uploaded directly to [Google StreetView Studio](https://streetviewstudio.maps.google.com/).

GoPro2GSV only officially supports GoPro Fusion and GoPro MAX cameras where the image or video has been shot in 360 mode (`equirectangular`).

## Inputs

### Image -> video processing pipeline

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
6. GoPro2GSV checks that time between consecutive images (`GPS:GPSDateStamp+GPS:GPSDateStamp`) is not >60 seconds. If true then the directory is not considered and an `INFO` log is reported
7. GoPro2GSV checks that a directory with all valid images from previous step has >=10 valid images after the previous step. If <10 valid images then the directory is not considered and an `INFO` log is reported
8. GoPro2GSV renames the images files in format `NNNNN.jpg`, starting from `00001.jpg` and ascends, e.g. `00001.jpg`, `00002.jpg`...
9. GoPro2GSV tracks the data of each timelapse image, including those that failed validation, in the local database. The original and new filename is included so that it is clear what files were not considered in the final video (and why)
10. All valid images in each timelapse (directory) are now ready to be proccessed. A GPX file is created from the valid images as follows;

```shell
exiftool -fileOrder gpsdatetime -p gpx.fmt <DIRECTORY NAME> <DIRECTORY NAME>.gpx
```

Note, the about command assumes that only the valid images are in the directory.

#### Processing

There are three distinct parts of the video created from the validated images

* video track: the video made from the images
* telemetry track: the telemetry track created from the image metadata (GPMF)
* video file metadata: the file metadata

##### Video processing

###### Video track

Helpful supporting information for this section:

* https://www.trekview.org/blog/2022/create-google-street-view-video-publish-api/
* https://trac.ffmpeg.org/wiki/Encode/H.265

Video processing can be done by ffmpeg as follows

```shell
ffmpeg -r 5 -i %05d.jpg -c:v libx265 -crf 28 -preset medium <DIRECTORY NAME>_NNNN.mp4
```

Let's break that down:

* `-r 5`: the output framerate per second (always 5, explained below)
* `-i %05d.jpg`: the filenames to match on. `%05d` means capture 5 digits.
* `-c:v libx264` is an abbreviated version of codec:v. Encodes the video using the libx264 codec (H264).
* `<DIRECTORY NAME>` is the directory name of the timelaps images

Note, this is purely for example purposes. The resulting video should be of the same quality as the input (so might need some more ffmpeg flags to be included).

[According to many ad-hoc observations in various Google Street View groups](https://www.facebook.com/groups/366117726774216), Street View servers also appear to prefer shorter segments, often rejecting longer videos. Again, this is undocumented but I will play it safe and pack videos with a length not exceeding 60 seconds. 

This means at a frame rate of 5 FPS (0.2 seconds per frame), each video will contain a maximum of 300 frames (60 * 5).

As such, a sequence with 720 images will create three videos; two with 300 frames (1 min each) and one with 120 frames (24 seconds long). Each video name is appended with a number based on order, e.g. `timelapse_0001.mp4`, `timelapse_0002.mp4`.

###### GPMF track

Helpful supporting information for this section:

* https://www.trekview.org/blog/2020/metadata-exif-xmp-360-video-files-gopro-gpmd/
* https://www.trekview.org/blog/2022/injecting-camm-gpmf-telemetry-videos-part-5-gpmf/
* https://github.com/trek-view/tools/tree/main/understanding_mp4
* https://github.com/trek-view/tools/tree/main/understanding_gps
* https://github.com/trek-view/tools/blob/main/understanding_gpmf_telemetry.md
* https://www.trekview.org/blog/2022/turn-gopro-timewarp-video-into-timelapse-images/
* Proof of concept implementation: https://github.com/trek-view/telemetry-injector/tree/dep

GPMF is a video telemetry standard embedded as a track to MP4 videos.

By setting the framerate at a fixed 5 FPS (in the video track step) we totally ignore the actual time spacing between photos, but that doesn’t matter.

The real time spacing between photos does not matter when it comes to Street View (e.g. Google does not really care if photo was taken at the time reported).

However, it does matter the time spacing between GPS points matches the time spacing between the frames in the video (so that the correct GPS position matches the correct frame).

To do this, GoPro2GSV first modified the `GPS:GPSTimeStamp` and `GPS:GPSDateStamp` values in the images.

The first image (by time) in the timelapse remains the same. From there, each subsequent image time is increased by +0.2 seconds.

For example,

* Image 1, original time = `2023-08-01T09:00:00.000` , modified time = `2023-08-01T09:00:00.000`
* Image 2, original time = `2023-08-01T09:00:10.000` , modified time = `2023-08-01T09:00:00.200`
* Image 3, original time = `2023-08-01T09:00:13.000` , modified time = `2023-08-01T09:00:00.400`
* Image 4, original time = `2023-08-01T09:00:17.380` , modified time = `2023-08-01T09:00:00.600`

Now that the times are corrected, the GPMF track can be created for the video.

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

### Video -> video processing pipeline

Processed GoPro MAX and Fusion videos can be directly uploaded to Street View.

However, there are many cases where user will want to add a nadir.

As such, user can enter GoPro videos to GoPro2GSV. They will be outputted with a nadir now added to the video track, however, all other tracks will remain the same.

#### Validation

GoPro2GSV validates the video input before processing.

It does this by checking each images metadata as follows;

* `Main:ProjectionType` is `equirectangular`
* `Main:MetaFormat` is `gpmd`
* `Main:GPSDateTime` has more than 10 results

```shell
exiftool -ee -G3 -api LargeFileSupport=1 -ProjectionType -MetaFormat -GPSDateTime <DIRECTORY NAME>.mp4
```

## Settings

### Adding a nadir

Helpful supporting information for this section:

* How to overlay a nadir on a video: https://www.trekview.org/blog/2022/overlay-nadir-watermark-video-using-ffmpeg/
* How to create a nadir with ImageMagick: https://www.trekview.org/blog/2021/adding-a-custom-nadir-to-360-video-photo/
* Proof of concept of implementation: https://github.com/trek-view/nadir-patcher/

In either mode (image or video) a user can add a nadir to the resulting image file.

A square nadir can be provided by the user on input with a minumum dimension of 1000x1000px and must be a `.png` image.

To determine how the nadir needs to be resized, the video resolution is checked as follows;

```shell
ffmpeg exiftool -ee -G3 -api LargeFileSupport=1 -ImageWidth -ImageHeight <DIRECTORY NAME>.mp4
```

The adjusted nadir height is always 15% of the `ImageHeight` value, and the nadir width the same as the `ImageWidth` value.

A simple walkthrough of the process is described here: https://www.trekview.org/blog/2022/overlay-nadir-watermark-video-using-ffmpeg/

The output video must match the input video for quality and for contained tracks (e.g. audio, telemetry, etc.).

## Outputs

### Files

* `non-adjusted.gpx`: the GPX file created after validation
* `adjusted.gpx`: the GPX file created from the final video
* `<DIRECTORY NAME>.mp4`: the final video file

### Database

The local SQLite database is structured with two tables;

* Video
	* User settings
	* Local path to output 
* Timelapse Images
	* User settings
	* Local path to output
* Photos (for photo input)
	* Contains photo data for timelapse image input
	* Key to Timelapse image

## License

[Apache 2.0](/LICENSE).